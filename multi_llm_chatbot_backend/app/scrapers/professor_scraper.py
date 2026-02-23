"""
Professor Ratings Scraper — fetches CU Boulder professor ratings from
RateMyProfessors using their GraphQL API and stores results in MongoDB.
"""

import logging
import httpx
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

RMP_GRAPHQL_URL = "https://www.ratemyprofessors.com/graphql"
CU_BOULDER_SCHOOL_ID = "U2Nob29sLTEzMzQ="  # Base64 encoded school ID for CU Boulder

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Basic dGVzdDp0ZXN0",
}

SEARCH_QUERY = """
query NewSearchTeachersQuery($query: TeacherSearchQuery!) {
  newSearch {
    teachers(query: $query) {
      edges {
        node {
          id
          firstName
          lastName
          department
          avgRating
          avgDifficulty
          wouldTakeAgainPercent
          numRatings
        }
      }
    }
  }
}
"""


async def scrape_professors(department_filter: str = "") -> List[Dict[str, Any]]:
    """Scrape professor ratings for CU Boulder. Returns list of professor dicts."""
    professors = []
    cursor = ""
    page = 0

    async with httpx.AsyncClient(timeout=30) as client:
        while page < 50:  # safety limit
            variables = {
                "query": {
                    "text": department_filter,
                    "schoolID": CU_BOULDER_SCHOOL_ID,
                    "fallback": True,
                }
            }
            if cursor:
                variables["query"]["after"] = cursor

            try:
                resp = await client.post(
                    RMP_GRAPHQL_URL,
                    json={"query": SEARCH_QUERY, "variables": variables},
                    headers=HEADERS,
                )
                resp.raise_for_status()
                data = resp.json()
                edges = (
                    data.get("data", {})
                    .get("newSearch", {})
                    .get("teachers", {})
                    .get("edges", [])
                )
                if not edges:
                    break

                for edge in edges:
                    node = edge.get("node", {})
                    professors.append({
                        "name": f"{node.get('firstName', '')} {node.get('lastName', '')}".strip(),
                        "department": node.get("department", ""),
                        "rating": node.get("avgRating", 0),
                        "difficulty": node.get("avgDifficulty", 0),
                        "would_take_again_pct": node.get("wouldTakeAgainPercent", -1),
                        "num_ratings": node.get("numRatings", 0),
                        "rmp_id": node.get("id", ""),
                        "scraped_at": datetime.utcnow(),
                    })

                page += 1
                # RMP doesn't use standard cursor pagination in this query
                # so we stop after first page per department
                break

            except Exception as e:
                logger.error(f"RMP scrape error (page {page}): {e}")
                break

    logger.info(f"Scraped {len(professors)} professors from RateMyProfessors")
    return professors


async def store_professors(professors: List[Dict[str, Any]]):
    """Upsert professor ratings into MongoDB."""
    from app.core.database import get_database
    db = get_database()
    collection = db.professor_ratings

    for prof in professors:
        await collection.update_one(
            {"name": prof["name"], "department": prof["department"]},
            {"$set": prof},
            upsert=True,
        )

    logger.info(f"Stored/updated {len(professors)} professor records")


async def run_professor_scrape():
    """Full scrape pipeline: fetch + store."""
    professors = await scrape_professors()
    if professors:
        await store_professors(professors)
    return len(professors)
