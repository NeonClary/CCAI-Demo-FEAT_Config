"""
Global RAG Manager — provides app-wide reference documents (e.g. student handbook)
that are available to all sessions, separate from per-session uploads.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any
from app.core.rag_manager import get_rag_manager

logger = logging.getLogger(__name__)

GLOBAL_SESSION_ID = "__global__"


def get_global_rag():
    """Return the shared RAG manager; global docs use a reserved session id."""
    return get_rag_manager()


def query_global_documents(query: str, n_results: int = 4) -> List[Dict[str, Any]]:
    """Search the global document collection."""
    rag = get_global_rag()
    try:
        return rag.search_documents_with_context(
            query=query,
            session_id=GLOBAL_SESSION_ID,
            persona_context="",
            n_results=n_results,
        )
    except Exception as e:
        logger.warning(f"Global RAG query failed: {e}")
        return []


def seed_global_documents(data_dir: str = "./data"):
    """Ingest all files in *data_dir* into the global RAG collection at startup."""
    data_path = Path(data_dir)
    if not data_path.exists():
        logger.info("No data/ directory found — skipping global RAG seed.")
        return

    rag = get_global_rag()
    supported = {".pdf", ".txt", ".docx", ".doc"}

    for filepath in data_path.iterdir():
        if filepath.suffix.lower() not in supported:
            continue
        try:
            text = _extract_text(filepath)
            if not text or len(text.strip()) < 50:
                continue
            rag.store_document(
                text=text,
                session_id=GLOBAL_SESSION_ID,
                filename=filepath.name,
                metadata={"source": "global", "filename": filepath.name},
            )
            logger.info(f"Seeded global doc: {filepath.name} ({len(text)} chars)")
        except Exception as e:
            logger.error(f"Failed to seed {filepath.name}: {e}")


def _extract_text(filepath: Path) -> str:
    ext = filepath.suffix.lower()
    if ext == ".txt":
        return filepath.read_text(encoding="utf-8", errors="ignore")
    if ext == ".pdf":
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(str(filepath))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            logger.warning(f"PDF extraction failed for {filepath}: {e}")
            return ""
    if ext in (".docx", ".doc"):
        try:
            import docx2txt
            return docx2txt.process(str(filepath))
        except Exception as e:
            logger.warning(f"DOCX extraction failed for {filepath}: {e}")
            return ""
    return ""
