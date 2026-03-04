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

"""Course search endpoints — used by the Course Advisor persona and direct API."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import get_current_active_user
from app.core.bootstrap import create_llm_client
from app.core.course_query_engine import smart_course_search
from app.models.user import User

LOG = logging.getLogger(__name__)
router = APIRouter()


class CourseSearchRequest(BaseModel):
    query: str
    semester: Optional[str] = None


@router.post("/courses/search")
async def search_courses_endpoint(
    req: CourseSearchRequest,
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Natural language course search with progressive relaxation."""
    llm = create_llm_client()
    result = await smart_course_search(req.query, llm)
    return result


@router.get("/courses/terms")
async def get_available_terms(current_user: User = Depends(get_current_active_user)) -> dict:
    """Return the list of semesters available in the course catalog."""
    from app.scrapers.course_scraper import KNOWN_TERMS
    return {"terms": KNOWN_TERMS}


@router.get("/courses/stats")
async def get_course_stats(current_user: User = Depends(get_current_active_user)) -> dict:
    """Get counts of stored course and professor data, broken down by term."""
    from app.core.database import get_database
    from app.scrapers.course_scraper import KNOWN_TERMS
    db = get_database()
    course_count = await db.courses.count_documents({})
    prof_count = await db.professor_ratings.count_documents({})
    per_term = {}
    for term in KNOWN_TERMS:
        per_term[term] = await db.courses.count_documents({"semester": term})
    return {
        "courses": course_count,
        "professor_ratings": prof_count,
        "courses_per_term": per_term,
    }
