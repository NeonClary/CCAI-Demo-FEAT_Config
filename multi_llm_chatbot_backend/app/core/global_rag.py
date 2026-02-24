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
    """Ingest all files in *data_dir* into the global RAG collection at startup.

    Already-loaded files (by filename) are skipped so restarts don't
    duplicate embeddings.
    """
    data_path = Path(data_dir)
    if not data_path.exists():
        logger.info("No data/ directory found — skipping global RAG seed.")
        return

    rag = get_global_rag()
    supported = {".pdf", ".txt", ".docx", ".doc"}

    # Determine which files are already in ChromaDB for the global session
    stats = rag.get_document_stats(GLOBAL_SESSION_ID)
    already_loaded = {
        d.get("filename") for d in stats.get("documents", [])
    }
    if already_loaded:
        logger.info(
            "Global RAG already has %d documents — will skip those",
            len(already_loaded),
        )

    added = 0
    for filepath in sorted(data_path.iterdir()):
        if filepath.suffix.lower() not in supported:
            continue
        if filepath.name in already_loaded:
            logger.debug("Skipping already-loaded global doc: %s", filepath.name)
            continue
        try:
            text = _extract_text(filepath)
            if not text or len(text.strip()) < 50:
                continue
            rag.add_document(
                content=text,
                filename=filepath.name,
                session_id=GLOBAL_SESSION_ID,
                file_type=filepath.suffix.lower().lstrip("."),
            )
            added += 1
            logger.info("Seeded global doc: %s (%d chars)", filepath.name, len(text))
        except Exception as e:
            logger.error("Failed to seed %s: %s", filepath.name, e)

    if added:
        logger.info("Global RAG: loaded %d new documents", added)
    else:
        logger.info("Global RAG: no new documents to load")


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
