"""
CRON Scheduler — uses APScheduler to run scrapers on a semester-based schedule.
Modeled on OpenClaw's Gateway scheduler pattern.

Configured via config.yaml → scheduling section.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def _get_semesters() -> List[Dict[str, str]]:
    """Load semester schedule from config, with hardcoded fallback."""
    try:
        from app.config import get_settings
        semesters = get_settings().scheduling.cu_semesters
        if semesters:
            return [{"name": s.name, "end_date": s.end_date} for s in semesters]
    except Exception:
        pass
    return [
        {"name": "Spring 2026", "end_date": "2026-05-08"},
        {"name": "Summer 2026", "end_date": "2026-08-07"},
        {"name": "Fall 2026", "end_date": "2026-12-18"},
        {"name": "Spring 2027", "end_date": "2027-05-07"},
    ]


def get_scrape_dates(end_date_str: str) -> List[datetime]:
    """Return the 4 scrape dates around a semester end."""
    end = datetime.strptime(end_date_str, "%Y-%m-%d")
    return [
        end - timedelta(days=30),
        end - timedelta(days=14),
        end,
        end + timedelta(days=14),
    ]


def get_course_scrape_dates(end_date_str: str) -> List[datetime]:
    """Return the 3 scrape dates for course catalog."""
    end = datetime.strptime(end_date_str, "%Y-%m-%d")
    return [
        end - timedelta(days=30),
        end + timedelta(days=14),
        end + timedelta(days=42),
    ]


_scheduler = None


def init_scheduler():
    """Initialize APScheduler with semester-based scrape jobs."""
    global _scheduler
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.date import DateTrigger
    except ImportError:
        logger.warning("APScheduler not installed — CRON jobs disabled. pip install apscheduler")
        return

    _scheduler = AsyncIOScheduler()

    now = datetime.utcnow()

    for sem in _get_semesters():
        # Professor rating scrapes
        for dt in get_scrape_dates(sem["end_date"]):
            if dt > now:
                _scheduler.add_job(
                    _run_professor_scrape,
                    trigger=DateTrigger(run_date=dt),
                    id=f"prof_{sem['name']}_{dt.isoformat()}",
                    replace_existing=True,
                )

        # Course catalog scrapes
        for dt in get_course_scrape_dates(sem["end_date"]):
            if dt > now:
                _scheduler.add_job(
                    _run_course_scrape,
                    trigger=DateTrigger(run_date=dt),
                    kwargs={"term": sem["name"]},
                    id=f"course_{sem['name']}_{dt.isoformat()}",
                    replace_existing=True,
                )

    _scheduler.start()
    job_count = len(_scheduler.get_jobs())
    logger.info(f"Scheduler started with {job_count} upcoming scrape jobs")


async def _run_professor_scrape():
    from app.scrapers.professor_scraper import run_professor_scrape
    count = await run_professor_scrape()
    logger.info(f"Scheduled professor scrape completed: {count} records")


async def _run_course_scrape(term: str = "Spring 2026"):
    from app.scrapers.course_scraper import run_course_scrape
    count = await run_course_scrape(term=term)
    logger.info(f"Scheduled course scrape completed: {count} records")


def get_scheduled_jobs() -> List[Dict[str, Any]]:
    """Return info about scheduled jobs for admin dashboard."""
    if not _scheduler:
        return []
    return [
        {"id": job.id, "next_run": str(job.next_run_time)}
        for job in _scheduler.get_jobs()
    ]
