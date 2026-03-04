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
import uuid
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from threading import Lock

from app.core.rag_manager import get_rag_manager

LOG = logging.getLogger(__name__)


@dataclass
class ConversationContext:
    """Enhanced conversation context for RAG integration."""

    def __init__(self, session_id: Optional[str] = None) -> None:
        self.session_id: str = session_id or str(uuid.uuid4())
        self.messages: List[Dict[str, str]] = []
        self.uploaded_files: List[str] = []
        self.total_upload_size: int = 0
        self.created_at: datetime = datetime.now()
        self.last_accessed: datetime = datetime.now()

        self.document_chunks_count: int = 0
        self.last_retrieval_stats: Dict[str, Any] = {}

    def append_message(self, role: str, content: str) -> None:
        """
        Add a message to the conversation history.

        :param role: Message role (e.g. ``"user"``, ``"assistant"``).
        :param content: Message text.
        """
        self.messages.append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            }
        )
        self.last_accessed = datetime.now()

    def clear_messages(self) -> None:
        """
        Clear conversation messages but keep document references.
        """
        self.messages.clear()
        self.last_accessed = datetime.now()

    def get_messages_by_role(self, role: str) -> List[Dict[str, str]]:
        """
        Get all messages by a specific role.

        :param role: Role to filter on.
        :returns: List of matching messages.
        """
        return [msg for msg in self.messages if msg.get("role") == role]

    def get_recent_messages(self, count: int = 10) -> List[Dict[str, str]]:
        """
        Get the most recent *count* messages.

        :param count: Maximum number of messages to return.
        :returns: List of recent messages.
        """
        return self.messages[-count:] if len(self.messages) > count else self.messages

    def get_user_messages(self) -> List[Dict[str, str]]:
        """
        Get all user messages.

        :returns: List of messages with role ``"user"``.
        """
        return self.get_messages_by_role("user")

    def get_latest_user_message(self) -> Optional[str]:
        """
        Get the content of the most recent user message.

        :returns: Message content string, or *None* if no user messages exist.
        """
        user_messages: List[Dict[str, str]] = self.get_user_messages()
        return user_messages[-1]["content"] if user_messages else None

    def add_uploaded_file(
        self, filename: str, content: str, file_size: int
    ) -> None:
        """
        Register an uploaded file in the session.

        Only the filename and size are tracked in session context; the actual
        content is stored in the vector database via the RAG manager.

        :param filename: Name of the uploaded file.
        :param content: File content (forwarded to RAG, not stored here).
        :param file_size: Size of the file in bytes.
        """
        self.uploaded_files.append(filename)
        self.total_upload_size += file_size

        self.append_message(
            "system",
            f"Document '{filename}' uploaded and processed into vector database",
        )

        try:
            rag_manager = get_rag_manager()
            stats = rag_manager.get_document_stats(self.session_id)
            self.document_chunks_count = stats.get("total_chunks", 0)
        except Exception as e:
            LOG.warning(f"Could not update chunk count: {e}")

    def get_context_size(self) -> int:
        """
        Calculate conversation context size in characters (excluding vector
        DB documents).

        :returns: Total character count across all messages.
        """
        return sum(len(msg["content"]) for msg in self.messages)

    def get_rag_stats(self) -> Dict[str, Any]:
        """
        Get statistics about documents in the vector database for this session.

        :returns: Dictionary with chunk / document counts, or an error entry.
        """
        try:
            rag_manager = get_rag_manager()
            return rag_manager.get_document_stats(self.session_id)
        except Exception as e:
            return {"error": str(e), "total_chunks": 0, "total_documents": 0}

    def clear_all_data(self) -> None:
        """
        Clear both conversation history and vector database documents.
        """
        self.clear_messages()

        try:
            rag_manager = get_rag_manager()
            success: bool = rag_manager.delete_session_documents(
                self.session_id
            )
            if success:
                self.uploaded_files.clear()
                self.total_upload_size = 0
                self.document_chunks_count = 0
                self.append_message(
                    "system",
                    "All conversation history and documents cleared",
                )
            else:
                self.append_message(
                    "system",
                    "Conversation cleared, but some documents may remain",
                )
        except Exception as e:
            self.append_message(
                "system",
                f"Conversation cleared, document cleanup failed: {e}",
            )


class SessionManager:
    """Thread-safe session manager for handling multiple user conversations."""

    def __init__(
        self,
        session_timeout_hours: int = 24,
        cleanup_interval_minutes: int = 60,
    ) -> None:
        self.sessions: Dict[str, ConversationContext] = {}
        self.session_timeout: timedelta = timedelta(hours=session_timeout_hours)
        self.cleanup_interval: timedelta = timedelta(
            minutes=cleanup_interval_minutes
        )
        self.lock: Lock = Lock()
        self.last_cleanup: datetime = datetime.now()

    def create_session(self) -> str:
        """
        Create a new session and return its ID.

        :returns: Newly generated session ID.
        """
        session_id: str = str(uuid.uuid4())
        with self.lock:
            self.sessions[session_id] = ConversationContext(
                session_id=session_id
            )
        return session_id

    def get_session(
        self, session_id: Optional[str] = None
    ) -> ConversationContext:
        """
        Get an existing session or create a new one.

        :param session_id: Session ID to look up. Creates a new session when
            *None* or not found.
        :returns: The matching or newly created :class:`ConversationContext`.
        """
        if not session_id:
            session_id = self.create_session()

        with self.lock:
            if session_id not in self.sessions:
                self.sessions[session_id] = ConversationContext(
                    session_id=session_id
                )

            session: ConversationContext = self.sessions[session_id]
            session.last_accessed = datetime.now()

            self._cleanup_expired_sessions()

            return session

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a specific session.

        :param session_id: Session to remove.
        :returns: *True* if the session existed and was deleted.
        """
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                return True
            return False

    def get_active_session_count(self) -> int:
        """
        Get the number of active sessions.

        :returns: Active session count.
        """
        with self.lock:
            return len(self.sessions)

    def _cleanup_expired_sessions(self) -> None:
        """
        Remove expired sessions (called periodically).
        """
        now: datetime = datetime.now()

        if now - self.last_cleanup < self.cleanup_interval:
            return

        expired_sessions: List[str] = []
        for session_id, session in self.sessions.items():
            if now - session.last_accessed > self.session_timeout:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            del self.sessions[session_id]

        self.last_cleanup = now

        if expired_sessions:
            LOG.info(f"Cleaned up {len(expired_sessions)} expired sessions")

    def reset_session_completely(self, session_id: str) -> bool:
        """
        Completely reset a session — both conversation and vector database
        documents.

        :param session_id: Session to reset.
        :returns: *True* if the session existed and was reset.
        """
        with self.lock:
            if session_id in self.sessions:
                session: ConversationContext = self.sessions[session_id]
                session.clear_all_data()
                return True
            return False

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """
        Get comprehensive session statistics including RAG data.

        :param session_id: Session to query.
        :returns: Dictionary of session and RAG statistics.
        """
        with self.lock:
            if session_id not in self.sessions:
                return {"error": "Session not found"}

            session: ConversationContext = self.sessions[session_id]

            basic_stats: Dict[str, Any] = {
                "session_id": session_id,
                "message_count": len(session.messages),
                "uploaded_files": session.uploaded_files,
                "total_upload_size": session.total_upload_size,
                "context_size_chars": session.get_context_size(),
                "created_at": session.created_at.isoformat(),
                "last_accessed": session.last_accessed.isoformat(),
            }

            rag_stats: Dict[str, Any] = session.get_rag_stats()

            return {**basic_stats, "rag_stats": rag_stats}


session_manager = SessionManager()


def get_session_manager() -> SessionManager:
    """
    Get the global session manager instance.

    :returns: Singleton :class:`SessionManager`.
    """
    return session_manager
