"""Admin endpoints for manual scrape triggers and scheduler status."""

from fastapi import APIRouter, Depends
from app.models.user import User
from app.core.auth import get_current_active_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/admin/scrape/professors")
async def trigger_professor_scrape(current_user: User = Depends(get_current_active_user)):
    """Manually trigger professor ratings scrape."""
    from app.scrapers.professor_scraper import run_professor_scrape
    count = await run_professor_scrape()
    return {"status": "success", "records_scraped": count}


@router.post("/admin/scrape/courses")
async def trigger_course_scrape(
    term: str = "Spring 2026",
    current_user: User = Depends(get_current_active_user),
):
    """Manually trigger course catalog scrape."""
    from app.scrapers.course_scraper import run_course_scrape
    count = await run_course_scrape(term=term)
    return {"status": "success", "records_scraped": count}


@router.get("/admin/scheduler/jobs")
async def get_scheduler_jobs(current_user: User = Depends(get_current_active_user)):
    """List all scheduled scrape jobs."""
    from app.core.scheduler import get_scheduled_jobs
    return {"jobs": get_scheduled_jobs()}
