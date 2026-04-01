"""
Weather query engine backed by free Open-Meteo APIs.

Flow:
  1. Extract a location from user text.
  2. Resolve location to coordinates via geocoding API.
  3. Fetch daily forecast via forecast API.
  4. Return structured summary for Weather Advisor.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote
from urllib.request import urlopen

LOG = logging.getLogger(__name__)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODE_TEXT = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Heavy rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
}


def _http_get_json(url: str) -> Dict[str, Any]:
    with urlopen(url, timeout=12) as response:
        return json.loads(response.read().decode("utf-8"))


def _extract_location(query: str) -> Optional[str]:
    text = query.strip()
    patterns = [
        r"\b(?:in|for|at|near)\s+([A-Za-z][A-Za-z\s\-,]{1,50})$",
        r"\bweather\s+(?:in|for)\s+([A-Za-z][A-Za-z\s\-,]{1,50})",
        r"\bforecast\s+(?:in|for)\s+([A-Za-z][A-Za-z\s\-,]{1,50})",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1).strip(" .,!?:;")
    return None


def _resolve_location(location_name: str) -> Optional[Dict[str, Any]]:
    url = f"{GEOCODE_URL}?name={quote(location_name)}&count=1&language=en&format=json"
    data = _http_get_json(url)
    results = data.get("results") or []
    if not results:
        return None
    first = results[0]
    return {
        "name": first.get("name", location_name),
        "admin1": first.get("admin1", ""),
        "country": first.get("country", ""),
        "latitude": first.get("latitude"),
        "longitude": first.get("longitude"),
        "timezone": first.get("timezone", "auto"),
    }


def _fetch_forecast(lat: float, lon: float, timezone: str = "auto") -> Dict[str, Any]:
    url = (
        f"{FORECAST_URL}?latitude={lat}&longitude={lon}"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
        f"&timezone={quote(timezone)}&forecast_days=5"
    )
    return _http_get_json(url)


def _format_days(daily: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, d in enumerate(daily.get("time", [])):
        code = (daily.get("weather_code") or [None])[i]
        out.append(
            {
                "date": d,
                "summary": WEATHER_CODE_TEXT.get(code, f"Weather code {code}"),
                "temp_max_c": (daily.get("temperature_2m_max") or [None])[i],
                "temp_min_c": (daily.get("temperature_2m_min") or [None])[i],
                "precip_prob_pct": (daily.get("precipitation_probability_max") or [None])[i],
            }
        )
    return out


async def smart_weather_search(query: str) -> Dict[str, Any]:
    location = _extract_location(query)
    if not location:
        return {
            "status": "need_location",
            "message": "Please include a city or location (for example: 'weather forecast in Denver').",
            "location": None,
            "forecast": [],
        }

    try:
        resolved = _resolve_location(location)
        if not resolved:
            return {
                "status": "location_not_found",
                "message": f"I couldn't find '{location}'. Try a nearby city name.",
                "location": location,
                "forecast": [],
            }

        raw = _fetch_forecast(
            lat=resolved["latitude"],
            lon=resolved["longitude"],
            timezone=resolved["timezone"] or "auto",
        )
        daily = raw.get("daily") or {}
        days = _format_days(daily)

        place_parts = [resolved["name"], resolved.get("admin1"), resolved.get("country")]
        place = ", ".join([p for p in place_parts if p])

        return {
            "status": "ok",
            "message": f"Forecast loaded for {place}.",
            "location": place,
            "forecast": days,
            "generated_at": datetime.utcnow().isoformat(),
        }
    except Exception as exc:
        LOG.warning(f"Weather search failed: {exc}")
        return {
            "status": "error",
            "message": "Weather service is temporarily unavailable. Please try again.",
            "location": location,
            "forecast": [],
        }
