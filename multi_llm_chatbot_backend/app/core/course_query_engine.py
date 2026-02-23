"""
Intelligent Course Query Engine — parses natural language course queries,
searches MongoDB, and implements progressive constraint relaxation.

Designed to be called as a tool by the Course Advisor persona.
"""

import json
import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

TIME_BUFFER_MINUTES = 30  # "no 8am" also excludes 8:15


def _parse_time(t: str) -> Optional[int]:
    """Convert a time string like '8:00am' or '2:30pm' to minutes since midnight."""
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


def _time_str_to_minutes(time_str: str) -> Optional[int]:
    return _parse_time(time_str)


async def parse_query_to_filters(query: str, llm) -> Dict[str, Any]:
    """Use LLM to extract structured course search filters from natural language."""
    system = (
        "Extract course search filters from the user's question. "
        "Return ONLY valid JSON with these optional fields:\n"
        '  course_code (string, e.g. "ENES 1010")\n'
        '  no_start_before (string time, e.g. "9:00am")\n'
        '  no_start_after (string time, e.g. "3:00pm")\n'
        '  preferred_days (string, e.g. "MWF")\n'
        "  min_professor_rating (number 1-5)\n"
        '  semester (string, e.g. "Spring 2026")\n'
        "Omit fields that aren't mentioned."
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
            return json.loads(m.group(0))
    except Exception as e:
        logger.warning(f"Filter extraction failed: {e}")
    return {}


async def search_courses(
    filters: Dict[str, Any],
    relax_level: int = 0,
) -> Dict[str, Any]:
    """
    Search MongoDB courses collection with the given filters.
    relax_level: 0 = exact, 1+ = progressively loosened constraints.
    """
    from app.core.database import get_database
    db = get_database()

    mongo_filter: Dict[str, Any] = {}
    relaxations_applied: List[str] = []

    # Course code
    code = filters.get("course_code")
    if code:
        mongo_filter["course_code"] = {"$regex": re.escape(code), "$options": "i"}

    # Semester
    semester = filters.get("semester", "Spring 2026")
    mongo_filter["semester"] = semester

    # Time constraints (with fuzzy buffer)
    no_before = filters.get("no_start_before")
    no_after = filters.get("no_start_after")

    results = []
    cursor = db.courses.find(mongo_filter)
    all_courses = await cursor.to_list(length=500)

    for course in all_courses:
        schedule = course.get("schedule", {})
        start_str = schedule.get("start_time", "")
        start_min = _time_str_to_minutes(start_str)

        # Apply time filter with buffer
        if no_before and start_min is not None and relax_level < 1:
            threshold = _time_str_to_minutes(no_before)
            if threshold and start_min < (threshold - TIME_BUFFER_MINUTES):
                continue
        if no_after and start_min is not None and relax_level < 1:
            threshold = _time_str_to_minutes(no_after)
            if threshold and start_min > threshold:
                continue

        # Preferred days
        pref_days = filters.get("preferred_days")
        if pref_days and relax_level < 2:
            course_days = schedule.get("days", "")
            if course_days and not any(d in course_days for d in pref_days):
                continue

        results.append(course)

    if relax_level >= 1 and not relaxations_applied:
        relaxations_applied.append("time constraints loosened")
    if relax_level >= 2:
        relaxations_applied.append("day preference removed")

    # Join with professor ratings
    enriched = await _enrich_with_ratings(results, db)

    # Filter by professor rating
    min_rating = filters.get("min_professor_rating")
    if min_rating and relax_level < 3:
        enriched = [c for c in enriched if (c.get("professor_rating") or 0) >= min_rating]
    elif relax_level >= 3:
        relaxations_applied.append("professor rating requirement lowered")

    return {
        "results": enriched[:20],
        "total_found": len(enriched),
        "relaxations": relaxations_applied,
        "filters_used": filters,
    }


async def _enrich_with_ratings(courses: list, db) -> list:
    """Join course data with professor ratings."""
    if not courses:
        return courses

    instructor_names = list({c.get("instructor", "") for c in courses if c.get("instructor")})
    ratings_map = {}
    for name in instructor_names:
        if not name or name == "Staff":
            continue
        # Fuzzy match: search by last name
        parts = name.split()
        last_name = parts[-1] if parts else name
        prof = await db.professor_ratings.find_one(
            {"name": {"$regex": re.escape(last_name), "$options": "i"}}
        )
        if prof:
            ratings_map[name] = {
                "rating": prof.get("rating", 0),
                "difficulty": prof.get("difficulty", 0),
                "would_take_again_pct": prof.get("would_take_again_pct", -1),
            }

    for course in courses:
        instructor = course.get("instructor", "")
        prof_data = ratings_map.get(instructor, {})
        course["professor_rating"] = prof_data.get("rating", 0)
        course["professor_difficulty"] = prof_data.get("difficulty", 0)
        course["would_take_again_pct"] = prof_data.get("would_take_again_pct", -1)

    return courses


async def smart_course_search(query: str, llm) -> Dict[str, Any]:
    """
    Full pipeline: parse query -> search -> progressive relaxation if no results.
    Returns results with explanation of any constraint relaxation.
    """
    filters = await parse_query_to_filters(query, llm)
    if not filters:
        return {"results": [], "message": "I couldn't understand the course search criteria. Please try rephrasing."}

    # Try exact search
    result = await search_courses(filters, relax_level=0)
    if result["results"]:
        return {**result, "message": f"Found {result['total_found']} matching courses."}

    # Progressive relaxation
    alternatives = []
    for level in range(1, 4):
        relaxed = await search_courses(filters, relax_level=level)
        if relaxed["results"]:
            alternatives.append({
                "results": relaxed["results"][:5],
                "relaxations": relaxed["relaxations"],
            })

    if alternatives:
        return {
            "results": [],
            "alternatives": alternatives,
            "message": (
                "No courses match all your criteria exactly, but here are close options "
                "with some constraints relaxed:"
            ),
        }

    return {"results": [], "message": "No courses found matching your criteria, even with relaxed constraints."}
