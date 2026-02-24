"""Voice service health & wake-up management.

Provides status checks and warm-up pings for the external TTS (Coqui) and
STT (Whisper) services, which may sleep when idle and take time to wake.
"""

import asyncio
import logging
import time
import httpx

from fastapi import APIRouter, Depends
from app.models.user import User
from app.core.auth import get_current_active_user

logger = logging.getLogger(__name__)
router = APIRouter()

COQUI_BASE = "https://coqui.neonaiservices.com"
WHISPER_BASE = "https://whisper.neonaiservices.com"

PROBE_TIMEOUT = 12  # seconds – enough to distinguish "awake" from "cold-starting"
CACHE_TTL = 120     # consider a service alive for 2 min after a successful probe

_status_cache: dict = {
    "tts": {"ready": False, "checked_at": 0.0},
    "stt": {"ready": False, "checked_at": 0.0},
}


async def _probe_tts() -> bool:
    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT) as c:
            r = await c.get(f"{COQUI_BASE}/status")
            ok = r.status_code < 500
            _status_cache["tts"] = {"ready": ok, "checked_at": time.time()}
            return ok
    except Exception:
        _status_cache["tts"] = {"ready": False, "checked_at": time.time()}
        return False


async def _probe_stt() -> bool:
    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT) as c:
            r = await c.get(f"{WHISPER_BASE}/status")
            ok = r.status_code < 500
            _status_cache["stt"] = {"ready": ok, "checked_at": time.time()}
            return ok
    except Exception:
        _status_cache["stt"] = {"ready": False, "checked_at": time.time()}
        return False


def _cached_ready(service: str) -> bool | None:
    """Return cached readiness if still fresh, else None (unknown)."""
    entry = _status_cache[service]
    if time.time() - entry["checked_at"] < CACHE_TTL:
        return entry["ready"]
    return None


async def wake_both():
    """Fire probes to both services concurrently (background-safe)."""
    await asyncio.gather(_probe_tts(), _probe_stt(), return_exceptions=True)


@router.get("/voice/status")
async def voice_status(current_user: User = Depends(get_current_active_user)):
    """Return cached readiness or probe fresh."""
    tts_ready = _cached_ready("tts")
    stt_ready = _cached_ready("stt")

    if tts_ready is None or stt_ready is None:
        tts_ok, stt_ok = await asyncio.gather(_probe_tts(), _probe_stt())
        tts_ready = tts_ok if tts_ready is None else tts_ready
        stt_ready = stt_ok if stt_ready is None else stt_ready

    return {"tts_ready": tts_ready, "stt_ready": stt_ready}


@router.post("/voice/wake")
async def voice_wake(current_user: User = Depends(get_current_active_user)):
    """Kick off warm-up pings for both services and return immediately."""
    asyncio.create_task(wake_both())
    return {"status": "waking"}
