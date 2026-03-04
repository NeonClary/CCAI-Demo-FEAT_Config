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

"""
CRON Scheduler — runs course and professor scrapers on a monthly interval.

Data persists in MongoDB between scrapes; if a scrape fails the previous
data remains available until the next successful run.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

LOG = logging.getLogger(__name__)

_SCHEDULER: Any = None


def _current_term() -> str:
    """Determine the current or upcoming CU semester name (legacy helper)."""
    now = datetime.utcnow()
    month = now.month
    year = now.year
    if month <= 5:
        return f"Spring {year}"
    if month <= 8:
        return f"Fall {year}"
    return f"Spring {year + 1}"


def init_scheduler() -> None:
    """Start APScheduler with monthly scrape jobs for professors and courses."""
    global _SCHEDULER
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        LOG.warning(
            "APScheduler not installed — scheduled scrapes disabled. "
            "pip install apscheduler"
        )
        return

    _SCHEDULER = AsyncIOScheduler()

    _SCHEDULER.add_job(
        _run_professor_scrape,
        trigger=CronTrigger(day=1, hour=3, minute=0),
        id="monthly_professor_scrape",
        replace_existing=True,
    )

    _SCHEDULER.add_job(
        _run_course_scrape,
        trigger=CronTrigger(day=1, hour=3, minute=30),
        id="monthly_course_scrape",
        replace_existing=True,
    )

    _SCHEDULER.add_job(
        _run_cu_info_scrape,
        trigger=CronTrigger(day=1, hour=4, minute=0),
        id="monthly_cu_info_scrape",
        replace_existing=True,
    )

    _SCHEDULER.start()
    jobs = _SCHEDULER.get_jobs()
    for job in jobs:
        LOG.info(f"Scheduled job {job.id} — next run: {job.next_run_time}")
    LOG.info(f"Scheduler started with {len(jobs)} monthly scrape jobs")


async def _run_professor_scrape() -> None:
    from app.scrapers.professor_scraper import run_professor_scrape

    count = await run_professor_scrape()
    LOG.info(f"Monthly professor scrape completed: {count} records")


async def _run_course_scrape() -> None:
    from app.scrapers.course_scraper import run_all_terms_scrape

    count = await run_all_terms_scrape()
    LOG.info(f"Monthly course scrape completed: {count} total records across all terms")


async def _run_cu_info_scrape() -> None:
    from app.scrapers.cu_info_scraper import run_cu_info_scrape
    from app.core.global_rag import seed_global_documents

    count = await run_cu_info_scrape()
    LOG.info(f"Monthly CU info scrape completed: {count} pages saved")
    if count > 0:
        seed_global_documents()
        LOG.info("Global RAG re-seeded after CU info scrape")


def get_scheduled_jobs() -> List[Dict[str, Any]]:
    """Return info about scheduled jobs for admin dashboard."""
    if not _SCHEDULER:
        return []
    return [
        {"id": job.id, "next_run": str(job.next_run_time)}
        for job in _SCHEDULER.get_jobs()
    ]
