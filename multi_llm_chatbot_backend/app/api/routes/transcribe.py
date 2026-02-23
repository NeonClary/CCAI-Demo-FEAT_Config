"""Speech-to-text endpoint using faster-whisper (open-source Whisper)."""

import logging
import tempfile
from fastapi import APIRouter, UploadFile, File, Depends
from app.models.user import User
from app.core.auth import get_current_active_user

logger = logging.getLogger(__name__)
router = APIRouter()

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        logger.info("Loading Whisper model (base.en) — first request will be slow...")
        _model = WhisperModel("base.en", device="cpu", compute_type="int8")
        logger.info("Whisper model loaded.")
    return _model


@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
):
    model = _get_model()
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=True) as tmp:
        contents = await audio.read()
        tmp.write(contents)
        tmp.flush()
        segments, info = model.transcribe(tmp.name, beam_size=3, language="en")
        text = " ".join(seg.text.strip() for seg in segments)

    return {"text": text}
