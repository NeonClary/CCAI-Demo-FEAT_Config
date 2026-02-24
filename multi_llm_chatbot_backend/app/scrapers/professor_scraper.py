"""
Professor Ratings Scraper — fetches CU Boulder professor ratings from
RateMyProfessors and stores results in MongoDB.

Multi-strategy approach:
  1. GraphQL API with proper auth token & pagination
  2. Playwright headless browser (intercepts GraphQL responses)
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

RMP_SEARCH_URL = "https://www.ratemyprofessors.com/search/professors/1087?q=*"
RMP_GRAPHQL_URL = "https://www.ratemyprofessors.com/graphql"

# base64("School-1087") — the CU Boulder school ID used by RMP's GraphQL API
CU_BOULDER_SCHOOL_ID = "U2Nob29sLTEwODc="

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

TEACHER_SEARCH_QUERY = """
query TeacherSearchPaginationQuery(
  $count: Int!
  $cursor: String
  $query: TeacherSearchQuery!
) {
  search: newSearch {
    teachers(query: $query, first: $count, after: $cursor) {
      didFallback
      edges {
        cursor
        node {
          id
          legacyId
          firstName
          lastName
          department
          school { id name }
          avgRating
          avgDifficulty
          wouldTakeAgainPercent
          numRatings
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
"""


def _node_to_professor(node: dict) -> dict:
    """Convert a GraphQL teacher node to our DB schema."""
    return {
        "name": f"{node.get('firstName', '')} {node.get('lastName', '')}".strip(),
        "department": node.get("department", ""),
        "rating": node.get("avgRating", 0),
        "difficulty": node.get("avgDifficulty", 0),
        "would_take_again_pct": node.get("wouldTakeAgainPercent", -1),
        "num_ratings": node.get("numRatings", 0),
        "rmp_id": node.get("id", ""),
        "scraped_at": datetime.utcnow(),
    }


async def _extract_auth_token(client: httpx.AsyncClient) -> str:
    """
    Fetch the RMP landing page and try to pull the auth token from the
    JavaScript bundle.  Falls back to the well-known Basic test:test token.
    """
    try:
        resp = await client.get(
            "https://www.ratemyprofessors.com/",
            headers={"User-Agent": BROWSER_UA},
        )
        html = resp.text

        m = re.search(
            r'"Authorization"\s*:\s*"(Basic\s+[A-Za-z0-9+/=]+)"', html
        )
        if m:
            logger.info("Extracted auth token from page JS")
            return m.group(1)

    except Exception as e:
        logger.debug("Auth token extraction failed: %s", e)

    return "Basic dGVzdDp0ZXN0"


# ── Strategy 1: GraphQL API ─────────────────────────────────────────────────

async def _scrape_via_graphql() -> List[Dict[str, Any]]:
    professors: List[Dict[str, Any]] = []
    page = 0
    cursor = ""

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        auth_token = await _extract_auth_token(client)
        headers = {
            "User-Agent": BROWSER_UA,
            "Authorization": auth_token,
            "Content-Type": "application/json",
            "Referer": RMP_SEARCH_URL,
            "Origin": "https://www.ratemyprofessors.com",
        }

        while page < 150:
            variables = {
                "count": 20,
                "cursor": cursor or "",
                "query": {
                    "text": "",
                    "schoolID": CU_BOULDER_SCHOOL_ID,
                    "fallback": True,
                    "departmentID": None,
                },
            }

            try:
                if page > 0:
                    await asyncio.sleep(0.4)

                resp = await client.post(
                    RMP_GRAPHQL_URL,
                    json={"query": TEACHER_SEARCH_QUERY, "variables": variables},
                    headers=headers,
                )

                if resp.status_code == 403:
                    logger.warning("RMP GraphQL 403 on page %d — auth may be invalid", page)
                    break

                resp.raise_for_status()
                data = resp.json()
                teachers = (
                    data.get("data", {})
                    .get("search", {})
                    .get("teachers", {})
                )
                edges = teachers.get("edges", [])
                page_info = teachers.get("pageInfo", {})

                if not edges:
                    break

                for edge in edges:
                    node = edge.get("node", {})
                    if node:
                        professors.append(_node_to_professor(node))

                if not page_info.get("hasNextPage"):
                    break
                cursor = page_info.get("endCursor", "")
                page += 1

            except Exception as e:
                logger.error("RMP GraphQL error (page %d): %s", page, e)
                break

    return professors


# ── Strategy 2: Playwright browser ──────────────────────────────────────────

async def _scrape_via_playwright() -> List[Dict[str, Any]]:
    """
    Launch a real browser, navigate to the RMP search page, and intercept the
    GraphQL network responses to capture structured professor data.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("playwright not installed — browser scrape unavailable")
        return []

    professors: List[Dict[str, Any]] = []
    captured: List[dict] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        ctx = await browser.new_context(user_agent=BROWSER_UA)
        page = await ctx.new_page()

        async def _on_response(resp):
            if "/graphql" in resp.url:
                try:
                    body = await resp.json()
                    captured.append(body)
                except Exception:
                    pass

        page.on("response", _on_response)

        async def _block_ads(route):
            await route.abort()

        await page.route(
            re.compile(
                r"(doubleclick|googlesyndication|googletagmanager|facebook"
                r"|analytics|adsystem|adservice|amazon-adsystem|moatads|quantserve)"
            ),
            _block_ads,
        )

        try:
            logger.info("Playwright: navigating to RMP search page")
            await page.goto(
                RMP_SEARCH_URL, timeout=60_000, wait_until="domcontentloaded"
            )
            await page.wait_for_timeout(5000)

            for sel in [
                'button:has-text("Close")',
                'button:has-text("Accept")',
                'button:has-text("Got it")',
                'button:has-text("I Accept")',
                '[aria-label="Close"]',
                '[class*="FullPageModal"] button',
                '[class*="CCPAModal"] button',
            ]:
                try:
                    loc = page.locator(sel).first
                    if await loc.is_visible(timeout=1500):
                        await loc.click()
                        await page.wait_for_timeout(500)
                except Exception:
                    pass

            stale_rounds = 0
            prev_len = len(captured)
            for _ in range(200):
                try:
                    btn = page.locator('button:has-text("Show More")').first
                    if await btn.is_visible(timeout=3000):
                        await btn.click()
                        await page.wait_for_timeout(2000)

                        if len(captured) == prev_len:
                            stale_rounds += 1
                        else:
                            stale_rounds = 0
                            prev_len = len(captured)

                        if stale_rounds >= 5:
                            break
                    else:
                        break
                except Exception:
                    break

        except Exception as e:
            logger.error("Playwright navigation error: %s", e)
        finally:
            await browser.close()

    for payload in captured:
        teachers = (
            payload.get("data", {}).get("search", {}).get("teachers", {})
        )
        for edge in teachers.get("edges", []):
            node = edge.get("node", {})
            if node:
                professors.append(_node_to_professor(node))

    return professors


# ── Helpers ──────────────────────────────────────────────────────────────────

def _deduplicate(profs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set = set()
    unique: list = []
    for p in profs:
        key = (p["name"], p["department"])
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


# ── Public API ───────────────────────────────────────────────────────────────

async def scrape_professors() -> List[Dict[str, Any]]:
    """Run scraping strategies in order; return the first that succeeds."""
    logger.info("Starting RMP professor scrape for CU Boulder")

    profs = await _scrape_via_graphql()
    if profs:
        profs = _deduplicate(profs)
        logger.info("GraphQL strategy succeeded: %d professors", len(profs))
        return profs

    logger.info("GraphQL failed — trying Playwright")
    profs = await _scrape_via_playwright()
    if profs:
        profs = _deduplicate(profs)
        logger.info("Playwright strategy succeeded: %d professors", len(profs))
        return profs

    logger.error("All RMP scraping strategies failed")
    return []


async def store_professors(professors: List[Dict[str, Any]]):
    """Upsert professor ratings into MongoDB."""
    from app.core.database import get_database

    db = get_database()
    coll = db.professor_ratings

    for p in professors:
        await coll.update_one(
            {"name": p["name"], "department": p["department"]},
            {"$set": p},
            upsert=True,
        )

    logger.info("Stored/updated %d professor records", len(professors))


async def run_professor_scrape():
    """Full pipeline: scrape + store."""
    profs = await scrape_professors()
    if profs:
        await store_professors(profs)
    return len(profs)
