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
import traceback
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.api.utils import get_or_create_session_for_request_async
from app.core.auth import get_current_active_user
from app.core.session_manager import get_session_manager
from app.models.user import User

LOG = logging.getLogger(__name__)

router = APIRouter()
SESSION_MANAGER = get_session_manager()


class ResetSessionRequest(BaseModel):
    chat_session_id: Optional[str] = None
    force_new: bool = False

@router.get("/context")
async def get_context(
    request: Request,
    chat_session_id: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """
    Get context for current session - ENHANCED with document access fix
    Now properly handles different chat sessions and ensures document access
    """
    try:
        if chat_session_id:
            session_id = f"chat_{chat_session_id}"
            LOG.info(f"Getting context for specific chat session: {session_id}")
            
            if session_id not in SESSION_MANAGER.sessions:
                LOG.info(f"Chat session {session_id} not in memory, loading from database")
                loaded_session_id = await get_or_create_session_for_request_async(
                    request,
                    chat_session_id=chat_session_id,
                    user_id=str(current_user.id)
                )
                session_id = loaded_session_id
                LOG.info(f"Loaded session ID: {session_id}")
        else:
            session_id = await get_or_create_session_for_request_async(request)
            LOG.info(f"Getting context for current session: {session_id}")
        
        session = SESSION_MANAGER.get_session(session_id)
        rag_stats = session.get_rag_stats()
        
        LOG.info(f"Retrieved context for session {session_id}:")
        LOG.info(f"  - Messages: {len(session.messages)}")
        LOG.info(f"  - Documents: {rag_stats.get('total_documents', 0)}")
        LOG.info(f"  - Chunks: {rag_stats.get('total_chunks', 0)}")
        LOG.info(f"  - Uploaded files: {len(session.uploaded_files)}")
        
        if rag_stats.get('documents'):
            for doc in rag_stats['documents']:
                LOG.info(f"  - Available document: {doc.get('filename', 'unknown')} ({doc.get('chunks', 0)} chunks)")
        
        context_response = {
            "session_id": session_id,
            "chat_session_id": chat_session_id,
            "messages": session.messages,
            "rag_info": {
                "total_documents": rag_stats.get("total_documents", 0),
                "total_chunks": rag_stats.get("total_chunks", 0),
                "documents": rag_stats.get("documents", [])
            },
            "context_stats": {
                "message_count": len(session.messages),
                "user_messages": len([m for m in session.messages if m.get('role') == 'user']),
                "uploaded_files": session.uploaded_files,
                "total_upload_size": session.total_upload_size,
                "created_at": session.created_at.isoformat(),
                "last_accessed": session.last_accessed.isoformat()
            },
            "debug_info": {
                "session_format": "chat_session" if chat_session_id else "new_session",
                "session_in_memory": session_id in SESSION_MANAGER.sessions,
                "document_access_working": rag_stats.get("total_documents", 0) > 0
            }
        }
        
        return context_response
        
    except Exception as e:
        LOG.error(f"Error getting context for session_id {session_id if 'session_id' in locals() else 'unknown'}: {str(e)}")
        LOG.error(f"Chat session ID: {chat_session_id}")
        LOG.error(f"Full traceback: {traceback.format_exc()}")
        
        return {
            "session_id": session_id if 'session_id' in locals() else None,
            "chat_session_id": chat_session_id,
            "messages": [], 
            "rag_info": {"total_documents": 0, "total_chunks": 0, "documents": []},
            "context_stats": {
                "message_count": 0,
                "user_messages": 0,
                "uploaded_files": [],
                "total_upload_size": 0
            },
            "error": str(e),
            "debug_info": {
                "error_occurred": True,
                "error_type": type(e).__name__
            }
        }

@router.post("/reset-session")
async def reset_session(
    reset_request: ResetSessionRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """
    Reset session - ENHANCED
    Now properly handles different reset scenarios
    """
    try:
        if reset_request.force_new:
            session_id = SESSION_MANAGER.create_session()
            session = SESSION_MANAGER.get_session(session_id)
            session.clear_all_data()
            
            LOG.info(f"Force created new session: {session_id}")
            
            return {
                "status": "reset", 
                "message": "New session created with fresh context",
                "session_id": session_id,
                "chat_session_id": None
            }
        
        elif reset_request.chat_session_id:
            session_id = f"chat_{reset_request.chat_session_id}"
            
            if session_id in SESSION_MANAGER.sessions:
                success = SESSION_MANAGER.reset_session_completely(session_id)
                message = "Chat session context reset successfully" if success else "Failed to reset chat session context"
            else:
                session = SESSION_MANAGER.get_session(session_id)
                session.clear_all_data()
                success = True
                message = "Fresh context created for chat session"
            
            LOG.info(f"Reset chat session {reset_request.chat_session_id}, memory session: {session_id}")
            
            return {
                "status": "reset" if success else "error",
                "message": message,
                "session_id": session_id,
                "chat_session_id": reset_request.chat_session_id
            }
        
        else:
            session_id = await get_or_create_session_for_request_async(request)
            success = SESSION_MANAGER.reset_session_completely(session_id)
            
            LOG.info(f"Reset current session: {session_id}")
            
            return {
                "status": "reset" if success else "error",
                "message": "Current session reset successfully" if success else "Failed to reset current session",
                "session_id": session_id
            }
            
    except Exception as e:
        LOG.error(f"Error resetting session: {e}")
        return {"status": "error", "message": f"Failed to reset session: {str(e)}"}

@router.get("/session-stats")
async def get_session_stats(
    request: Request,
    chat_session_id: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """
    Get session statistics - ENHANCED
    Now provides detailed stats for different session types
    """
    try:
        if chat_session_id:
            session_id = f"chat_{chat_session_id}"
        else:
            session_id = await get_or_create_session_for_request_async(request)
        
        stats = SESSION_MANAGER.get_session_stats(session_id)
        
        stats["session_type"] = "chat_session" if chat_session_id else "current_session"
        stats["chat_session_id"] = chat_session_id
        
        return stats
        
    except Exception as e:
        LOG.error(f"Error getting session stats: {str(e)}")
        return {"error": str(e)}

@router.get("/active-sessions")
async def get_active_sessions(current_user: User = Depends(get_current_active_user)) -> dict:
    """
    Get all active sessions for debugging
    """
    try:
        active_count = SESSION_MANAGER.get_active_session_count()
        
        session_overview = {}
        for session_id, session in SESSION_MANAGER.sessions.items():
            session_overview[session_id] = {
                "message_count": len(session.messages),
                "uploaded_files": len(session.uploaded_files),
                "created_at": session.created_at.isoformat(),
                "last_accessed": session.last_accessed.isoformat(),
                "is_chat_session": session_id.startswith("chat_")
            }
        
        return {
            "active_session_count": active_count,
            "sessions": session_overview
        }
        
    except Exception as e:
        LOG.error(f"Error getting active sessions: {str(e)}")
        return {"error": str(e)}

@router.post("/cleanup-sessions")
async def cleanup_expired_sessions(current_user: User = Depends(get_current_active_user)) -> dict:
    """
    Manually trigger session cleanup
    """
    try:
        initial_count = SESSION_MANAGER.get_active_session_count()
        
        SESSION_MANAGER._cleanup_expired_sessions()
        
        final_count = SESSION_MANAGER.get_active_session_count()
        cleaned_count = initial_count - final_count
        
        return {
            "status": "success",
            "message": f"Cleaned up {cleaned_count} expired sessions",
            "sessions_before": initial_count,
            "sessions_after": final_count
        }
        
    except Exception as e:
        LOG.error(f"Error during session cleanup: {str(e)}")
        return {"status": "error", "message": str(e)}
