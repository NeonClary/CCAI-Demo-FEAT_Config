"""Course search endpoints — used by the Course Advisor persona and direct API."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from app.models.user import User
from app.core.auth import get_current_active_user
from app.core.course_query_engine import smart_course_search
from app.core.bootstrap import create_llm_client
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class CourseSearchRequest(BaseModel):
    query: str
    semester: Optional[str] = "Spring 2026"


@router.post("/courses/search")
async def search_courses_endpoint(
    req: CourseSearchRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Natural language course search with progressive relaxation."""
    llm = create_llm_client()
    result = await smart_course_search(req.query, llm)
    return result


@router.get("/courses/stats")
async def get_course_stats(current_user: User = Depends(get_current_active_user)):
    """Get counts of stored course and professor data."""
    from app.core.database import get_database
    db = get_database()
    course_count = await db.courses.count_documents({})
    prof_count = await db.professor_ratings.count_documents({})
    return {
        "courses": course_count,
        "professor_ratings": prof_count,
    }
