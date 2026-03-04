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
Global RAG Manager — provides app-wide reference documents (e.g. student handbook)
that are available to all sessions, separate from per-session uploads.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

from app.core.rag_manager import get_rag_manager

LOG = logging.getLogger(__name__)

GLOBAL_SESSION_ID = "__global__"
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".docx", ".doc"}


def get_global_rag() -> Any:
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
        LOG.warning(f"Global RAG query failed: {e}")
        return []


def seed_global_documents(data_dir: str = "./data") -> None:
    """Ingest all files in *data_dir* into the global RAG collection at startup.

    Already-loaded files (by filename) are skipped so restarts don't
    duplicate embeddings.
    """
    data_path = Path(data_dir)
    if not data_path.exists():
        LOG.info("No data/ directory found — skipping global RAG seed.")
        return

    rag = get_global_rag()
    # Determine which files are already in ChromaDB for the global session
    stats = rag.get_document_stats(GLOBAL_SESSION_ID)
    already_loaded = {
        d.get("filename") for d in stats.get("documents", [])
    }
    if already_loaded:
        LOG.info(
            f"Global RAG already has {len(already_loaded)} documents — will skip those"
        )

    added = 0
    for filepath in sorted(data_path.iterdir()):
        if filepath.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        if filepath.name in already_loaded:
            LOG.debug(f"Skipping already-loaded global doc: {filepath.name}")
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
            LOG.info(f"Seeded global doc: {filepath.name} ({len(text)} chars)")
        except Exception as e:
            LOG.error(f"Failed to seed {filepath.name}: {e}")

    if added:
        LOG.info(f"Global RAG: loaded {added} new documents")
    else:
        LOG.info("Global RAG: no new documents to load")


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
            LOG.warning(f"PDF extraction failed for {filepath}: {e}")
            return ""
    if ext in (".docx", ".doc"):
        try:
            import docx2txt
            return docx2txt.process(str(filepath))
        except Exception as e:
            LOG.warning(f"DOCX extraction failed for {filepath}: {e}")
            return ""
    return ""
