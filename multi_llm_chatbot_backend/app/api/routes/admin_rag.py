"""Admin-only RAG uploads: persona-scoped knowledge documents."""

import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.config import get_settings
from app.core.auth import get_current_active_user, is_user_admin, require_admin_user
from app.core.rag_manager import get_rag_manager
from app.core.rag_scopes import RAG_SCOPE_PERSONA, SESSION_ADMIN_PERSONA
from app.core import global_rag
from app.models.user import User

LOG = logging.getLogger(__name__)
router = APIRouter()


def _parse_persona_ids(raw: str) -> List[str]:
    raw = (raw or "").strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x).strip() for x in data if str(x).strip()]
    except json.JSONDecodeError:
        pass
    return [p.strip() for p in raw.split(",") if p.strip()]


@router.get("/admin/rag/personas")
async def list_personas_for_rag(
    current_user: User = Depends(require_admin_user),
) -> Dict[str, Any]:
    """Advisor persona ids and labels for admin RAG assignment."""
    settings = get_settings()
    items = []
    for p in settings.personas.items:
        if (p.type or "advisor") == "agent":
            continue
        items.append({"id": p.id, "name": p.name, "role": p.role})
    return {"personas": items}


@router.get("/admin/rag/persona-documents")
async def list_persona_rag_documents(
    current_user: User = Depends(require_admin_user),
) -> Dict[str, Any]:
    """Summary of admin-uploaded persona documents."""
    rag = get_rag_manager()
    stats = rag.get_document_stats(SESSION_ADMIN_PERSONA)
    return stats


@router.post("/admin/rag/persona-document")
async def upload_persona_rag_document(
    file: UploadFile = File(...),
    persona_ids: str = Form(...),
    source_url: str = Form(""),
    citation_title: str = Form(""),
    current_user: User = Depends(require_admin_user),
) -> Dict[str, Any]:
    """
    Upload a document and attach it to one or more advisor personas (admin only).

    *persona_ids*: JSON array string e.g. ``["safety_advisor","cost_estimator"]``
    or comma-separated ids.
    """
    pids = _parse_persona_ids(persona_ids)
    if not pids:
        raise HTTPException(status_code=400, detail="persona_ids is required")

    settings = get_settings()
    valid = {p.id for p in settings.personas.items}
    for pid in pids:
        if pid not in valid:
            raise HTTPException(status_code=400, detail=f"Unknown persona id: {pid}")

    suffix = Path(file.filename or "upload").suffix.lower() or ".txt"
    if suffix not in global_rag.SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type {suffix}. Allowed: {sorted(global_rag.SUPPORTED_EXTENSIONS)}",
        )

    raw = await file.read()
    if len(raw) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 25 MB)")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(raw)
        tmp_path = Path(tmp.name)

    try:
        text = global_rag._extract_text(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    if not text or len(text.strip()) < 30:
        raise HTTPException(status_code=400, detail="Could not extract enough text from the file")

    rag = get_rag_manager()
    cite = (citation_title or file.filename or "document")[:2000]
    url = (source_url or "")[:2000]
    ft = suffix.lstrip(".")

    total_chunks = 0
    for pid in pids:
        res = rag.add_document(
            content=text,
            filename=file.filename or "upload",
            session_id=SESSION_ADMIN_PERSONA,
            file_type=ft,
            rag_scope=RAG_SCOPE_PERSONA,
            source_url=url,
            citation_title=cite,
            persona_id=pid,
        )
        if not res.get("success"):
            raise HTTPException(
                status_code=500,
                detail=res.get("error", "Ingest failed"),
            )
        total_chunks += int(res.get("chunks_created", 0))

    LOG.info(
        "Admin RAG upload by %s: %s -> personas %s (%s chunks)",
        current_user.email,
        file.filename,
        pids,
        total_chunks,
    )
    return {
        "success": True,
        "filename": file.filename,
        "persona_ids": pids,
        "chunks_created": total_chunks,
        "citation_title": cite,
    }


@router.get("/admin/rag/status")
async def admin_rag_status(
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Whether the current user may access admin RAG endpoints."""
    return {"is_admin": is_user_admin(current_user.email)}
