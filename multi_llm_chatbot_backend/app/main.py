import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Load configuration FIRST so every module can use it
from app.config import load_settings
settings = load_settings()

# Import the new database functions
from app.core.database import connect_to_mongo, close_mongo_connection

# Import all route modules
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

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    # Seed global RAG documents from data/ directory
    try:
        from app.core.global_rag import seed_global_documents
        seed_global_documents()
    except Exception as e:
        logging.getLogger(__name__).warning(f"Global RAG seed skipped: {e}")
    # Seed course/professor data if collections are empty
    try:
        from app.scrapers.seed_data import seed_if_empty
        await seed_if_empty()
    except Exception as e:
        logging.getLogger(__name__).warning(f"Seed data skipped: {e}")
    # Start CRON scheduler for scraper jobs
    try:
        from app.core.scheduler import init_scheduler
        init_scheduler()
    except Exception as e:
        logging.getLogger(__name__).warning(f"Scheduler init skipped: {e}")
    yield
    # Shutdown
    await close_mongo_connection()

app = FastAPI(
    title=f"{settings.app.title} Backend",
    version="2.0.0",
    lifespan=lifespan
)

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
cors_origins = [origin.strip() for origin in cors_origins]  # Clean whitespace

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
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

# ---------------------------------------------------------------------------
# Public configuration endpoint — serves the frontend-safe subset
# ---------------------------------------------------------------------------
@app.get("/api/config")
def get_public_config():
    """Return the public (non-secret) application configuration."""
    return settings.get_public_config()

@app.get("/")
def root():
    return {
        "message": f"{settings.app.title} Backend",
        "version": "2.0.0",
        "features": [
            "User Authentication", 
            "Persistent Chat Sessions",
            "MongoDB Integration",
            "Ollama Support", 
            "Gemini API Support",
            "Configurable Personas"
        ]
    }
