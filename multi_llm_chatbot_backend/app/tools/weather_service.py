"""
Weather forecast service using the Open-Meteo API (free, no key required).

Provides geocoding, 10-day daily forecasts, and weather-risk evaluation
for construction tasks based on WMO weather codes, wind, and temperature.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

LOG = logging.getLogger(__name__)

_OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"
_OPEN_METEO_GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"

WMO_DESCRIPTIONS: Dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    56: "Light freezing drizzle", 57: "Dense freezing drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Light freezing rain", 67: "Heavy freezing rain",
    71: "Slight snowfall", 73: "Moderate snowfall", 75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
}

_PRECIP_CODES = {51, 53, 55, 61, 63, 65, 80, 81, 82}
_FREEZING_CODES = {56, 57, 66, 67}
_SNOW_CODES = {71, 73, 75, 77, 85, 86}
_THUNDER_CODES = {95, 96, 99}

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _load_service_weather_rules() -> Dict[str, Any]:
    """Load weather-sensitivity rules from contractor_schedules.json."""
    path = _DATA_DIR / "contractor_schedules.json"
    if not path.exists():
        LOG.warning("contractor_schedules.json not found at %s", path)
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("services", {})


async def geocode_location(location_name: str) -> Optional[Dict[str, Any]]:
    """Resolve a place name to lat/lon via Open-Meteo geocoding.

    The API works best with plain city names, so we try the raw input first,
    then fall back to just the first token before a comma (e.g. "Denver, CO"
    becomes "Denver").

    :returns: ``{latitude, longitude, name, country, admin1}`` or ``None``.
    """
    candidates = [location_name.strip()]
    if "," in location_name:
        candidates.append(location_name.split(",")[0].strip())

    async with httpx.AsyncClient(timeout=10) as client:
        for candidate in candidates:
            resp = await client.get(
                _OPEN_METEO_GEOCODE,
                params={"name": candidate, "count": 1, "language": "en", "format": "json"},
            )
            resp.raise_for_status()
            results = resp.json().get("results")
            if results:
                r = results[0]
                return {
                    "latitude": r["latitude"],
                    "longitude": r["longitude"],
                    "name": r.get("name", location_name),
                    "admin1": r.get("admin1", ""),
                    "country": r.get("country", ""),
                }
    return None


async def get_forecast(
    latitude: float,
    longitude: float,
    days: int = 10,
) -> Dict[str, Any]:
    """Fetch a daily weather forecast from Open-Meteo.

    :returns: ``{location: {...}, days: [{date, weather_code, description,
              temp_max_f, temp_min_f, precip_in, rain_in, snow_in,
              wind_max_mph, gust_max_mph, precip_prob_pct}]}``
    """
    daily_vars = ",".join([
        "weather_code",
        "temperature_2m_max", "temperature_2m_min",
        "precipitation_sum", "rain_sum", "snowfall_sum",
        "wind_speed_10m_max", "wind_gusts_10m_max",
        "precipitation_probability_max",
    ])
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": daily_vars,
        "forecast_days": days,
        "timezone": "auto",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(_OPEN_METEO_FORECAST, params=params)
        resp.raise_for_status()
        raw = resp.json()

    daily = raw.get("daily", {})
    dates = daily.get("time", [])
    forecast_days: List[Dict[str, Any]] = []
    for i, d in enumerate(dates):
        code = (daily.get("weather_code") or [None])[i]
        forecast_days.append({
            "date": d,
            "weather_code": code,
            "description": WMO_DESCRIPTIONS.get(code, "Unknown") if code is not None else "Unknown",
            "temp_max_f": (daily.get("temperature_2m_max") or [None])[i],
            "temp_min_f": (daily.get("temperature_2m_min") or [None])[i],
            "precip_in": (daily.get("precipitation_sum") or [None])[i],
            "rain_in": (daily.get("rain_sum") or [None])[i],
            "snow_in": (daily.get("snowfall_sum") or [None])[i],
            "wind_max_mph": (daily.get("wind_speed_10m_max") or [None])[i],
            "gust_max_mph": (daily.get("wind_gusts_10m_max") or [None])[i],
            "precip_prob_pct": (daily.get("precipitation_probability_max") or [None])[i],
        })

    return {
        "location": {
            "latitude": raw.get("latitude"),
            "longitude": raw.get("longitude"),
            "timezone": raw.get("timezone"),
        },
        "days": forecast_days,
    }


def evaluate_weather_risks(
    forecast: Dict[str, Any],
    tasks: List[str],
    target_dates: List[str],
) -> List[Dict[str, Any]]:
    """Check each (task, date) against the forecast and service weather rules.

    :param forecast: Output of :func:`get_forecast`.
    :param tasks: Service IDs (e.g. ``["cement_pouring", "roofing"]``).
    :param target_dates: ISO-format date strings aligned 1:1 with *tasks*.
    :returns: List of warning dicts — empty when all clear.
    """
    rules = _load_service_weather_rules()
    day_lookup = {d["date"]: d for d in forecast.get("days", [])}
    warnings: List[Dict[str, Any]] = []

    for task, tdate in zip(tasks, target_dates):
        svc = rules.get(task)
        if not svc or not svc.get("weather_sensitive"):
            continue

        day = day_lookup.get(tdate)
        if not day:
            continue

        problems: List[str] = []
        code = day.get("weather_code")
        adverse_codes = set(svc.get("adverse_wmo_codes", []))
        templates = svc.get("reason_templates", {})

        if code in _THUNDER_CODES and code in adverse_codes:
            problems.append(templates.get("thunderstorm", f"Thunderstorm forecast (WMO {code})"))
        elif code in _FREEZING_CODES and code in adverse_codes:
            problems.append(templates.get("freezing", f"Freezing precipitation forecast (WMO {code})"))
        elif code in _SNOW_CODES and code in adverse_codes:
            problems.append(templates.get("freezing", f"Snow forecast (WMO {code})"))
        elif code in _PRECIP_CODES and code in adverse_codes:
            problems.append(templates.get("precipitation", f"Precipitation forecast (WMO {code})"))
        elif code in adverse_codes:
            problems.append(templates.get("precipitation", f"Adverse weather (WMO {code})"))

        wind_limit = svc.get("adverse_wind_mph")
        if wind_limit and day.get("wind_max_mph") and day["wind_max_mph"] >= wind_limit:
            tpl = templates.get("wind", "High winds (>{speed} mph)")
            problems.append(tpl.replace("{speed}", str(wind_limit)))

        temp_limit = svc.get("adverse_temp_f")
        if temp_limit is not None and day.get("temp_min_f") is not None:
            if day["temp_min_f"] <= temp_limit:
                tpl = templates.get("freezing", f"Temperature below {temp_limit}°F")
                problems.append(tpl)

        if problems:
            suggested = _find_next_compatible_day(forecast, task, tdate, rules)
            warnings.append({
                "task": task,
                "task_label": svc.get("label", task),
                "date": tdate,
                "weather_description": day.get("description", ""),
                "problems": problems,
                "suggested_alternative": suggested,
            })

    return warnings


def _find_next_compatible_day(
    forecast: Dict[str, Any],
    task: str,
    after_date: str,
    rules: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Scan the forecast for the next day after *after_date* that is safe for *task*."""
    svc = rules.get(task)
    if not svc:
        return None
    adverse_codes = set(svc.get("adverse_wmo_codes", []))
    wind_limit = svc.get("adverse_wind_mph")
    temp_limit = svc.get("adverse_temp_f")

    for day in forecast.get("days", []):
        if day["date"] <= after_date:
            continue
        code = day.get("weather_code")
        if code in adverse_codes:
            continue
        if wind_limit and day.get("wind_max_mph") and day["wind_max_mph"] >= wind_limit:
            continue
        if temp_limit is not None and day.get("temp_min_f") is not None and day["temp_min_f"] <= temp_limit:
            continue
        return {"date": day["date"], "description": day.get("description", "")}

    return None


def format_forecast_table(forecast: Dict[str, Any], location_label: str = "") -> str:
    """Render a forecast as a readable markdown table for LLM/chat output."""
    header = f"### 10-Day Weather Forecast"
    if location_label:
        header += f" — {location_label}"
    lines = [header, ""]
    lines.append("| Date | Conditions | High | Low | Precip | Wind | Prob |")
    lines.append("|------|-----------|------|-----|--------|------|------|")
    for d in forecast.get("days", []):
        hi = f"{d['temp_max_f']:.0f}°F" if d.get("temp_max_f") is not None else "—"
        lo = f"{d['temp_min_f']:.0f}°F" if d.get("temp_min_f") is not None else "—"
        precip = f"{d['precip_in']:.2f} in" if d.get("precip_in") is not None else "—"
        wind = f"{d['wind_max_mph']:.0f} mph" if d.get("wind_max_mph") is not None else "—"
        prob = f"{d['precip_prob_pct']}%" if d.get("precip_prob_pct") is not None else "—"
        lines.append(f"| {d['date']} | {d.get('description', '—')} | {hi} | {lo} | {precip} | {wind} | {prob} |")
    return "\n".join(lines)


def format_weather_warnings(warnings: List[Dict[str, Any]]) -> str:
    """Render weather warnings as markdown text to insert into a scheduler response."""
    if not warnings:
        return ""
    lines = ["", "---", "**WEATHER ADVISORY**", ""]
    for w in warnings:
        lines.append(f"**{w['date']}** — {w['weather_description']} forecast")
        for p in w["problems"]:
            lines.append(f"- **{w['task_label']}**: {p}")
        alt = w.get("suggested_alternative")
        if alt:
            lines.append(f"- Suggested alternative: **{alt['date']}** ({alt['description']})")
        else:
            lines.append(f"- No compatible weather window found in the next 10 days for {w['task_label']}. Monitor forecasts for updates.")
        lines.append("")
    lines.append("---")
    return "\n".join(lines)
