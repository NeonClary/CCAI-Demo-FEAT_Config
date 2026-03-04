# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All Rights Reserved 2008-2025
# Licensed under the BSD 3-Clause License
# https://opensource.org/licenses/BSD-3-Clause
#
# Copyright (c) 2008-2025, Neongecko.com Inc.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
Intelligent Course Query Engine — parses natural-language course queries,
searches MongoDB, and implements progressive per-parameter constraint
relaxation so the student always gets the best available alternatives.

Flow:
  1. LLM extracts structured filters from the query
  2. Exact search against MongoDB
  3. If empty → loosen each parameter independently (one at a time, in steps)
  4. Return results + alternatives + explanation of what was relaxed
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

LOG = logging.getLogger(__name__)

# 8:15am is "functionally the same" as 8:00am
TIME_BUFFER_MINUTES = 20


def _parse_time(t: str) -> Optional[int]:
    """Convert '8:00am' or '2:30pm' to minutes since midnight."""
    m = re.match(r"(\d{1,2}):?(\d{2})?\s*(am|pm)?", t.strip(), re.I)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    period = (m.group(3) or "").lower()
    if period == "pm" and hour != 12:
        hour += 12
    if period == "am" and hour == 12:
        hour = 0
    return hour * 60 + minute


# ── LLM filter extraction ───────────────────────────────────────────────────

def _default_semester() -> str:
    """Pick the most relevant current semester based on today's date."""
    now = datetime.utcnow()
    month = now.month
    if month <= 5:
        return f"Spring {now.year}"
    if month <= 8:
        return f"Summer {now.year}"
    return f"Fall {now.year}"


async def parse_query_to_filters(query: str, llm: Any) -> Dict[str, Any]:
    """Use the LLM to extract structured course-search filters."""
    from app.scrapers.course_scraper import KNOWN_TERMS

    default_sem = _default_semester()
    terms_str = ", ".join(KNOWN_TERMS)

    system = (
        "You extract course search filters from a student's natural-language question.\n"
        "Return ONLY valid JSON (no markdown fences, no extra text) with these optional fields:\n"
        '  "course_code": string, e.g. "ENES 1010"\n'
        '  "earliest_start": string, the earliest acceptable class start time, e.g. "9:00am"\n'
        '    IMPORTANT: if the student says "no 8am classes" or "I don\'t want 8am", set earliest_start to "9:00am".\n'
        '    If they say "no classes before 10", set earliest_start to "10:00am".\n'
        '  "latest_start": string, the latest acceptable start, e.g. "3:00pm"\n'
        '  "preferred_days": string, e.g. "MWF" or "TTh"\n'
        '  "min_professor_rating": number 1-5, minimum acceptable professor quality rating\n'
        f'  "semester": string — one of: {terms_str}. Default to "{default_sem}" if not specified.\n'
        "Omit fields the student did not mention. Always include semester.\n"
    )
    try:
        raw = await llm.generate(
            system_prompt=system,
            context=[{"role": "user", "content": query}],
            temperature=0.1,
            max_tokens=256,
        )
        cleaned = re.sub(r"```(?:json)?", "", raw).strip()
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            filters = json.loads(m.group(0))
            if "semester" not in filters:
                filters["semester"] = default_sem
            LOG.info(f"Extracted filters: {filters}")
            return filters
        LOG.warning(f"No JSON found in LLM response: {cleaned[:200]}")
    except Exception as e:
        LOG.warning(f"Filter extraction failed: {e}")

    return {"semester": default_sem}


# ── Core search ──────────────────────────────────────────────────────────────

async def _run_search(
    filters: Dict[str, Any],
    time_buffer: int = TIME_BUFFER_MINUTES,
    skip_time: bool = False,
    skip_days: bool = False,
    skip_rating: bool = False,
    min_rating_override: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Search MongoDB courses with given filters and return enriched results.
    Use skip_* flags and overrides to relax individual constraints.
    """
    from app.core.database import get_database

    db = get_database()
    mongo_filter: Dict[str, Any] = {}

    code = filters.get("course_code")
    if code:
        mongo_filter["course_code"] = {"$regex": re.escape(code), "$options": "i"}

    mongo_filter["semester"] = filters.get("semester", _default_semester())

    cursor = db.courses.find(mongo_filter, {"_id": 0})
    all_courses: List[Dict[str, Any]] = await cursor.to_list(length=500)

    results: List[Dict[str, Any]] = []
    for course in all_courses:
        schedule = course.get("schedule", {})
        start_str = schedule.get("start_time", "")
        start_min = _parse_time(start_str) if start_str else None

        if not skip_time:
            earliest = filters.get("earliest_start")
            if earliest and start_min is not None:
                threshold = _parse_time(earliest)
                if threshold is not None and start_min < (threshold - time_buffer):
                    continue

            latest = filters.get("latest_start")
            if latest and start_min is not None:
                threshold = _parse_time(latest)
                if threshold is not None and start_min > (threshold + time_buffer):
                    continue

        if not skip_days:
            pref_days = filters.get("preferred_days")
            if pref_days:
                course_days = schedule.get("days", "")
                if course_days and not any(d in course_days for d in pref_days):
                    continue

        results.append(course)

    enriched = await _enrich_with_ratings(results, db)

    effective_rating: Optional[float] = None
    if not skip_rating:
        effective_rating = (
            min_rating_override
            if min_rating_override is not None
            else filters.get("min_professor_rating")
        )
        if effective_rating:
            enriched = [
                c for c in enriched
                if (c.get("professor_rating") or 0) >= effective_rating
            ]

    enriched.sort(key=lambda c: c.get("professor_rating", 0), reverse=True)
    return enriched


async def _enrich_with_ratings(courses: List[Dict[str, Any]], db: Any) -> List[Dict[str, Any]]:
    """Join course data with professor ratings from MongoDB."""
    if not courses:
        return courses

    instructor_names = list(
        {c.get("instructor", "") for c in courses if c.get("instructor")}
    )
    ratings_map: Dict[str, dict] = {}

    for name in instructor_names:
        if not name or name.lower() == "staff":
            continue

        prof = await db.professor_ratings.find_one(
            {"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}},
            {"_id": 0},
        )

        if not prof:
            parts = name.split()
            last_name = parts[-1] if parts else name
            prof = await db.professor_ratings.find_one(
                {"name": {"$regex": re.escape(last_name), "$options": "i"}},
                {"_id": 0},
            )

        if prof:
            ratings_map[name] = {
                "rating": prof.get("rating", 0),
                "difficulty": prof.get("difficulty", 0),
                "would_take_again_pct": prof.get("would_take_again_pct", -1),
                "num_ratings": prof.get("num_ratings", 0),
            }

    for course in courses:
        instr = course.get("instructor", "")
        data = ratings_map.get(instr, {})
        course["professor_rating"] = data.get("rating", 0)
        course["professor_difficulty"] = data.get("difficulty", 0)
        course["would_take_again_pct"] = data.get("would_take_again_pct", -1)
        course["num_ratings"] = data.get("num_ratings", 0)

    return courses


# ── Progressive relaxation ───────────────────────────────────────────────────

async def smart_course_search(query: str, llm: Any) -> Dict[str, Any]:
    """
    Full pipeline:
      1. LLM extracts filters
      2. Exact search
      3. Per-parameter progressive relaxation
      4. Return results + alternatives + explanation
    """
    filters = await parse_query_to_filters(query, llm)
    if not filters or not any(v for k, v in filters.items() if k != "semester"):
        return {
            "results": [],
            "alternatives": [],
            "message": (
                "I couldn't understand specific course search criteria. "
                "Try something like: 'Find ENES 1010 sections, no 8am classes, "
                "professors rated 4+.'"
            ),
            "filters_used": filters,
        }

    # ── Exact search ────────────────────────────────────────────────────
    results = await _run_search(filters)
    if results:
        return {
            "results": results[:20],
            "total_found": len(results),
            "alternatives": [],
            "message": f"Found {len(results)} courses matching all your criteria.",
            "filters_used": filters,
        }

    # ── Per-parameter progressive relaxation ────────────────────────────
    has_time = bool(
        filters.get("earliest_start") or filters.get("latest_start")
    )
    has_days = bool(filters.get("preferred_days"))
    has_rating = bool(filters.get("min_professor_rating"))
    min_rating = filters.get("min_professor_rating", 0)

    alternatives: List[Dict[str, Any]] = []

    if has_time:
        res = await _run_search(filters, time_buffer=60)
        if res:
            alternatives.append({
                "results": res[:5],
                "relaxed_parameter": "time preference",
                "relaxation_detail": "Widened acceptable window by 30 minutes",
            })
        else:
            res = await _run_search(filters, skip_time=True)
            if res:
                alternatives.append({
                    "results": res[:5],
                    "relaxed_parameter": "time preference",
                    "relaxation_detail": "Removed time constraint entirely",
                })

    if has_rating and min_rating:
        lowered = max(0, min_rating - 1)
        res = await _run_search(filters, min_rating_override=lowered)
        if res:
            alternatives.append({
                "results": res[:5],
                "relaxed_parameter": "professor rating",
                "relaxation_detail": (
                    f"Lowered minimum rating from {min_rating} to {lowered}"
                ),
            })
        else:
            res = await _run_search(filters, skip_rating=True)
            if res:
                alternatives.append({
                    "results": res[:5],
                    "relaxed_parameter": "professor rating",
                    "relaxation_detail": "Removed professor rating requirement",
                })

    if has_days:
        res = await _run_search(filters, skip_days=True)
        if res:
            alternatives.append({
                "results": res[:5],
                "relaxed_parameter": "day preference",
                "relaxation_detail": "Removed day-of-week preference",
            })

    if not alternatives:
        res = await _run_search(
            filters, skip_time=True, skip_days=True, skip_rating=True
        )
        if res:
            alternatives.append({
                "results": res[:5],
                "relaxed_parameter": "all optional constraints",
                "relaxation_detail": "Removed all preference constraints",
            })

    if alternatives:
        return {
            "results": [],
            "alternatives": alternatives,
            "message": (
                "No courses match all your criteria exactly. "
                "Here are the closest options with some constraints relaxed:"
            ),
            "filters_used": filters,
        }

    return {
        "results": [],
        "alternatives": [],
        "message": (
            "No courses found matching your criteria, even with relaxed "
            "constraints. Please check the course code or try different criteria."
        ),
        "filters_used": filters,
    }
