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

import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, List

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from app.config import load_settings

settings = load_settings()

from app.core.database import connect_to_mongo, close_mongo_connection

from app.api.routes import router as main_router
from app.api.routes.auth import router as auth_router
from app.api.routes.chat_sessions import router as chat_sessions_router
from app.api.routes.phd_canvas import router as phd_canvas_router
from app.api.routes.user_profile import router as user_profile_router
from app.api.routes.onboarding import router as onboarding_router
from app.api.routes.search_references import router as search_ref_router
from app.api.routes.admin import router as admin_router
from app.api.routes.courses import router as courses_router
from app.api.routes.transcribe import router as transcribe_router
from app.api.routes.tts import router as tts_router
from app.api.routes.voice import router as voice_router

LOG = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

APP_VERSION = "2.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown lifecycle events."""
    await connect_to_mongo()

    try:
        from app.scrapers.cu_info_scraper import run_cu_info_scrape
        await run_cu_info_scrape()
    except Exception as exc:
        LOG.warning(f"CU info scrape skipped: {exc}")

    try:
        from app.core.global_rag import seed_global_documents
        seed_global_documents()
    except Exception as exc:
        LOG.warning(f"Global RAG seed skipped: {exc}")

    try:
        from app.core.scheduler import init_scheduler
        init_scheduler()
    except Exception as exc:
        LOG.warning(f"Scheduler init skipped: {exc}")

    yield

    from app.llm.improved_gemini_client import close_shared_client as close_gemini
    from app.llm.improved_ollama_client import close_shared_client as close_ollama
    await close_gemini()
    await close_ollama()
    await close_mongo_connection()


app = FastAPI(
    title=f"{settings.app.title} Backend",
    version=APP_VERSION,
    lifespan=lifespan,
)

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
cors_origins = [origin.strip() for origin in cors_origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(main_router)
app.include_router(auth_router, prefix="/auth", tags=["authentication"])
app.include_router(chat_sessions_router, prefix="/api", tags=["chat-sessions"])
app.include_router(phd_canvas_router, prefix="/api", tags=["phd-canvas"])
app.include_router(user_profile_router, prefix="/api", tags=["user-profile"])
app.include_router(onboarding_router, prefix="/api", tags=["onboarding"])
app.include_router(search_ref_router, prefix="/api", tags=["search-references"])
app.include_router(admin_router, prefix="/api", tags=["admin"])
app.include_router(courses_router, prefix="/api", tags=["courses"])
app.include_router(transcribe_router, prefix="/api", tags=["transcribe"])
app.include_router(tts_router, prefix="/api", tags=["tts"])
app.include_router(voice_router, prefix="/api", tags=["voice"])


@app.get("/api/config")
def get_public_config() -> Dict:
    """Return the public (non-secret) application configuration."""
    return settings.get_public_config()


@app.get("/")
def root() -> Dict:
    """Health-check endpoint returning basic service metadata."""
    return {
        "message": f"{settings.app.title} Backend",
        "version": APP_VERSION,
        "features": [
            "User Authentication",
            "Persistent Chat Sessions",
            "MongoDB Integration",
            "Ollama Support",
            "Gemini API Support",
            "Configurable Personas",
        ],
    }
