"""Speech-to-text proxy — forwards audio to external Whisper STT service.

The browser records in WebM/Opus which the Whisper API cannot decode from raw
bytes.  We convert to WAV via ffmpeg before forwarding.
"""

import asyncio
import logging
import subprocess
import tempfile
import httpx
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from app.models.user import User
from app.core.auth import get_current_active_user

logger = logging.getLogger(__name__)
router = APIRouter()

WHISPER_BASE = "https://whisper.neonaiservices.com"


def _convert_to_wav(audio_bytes: bytes, src_mime: str) -> bytes:
    """Use ffmpeg to convert any audio format to 16 kHz mono WAV."""
    with tempfile.TemporaryDirectory() as tmp:
        ext = "webm" if "webm" in (src_mime or "") else "ogg"
        src = Path(tmp) / f"in.{ext}"
        dst = Path(tmp) / "out.wav"
        src.write_bytes(audio_bytes)
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(src),
                "-ar", "16000", "-ac", "1", "-f", "wav", str(dst),
            ],
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.warning("ffmpeg stderr: %s", result.stderr.decode(errors="replace")[-500:])
            raise RuntimeError("ffmpeg conversion failed")
        return dst.read_bytes()


@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
):
    contents = await audio.read()
    if not contents:
        return {"text": ""}

    mime = audio.content_type or "audio/webm"
    logger.info("STT: received %d bytes (%s)", len(contents), mime)

    # Cross-wake TTS while we handle STT
    try:
        from app.api.routes.voice import _probe_tts, _cached_ready
        if _cached_ready("tts") is not True:
            asyncio.create_task(_probe_tts())
    except Exception:
        pass

    # Convert to WAV for the Whisper API
    need_convert = "wav" not in mime.lower()
    if need_convert:
        try:
            loop = asyncio.get_event_loop()
            wav_bytes = await loop.run_in_executor(None, _convert_to_wav, contents, mime)
            logger.info("STT: converted to WAV (%d bytes)", len(wav_bytes))
        except Exception as e:
            logger.error("STT conversion error: %s", e)
            raise HTTPException(status_code=500, detail="Audio conversion failed")
    else:
        wav_bytes = contents

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{WHISPER_BASE}/stt",
                content=wav_bytes,
                headers={"Content-Type": "audio/wav"},
            )
            resp.raise_for_status()

            from app.api.routes.voice import _status_cache
            import time as _t
            _status_cache["stt"] = {"ready": True, "checked_at": _t.time()}

            text = resp.text.strip().strip('"')
            logger.info("STT result: '%s'", text[:100])
            return {"text": text}
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="STT service timed out")
    except Exception as e:
        logger.error("STT proxy error: %s", e)
        raise HTTPException(status_code=502, detail="STT service unavailable")
