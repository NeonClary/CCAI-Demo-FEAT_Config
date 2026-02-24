"""
CRON Scheduler — runs course and professor scrapers on a monthly interval.

Data persists in MongoDB between scrapes; if a scrape fails the previous
data remains available until the next successful run.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

_scheduler = None


def _current_term() -> str:
    """Determine the current or upcoming CU semester name (legacy helper)."""
    from datetime import datetime

    now = datetime.utcnow()
    month = now.month
    year = now.year
    if month <= 5:
        return f"Spring {year}"
    if month <= 8:
        return f"Fall {year}"
    return f"Spring {year + 1}"


def init_scheduler():
    """Start APScheduler with monthly scrape jobs for professors and courses."""
    global _scheduler
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning(
            "APScheduler not installed — scheduled scrapes disabled. "
            "pip install apscheduler"
        )
        return

    _scheduler = AsyncIOScheduler()

    _scheduler.add_job(
        _run_professor_scrape,
        trigger=CronTrigger(day=1, hour=3, minute=0),
        id="monthly_professor_scrape",
        replace_existing=True,
    )

    _scheduler.add_job(
        _run_course_scrape,
        trigger=CronTrigger(day=1, hour=3, minute=30),
        id="monthly_course_scrape",
        replace_existing=True,
    )

    _scheduler.add_job(
        _run_cu_info_scrape,
        trigger=CronTrigger(day=1, hour=4, minute=0),
        id="monthly_cu_info_scrape",
        replace_existing=True,
    )

    _scheduler.start()
    jobs = _scheduler.get_jobs()
    for job in jobs:
        logger.info(
            "Scheduled job %s — next run: %s", job.id, job.next_run_time
        )
    logger.info("Scheduler started with %d monthly scrape jobs", len(jobs))


async def _run_professor_scrape():
    from app.scrapers.professor_scraper import run_professor_scrape

    count = await run_professor_scrape()
    logger.info("Monthly professor scrape completed: %d records", count)


async def _run_course_scrape():
    from app.scrapers.course_scraper import run_all_terms_scrape

    count = await run_all_terms_scrape()
    logger.info("Monthly course scrape completed: %d total records across all terms", count)


async def _run_cu_info_scrape():
    from app.scrapers.cu_info_scraper import run_cu_info_scrape
    from app.core.global_rag import seed_global_documents

    count = await run_cu_info_scrape()
    logger.info("Monthly CU info scrape completed: %d pages saved", count)
    if count > 0:
        seed_global_documents()
        logger.info("Global RAG re-seeded after CU info scrape")


def get_scheduled_jobs() -> List[Dict[str, Any]]:
    """Return info about scheduled jobs for admin dashboard."""
    if not _scheduler:
        return []
    return [
        {"id": job.id, "next_run": str(job.next_run_time)}
        for job in _scheduler.get_jobs()
    ]
