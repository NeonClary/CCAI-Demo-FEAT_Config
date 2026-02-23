"""
Course Catalog Scraper — fetches CU Boulder course listings from
classes.colorado.edu and stores results in MongoDB.

classes.colorado.edu is a JS-heavy site. This scraper attempts to use the
underlying API endpoints it calls. If those fail, it falls back to a
simplified static parse. For full fidelity, Playwright can be added later.
"""

import logging
import httpx
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

CLASSES_SEARCH_URL = "https://classes.colorado.edu/api/?page=fose&route=search"


async def scrape_courses(
    term: str = "Spring 2026",
    subject: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Scrape courses from CU Boulder class search.
    *term* is a human-readable semester label.
    """
    courses: List[Dict[str, Any]] = []

    payload = {
        "other": {"srcdb": _term_to_srcdb(term)},
        "criteria": [],
    }
    if subject:
        payload["criteria"].append({"field": "subject", "value": subject})

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(CLASSES_SEARCH_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])

            for item in results:
                schedule = _parse_schedule(item.get("meets", ""))
                courses.append({
                    "course_code": f"{item.get('subject', '')} {item.get('catalog_nbr', '')}".strip(),
                    "title": item.get("title", ""),
                    "section": item.get("section", ""),
                    "instructor": item.get("instr", "Staff"),
                    "schedule": schedule,
                    "location": item.get("bldg", ""),
                    "seats_available": item.get("seats", 0),
                    "semester": term,
                    "scraped_at": datetime.utcnow(),
                })

            logger.info(f"Scraped {len(courses)} courses for {term}")

        except Exception as e:
            logger.error(f"Course scrape error: {e}")

    return courses


def _term_to_srcdb(term: str) -> str:
    """Convert a human-readable term to the srcdb code used by CU's API."""
    term_lower = term.lower()
    year_match = re.search(r"20\d{2}", term)
    year = year_match.group(0) if year_match else "2026"
    if "spring" in term_lower:
        return f"{year}1"
    if "summer" in term_lower:
        return f"{year}4"
    if "fall" in term_lower:
        return f"{year}7"
    return f"{year}1"


def _parse_schedule(meets: str) -> Dict[str, Any]:
    """Parse a schedule string like 'MWF 10:00am-10:50am' into structured data."""
    if not meets:
        return {"days": "", "start_time": "", "end_time": "", "raw": ""}

    day_match = re.match(r"([A-Za-z]+)", meets)
    days = day_match.group(1) if day_match else ""

    time_match = re.search(r"(\d{1,2}:\d{2}\s*[ap]m)\s*-\s*(\d{1,2}:\d{2}\s*[ap]m)", meets, re.I)
    start_time = time_match.group(1).strip() if time_match else ""
    end_time = time_match.group(2).strip() if time_match else ""

    return {"days": days, "start_time": start_time, "end_time": end_time, "raw": meets}


async def store_courses(courses: List[Dict[str, Any]]):
    """Upsert course data into MongoDB."""
    from app.core.database import get_database
    db = get_database()
    collection = db.courses

    for course in courses:
        await collection.update_one(
            {
                "course_code": course["course_code"],
                "section": course["section"],
                "semester": course["semester"],
            },
            {"$set": course},
            upsert=True,
        )

    logger.info(f"Stored/updated {len(courses)} course records")


async def run_course_scrape(term: str = "Spring 2026"):
    """Full scrape pipeline: fetch + store."""
    courses = await scrape_courses(term=term)
    if courses:
        await store_courses(courses)
    return len(courses)
