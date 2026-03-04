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

"""Admin endpoints for manual scrape triggers and scheduler status."""

import logging

from fastapi import APIRouter, Depends

from app.core.auth import get_current_active_user
from app.models.user import User

LOG = logging.getLogger(__name__)
router = APIRouter()


@router.post("/admin/scrape/professors")
async def trigger_professor_scrape(current_user: User = Depends(get_current_active_user)) -> dict:
    """Manually trigger professor ratings scrape."""
    from app.scrapers.professor_scraper import run_professor_scrape
    count = await run_professor_scrape()
    return {"status": "success", "records_scraped": count}


@router.post("/admin/scrape/courses")
async def trigger_course_scrape(
    term: str = "Spring 2026",
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Manually trigger course catalog scrape."""
    from app.scrapers.course_scraper import run_course_scrape
    count = await run_course_scrape(term=term)
    return {"status": "success", "records_scraped": count}


@router.get("/admin/scheduler/jobs")
async def get_scheduler_jobs(current_user: User = Depends(get_current_active_user)) -> dict:
    """List all scheduled scrape jobs."""
    from app.core.scheduler import get_scheduled_jobs
    return {"jobs": get_scheduled_jobs()}
