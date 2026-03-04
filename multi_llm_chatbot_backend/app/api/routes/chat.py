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

import asyncio
import json as json_mod
import logging
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.utils import get_or_create_session_for_request_async
from app.core.auth import get_current_active_user
from app.core.bootstrap import chat_orchestrator
from app.core.database import get_database
from app.core.session_manager import get_session_manager
from app.models.default_personas import get_agent_ids
from app.models.persona import Persona
from app.models.user import User

LOG = logging.getLogger(__name__)

router = APIRouter()
SESSION_MANAGER = get_session_manager()


class UserInput(BaseModel):
    """Schema for a simple user message."""

    user_input: str


class ChatMessage(BaseModel):
    """Schema for a chat request with session and advisor options."""

    user_input: str
    session_id: Optional[str] = None
    chat_session_id: Optional[str] = None
    response_length: str = "medium"
    active_advisors: Optional[List[str]] = None
    synthesized: bool = False


class ReplyToAdvisor(BaseModel):
    """Schema for replying to a specific advisor."""

    user_input: str
    advisor_id: str
    original_message_id: str = None
    chat_session_id: Optional[str] = None


class PersonaQuery(BaseModel):
    """Schema for a question directed at a specific persona."""

    question: str
    persona: str


class SwitchChatRequest(BaseModel):
    """Schema for switching to an existing chat session."""

    chat_session_id: str


class NewChatRequest(BaseModel):
    """Schema for creating a new chat session."""

    title: Optional[str] = "New Chat"


@router.post("/switch-chat")
async def switch_to_chat(
    request: SwitchChatRequest,
    req: Request,
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Switch to an existing chat session and load its context.

    Ensures documents are accessible after switching.

    :param request: The switch-chat request body.
    :param req: The raw FastAPI request.
    :param current_user: The authenticated user.
    :returns: A dict with session context, messages, and document access info.
    """
    try:
        LOG.info(f"Switching to chat session: {request.chat_session_id}")

        memory_session_id = await get_or_create_session_for_request_async(
            req,
            chat_session_id=request.chat_session_id,
            user_id=str(current_user.id)
        )

        if not memory_session_id:
            raise HTTPException(status_code=404, detail="Chat session not found")

        LOG.info(f"Loaded chat into memory session: {memory_session_id}")

        session = SESSION_MANAGER.get_session(memory_session_id)

        rag_stats = session.get_rag_stats()
        LOG.info(f"After switch - Session {memory_session_id} has {rag_stats.get('total_documents', 0)} documents")

        db = get_database()
        chat_session = await db.chat_sessions.find_one({
            "_id": ObjectId(request.chat_session_id),
            "user_id": current_user.id,
            "is_active": True
        })

        if not chat_session:
            raise HTTPException(status_code=404, detail="Chat session not found in database")

        original_messages = chat_session.get("messages", [])

        LOG.info(f"Switch successful - {len(original_messages)} messages, {rag_stats.get('total_documents', 0)} documents")

        return {
            "status": "success",
            "memory_session_id": memory_session_id,
            "chat_session_id": request.chat_session_id,
            "message_count": len(original_messages),
            "context": {
                "messages": original_messages,
                "rag_info": rag_stats
            },
            "document_access": {
                "total_documents": rag_stats.get('total_documents', 0),
                "total_chunks": rag_stats.get('total_chunks', 0),
                "documents": rag_stats.get('documents', []),
                "uploaded_files": session.uploaded_files
            },
            "debug_info": {
                "memory_session_format": memory_session_id,
                "documents_accessible": rag_stats.get('total_documents', 0) > 0,
                "session_loaded": memory_session_id in SESSION_MANAGER.sessions
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        LOG.error(f"Error switching to chat {request.chat_session_id}: {e}")
        LOG.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to switch to chat")


@router.post("/new-chat")
async def create_new_chat(
    request: NewChatRequest,
    req: Request,
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Create a new chat with fresh context.

    :param request: The new-chat request body.
    :param req: The raw FastAPI request.
    :param current_user: The authenticated user.
    :returns: A dict with the new session info.
    """
    try:
        memory_session_id = await get_or_create_session_for_request_async(req)

        session = SESSION_MANAGER.get_session(memory_session_id)
        session.clear_all_data()

        return {
            "status": "success",
            "memory_session_id": memory_session_id,
            "message": "New chat created with fresh context",
            "context": {
                "messages": [],
                "rag_info": {"total_documents": 0, "total_chunks": 0}
            }
        }

    except Exception as e:
        LOG.error(f"Error creating new chat: {e}")
        raise HTTPException(status_code=500, detail="Failed to create new chat")


@router.post("/chat-sequential")
async def chat_sequential_enhanced(
    message: ChatMessage,
    request: Request,
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Enhanced sequential chat with proper session management, document access,
    and intelligent persona ordering.

    :param message: The chat message payload.
    :param request: The raw FastAPI request.
    :param current_user: The authenticated user.
    :returns: A dict with advisor responses and session debug info.
    """
    try:
        if message.chat_session_id:
            session_id = f"chat_{message.chat_session_id}"
            LOG.info(f"Using chat session: {session_id}")

            if session_id not in SESSION_MANAGER.sessions:
                LOG.warning(f"Chat session {message.chat_session_id} not in memory, loading now")

                loaded_session_id = await get_or_create_session_for_request_async(
                    request,
                    chat_session_id=message.chat_session_id,
                    user_id=str(current_user.id)
                )

                session_id = loaded_session_id
                LOG.info(f"Loaded session from database: {session_id}")
        else:
            session_id = await get_or_create_session_for_request_async(request)
            LOG.info(f"Using ephemeral session: {session_id}")

        session = SESSION_MANAGER.get_session(session_id)

        rag_stats = session.get_rag_stats()
        LOG.info(f"Session {session_id} has {rag_stats.get('total_documents', 0)} documents available")

        already_in_session = (
            session.messages
            and session.messages[-1].get('role') == 'user'
            and session.messages[-1].get('content') == message.user_input
        )
        if not already_in_session:
            session.append_message("user", message.user_input)

        try:
            db_ref = get_database()
            user_profile = await db_ref.user_profiles.find_one({"user_id": current_user.id})
            if user_profile:
                profile_fields = ["major", "minor", "year", "gpa_range", "career_goals",
                                  "courses_completed", "courses_planned", "schedule_preferences",
                                  "learning_style", "extracurriculars"]
                profile_summary = ", ".join(
                    f"{k}: {user_profile[k]}" for k in profile_fields
                    if user_profile.get(k)
                )
                if profile_summary:
                    session.user_profile_context = f"USER PROFILE: {profile_summary}"
        except Exception as prof_err:
            LOG.warning(f"Could not load user profile: {prof_err}")

        if chat_orchestrator._needs_clarification(session, message.user_input):
            clarification = await chat_orchestrator.generate_contextual_clarification(
                message.user_input
            )
            LOG.info(f"Clarification triggered for input: {message.user_input!r}")
            return {
                "status": "clarification_needed",
                "message": clarification["question"],
                "suggestions": clarification["suggestions"],
                "session_debug": {
                    "session_id": session_id,
                    "trigger": "vague_input"
                }
            }

        query_type = chat_orchestrator.classify_query(message.user_input, session_id=session_id)
        if query_type == "course_db":
            LOG.info("Routing to Course Advisor sub-agent for database query")
            course_response = await chat_orchestrator.handle_course_query(
                user_message=message.user_input,
                session_id=session_id,
                response_length=message.response_length or "medium",
            )
            return {
                "responses": [course_response],
                "session_debug": {
                    "session_id": session_id,
                    "route": "course_db",
                    "documents_available": rag_stats.get('total_documents', 0),
                    "selected_personas": ["course_advisor"],
                    "total_personas_available": len(chat_orchestrator.personas),
                }
            }

        chat_orchestrator._clear_agent_route(session_id)

        _agent_ids = get_agent_ids()
        all_persona_ids = [pid for pid in chat_orchestrator.personas
                           if pid not in _agent_ids]
        if message.active_advisors:
            all_persona_ids = [pid for pid in all_persona_ids if pid in message.active_advisors]

        k = min(3, len(all_persona_ids))
        top_personas = await chat_orchestrator.get_top_personas(
            session_id=session_id,
            k=k,
            allowed_ids=all_persona_ids
        )

        LOG.info(f"Intelligent persona order for session {session_id}: {top_personas}")

        raw_responses = await chat_orchestrator.generate_parallel_responses(
            persona_ids=top_personas,
            session_id=session_id,
            user_input=message.user_input,
            response_length=message.response_length or "medium",
        )

        responses = []
        for r in raw_responses:
            responses.append({
                "persona_id": r["persona_id"],
                "persona_name": r["persona_name"],
                "content": r["response"],
                "used_documents": r.get("used_documents", False),
                "document_chunks_used": r.get("document_chunks_used", 0),
            })

        if message.synthesized and len(responses) > 1:
            synthesized = await chat_orchestrator.synthesize_responses(responses)
            return {
                "responses": [synthesized],
                "session_debug": {
                    "session_id": session_id,
                    "documents_available": rag_stats.get('total_documents', 0),
                    "chunks_available": rag_stats.get('total_chunks', 0),
                    "valid_responses": 1,
                    "selected_personas": top_personas,
                    "synthesized": True,
                    "total_personas_available": len(chat_orchestrator.personas)
                }
            }

        return {
            "responses": responses,
            "session_debug": {
                "session_id": session_id,
                "documents_available": rag_stats.get('total_documents', 0),
                "chunks_available": rag_stats.get('total_chunks', 0),
                "valid_responses": len(responses),
                "selected_personas": top_personas,
                "total_personas_available": len(chat_orchestrator.personas)
            }
        }

    except Exception as e:
        LOG.error(f"Error in chat_sequential_enhanced: {e}")
        LOG.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@router.post("/chat-stream")
async def chat_stream(
    message: ChatMessage,
    request: Request,
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """SSE streaming variant of chat-sequential.

    Sends each advisor response as a server-sent event the moment it is ready,
    so the frontend can display advisors incrementally.

    Event types:

    - ``event: advisor`` -- one advisor's complete response
    - ``event: synthesized`` -- synthesised single answer (when synthesized=true)
    - ``event: done`` -- signals end of stream
    - ``event: error`` -- top-level error
    - ``event: clarification`` -- orchestrator needs clarification

    :param message: The chat message payload.
    :param request: The raw FastAPI request.
    :param current_user: The authenticated user.
    :returns: A streaming response with SSE events.
    """

    async def _event_generator():
        try:
            if message.chat_session_id:
                sid = f"chat_{message.chat_session_id}"
                if sid not in SESSION_MANAGER.sessions:
                    sid = await get_or_create_session_for_request_async(
                        request,
                        chat_session_id=message.chat_session_id,
                        user_id=str(current_user.id),
                    )
            else:
                sid = await get_or_create_session_for_request_async(request)

            session = SESSION_MANAGER.get_session(sid)
            rag_stats = session.get_rag_stats()

            already = (
                session.messages
                and session.messages[-1].get("role") == "user"
                and session.messages[-1].get("content") == message.user_input
            )
            if not already:
                session.append_message("user", message.user_input)

            try:
                db_ref = get_database()
                user_profile = await db_ref.user_profiles.find_one({"user_id": current_user.id})
                if user_profile:
                    pf = ["major", "minor", "year", "gpa_range", "career_goals",
                          "courses_completed", "courses_planned", "schedule_preferences",
                          "learning_style", "extracurriculars"]
                    ps = ", ".join(f"{k}: {user_profile[k]}" for k in pf if user_profile.get(k))
                    if ps:
                        session.user_profile_context = f"USER PROFILE: {ps}"
            except Exception:
                pass

            if chat_orchestrator._needs_clarification(session, message.user_input):
                clar = await chat_orchestrator.generate_contextual_clarification(message.user_input)
                yield f"event: clarification\ndata: {json_mod.dumps({'message': clar['question'], 'suggestions': clar['suggestions']})}\n\n"
                yield "event: done\ndata: {}\n\n"
                return

            query_type = chat_orchestrator.classify_query(message.user_input, session_id=sid)
            if query_type == "course_db":
                cr = await chat_orchestrator.handle_course_query(
                    user_message=message.user_input,
                    session_id=sid,
                    response_length=message.response_length or "medium",
                )
                yield f"event: advisor\ndata: {json_mod.dumps(cr)}\n\n"
                yield "event: done\ndata: {}\n\n"
                return

            chat_orchestrator._clear_agent_route(sid)

            _agent_ids = get_agent_ids()
            all_ids = [pid for pid in chat_orchestrator.personas if pid not in _agent_ids]
            if message.active_advisors:
                all_ids = [pid for pid in all_ids if pid in message.active_advisors]
            k = min(3, len(all_ids))
            top_personas = await chat_orchestrator.get_top_personas(
                session_id=sid, k=k, allowed_ids=all_ids,
            )

            doc_ctx = await chat_orchestrator._retrieve_relevant_documents(
                user_input=message.user_input, session_id=sid, persona_id="",
            )

            is_synthesized = bool(message.synthesized)
            done_queue: asyncio.Queue = asyncio.Queue()

            async def _run(pid: str) -> None:
                persona = chat_orchestrator.get_persona(pid)
                if not persona:
                    return
                result = await chat_orchestrator._generate_single_persona_response(
                    session, persona,
                    message.response_length or "medium",
                    prefetched_document_context=doc_ctx,
                )
                session.append_message(pid, result["response"])
                await done_queue.put(result)

            tasks = [asyncio.create_task(_run(pid)) for pid in top_personas]

            collected = []
            for _ in range(len(tasks)):
                result = await done_queue.get()
                evt = {
                    "persona_id": result["persona_id"],
                    "persona_name": result["persona_name"],
                    "content": result["response"],
                    "used_documents": result.get("used_documents", False),
                    "document_chunks_used": result.get("document_chunks_used", 0),
                }
                collected.append(evt)

                if is_synthesized:
                    yield f"event: progress\ndata: {json_mod.dumps({'persona_id': evt['persona_id'], 'persona_name': evt['persona_name']})}\n\n"
                else:
                    yield f"event: advisor\ndata: {json_mod.dumps(evt)}\n\n"

            await asyncio.gather(*tasks, return_exceptions=True)

            if is_synthesized and len(collected) > 1:
                synth = await chat_orchestrator.synthesize_responses(collected)
                yield f"event: synthesized\ndata: {json_mod.dumps(synth)}\n\n"

            yield "event: done\ndata: {}\n\n"

        except Exception as exc:
            LOG.error(f"chat-stream error: {exc}")
            LOG.error(traceback.format_exc())
            yield f"event: error\ndata: {json_mod.dumps({'detail': str(exc)})}\n\n"

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/{persona_id}")
async def chat_with_specific_advisor(
    persona_id: str,
    input: UserInput,
    request: Request,
) -> Dict[str, Any]:
    """Chat with a specific advisor.

    :param persona_id: The target advisor persona identifier.
    :param input: The user's message payload.
    :param request: The raw FastAPI request.
    :returns: A dict with persona name, id, and response text.
    """
    try:
        if persona_id not in chat_orchestrator.personas:
            raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found")

        session_id = await get_or_create_session_for_request_async(request)

        result = await chat_orchestrator.chat_with_persona(
            user_input=input.user_input,
            persona_id=persona_id,
            session_id=session_id
        )

        if result.get("type") == "single_persona_response" and "persona" in result:
            persona_data = result["persona"]
            return {
                "persona": persona_data["persona_name"],
                "persona_id": persona_data["persona_id"],
                "response": persona_data["response"]
            }
        elif "persona_id" in result and "response" in result:
            return {
                "persona": result["persona_name"],
                "persona_id": result["persona_id"],
                "response": result["response"]
            }
        else:
            return {
                "persona": "System",
                "response": "I'm having trouble generating a response right now. Please try again."
            }

    except HTTPException:
        raise
    except Exception as e:
        LOG.error(f"Error in chat_with_specific_advisor: {e}")
        return {
            "persona": "System",
            "response": "I'm having trouble generating a response right now. Please try again."
        }


@router.post("/reply-to-advisor")
async def reply_to_advisor(
    reply: ReplyToAdvisor,
    request: Request,
) -> Dict[str, Any]:
    """Reply to a specific advisor with proper context.

    :param reply: The reply payload with advisor id and message.
    :param request: The raw FastAPI request.
    :returns: A dict with the advisor's reply and metadata.
    """
    try:
        if reply.advisor_id not in chat_orchestrator.personas:
            raise HTTPException(status_code=404, detail=f"Advisor '{reply.advisor_id}' not found")

        if reply.chat_session_id:
            session_id = f"chat_{reply.chat_session_id}"
        else:
            session_id = await get_or_create_session_for_request_async(request)

        session = SESSION_MANAGER.get_session(session_id)

        original_message = None
        if reply.original_message_id:
            for msg in session.messages:
                if getattr(msg, 'id', None) == reply.original_message_id:
                    original_message = msg.content
                    break

        contextual_input = reply.user_input
        if original_message:
            contextual_input = f"[Replying to your previous message: '{original_message[:100]}...'] {reply.user_input}"

        result = await chat_orchestrator.chat_with_persona(
            user_input=contextual_input,
            persona_id=reply.advisor_id,
            session_id=session_id
        )

        if result.get("type") == "single_persona_response" and "persona" in result:
            persona_data = result["persona"]
            return {
                "type": "advisor_reply",
                "persona": persona_data["persona_name"],
                "persona_id": persona_data["persona_id"],
                "response": persona_data["response"],
                "original_message_id": reply.original_message_id
            }
        elif "persona_id" in result and "response" in result:
            return {
                "type": "advisor_reply",
                "persona": result["persona_name"],
                "persona_id": result["persona_id"],
                "response": result["response"],
                "original_message_id": reply.original_message_id
            }
        else:
            return {
                "type": "error",
                "persona": "System",
                "response": "I'm having trouble generating a reply right now. Please try again."
            }

    except HTTPException:
        raise
    except Exception as e:
        LOG.error(f"Error in reply_to_advisor: {e}")
        return {
            "type": "error",
            "persona": "System",
            "response": "I'm having trouble generating a reply right now. Please try again."
        }


@router.post("/ask/")
async def ask_question(
    query: PersonaQuery,
    request: Request,
) -> Dict[str, Any]:
    """Ask a question directed at a specific persona.

    :param query: The question and target persona.
    :param request: The raw FastAPI request.
    :returns: A dict containing the response text.
    """
    try:
        session_id = await get_or_create_session_for_request_async(request)

        result = await chat_orchestrator.chat_with_persona(
            user_input=query.question,
            persona_id=query.persona,
            session_id=session_id
        )

        if result["type"] == "single_persona_response":
            response_text = result["persona"]["response"]
        else:
            response_text = result.get("message", "I'm having trouble responding right now.")

        return {"response": response_text}

    except Exception as e:
        LOG.error(f"Error in ask endpoint: {e}")
        return {"response": "I encountered an error. Please try again."}
