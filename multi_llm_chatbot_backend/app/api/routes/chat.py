from fastapi import APIRouter, Request, HTTPException, Body, Depends
from fastapi.responses import StreamingResponse
from app.models.persona import Persona
from app.core.session_manager import get_session_manager
from app.api.utils import get_or_create_session_for_request_async
from app.core.bootstrap import chat_orchestrator
from app.core.auth import get_current_active_user
from app.models.user import User
from app.models.default_personas import get_agent_ids
from pydantic import BaseModel
from typing import Optional
import asyncio
import json as json_mod
import logging
from app.core.database import get_database
from bson import ObjectId
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()
session_manager = get_session_manager()

# Enhanced data models
class UserInput(BaseModel):
    user_input: str

class ChatMessage(BaseModel):
    user_input: str
    session_id: Optional[str] = None
    chat_session_id: Optional[str] = None
    response_length: str = "medium"
    active_advisors: Optional[list] = None
    synthesized: bool = False

class ReplyToAdvisor(BaseModel):
    user_input: str
    advisor_id: str
    original_message_id: str = None
    chat_session_id: Optional[str] = None

class PersonaQuery(BaseModel):
    question: str
    persona: str

class SwitchChatRequest(BaseModel):
    chat_session_id: str

class NewChatRequest(BaseModel):
    title: Optional[str] = "New Chat"

@router.post("/switch-chat")
async def switch_to_chat(
    request: SwitchChatRequest, 
    req: Request,
    current_user: User = Depends(get_current_active_user)
):
    """
    Switch to an existing chat session and load its context - FIXED VERSION
    Ensures documents are accessible after switching
    """
    try:
        logger.info(f"Switching to chat session: {request.chat_session_id}")
        
        # Load the chat session into memory context with consistent session ID
        memory_session_id = await get_or_create_session_for_request_async(
            req, 
            chat_session_id=request.chat_session_id,
            user_id=str(current_user.id)
        )
        
        if not memory_session_id:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        logger.info(f"Loaded chat into memory session: {memory_session_id}")
        
        # Get the loaded session
        session = session_manager.get_session(memory_session_id)
        
        # Verify document access after loading
        rag_stats = session.get_rag_stats()
        logger.info(f"After switch - Session {memory_session_id} has {rag_stats.get('total_documents', 0)} documents")
        
        # Get the original MongoDB chat session to retrieve messages in proper format
        db = get_database()
        chat_session = await db.chat_sessions.find_one({
            "_id": ObjectId(request.chat_session_id),
            "user_id": current_user.id,
            "is_active": True
        })
        
        if not chat_session:
            raise HTTPException(status_code=404, detail="Chat session not found in database")
        
        # Return the messages in the original frontend format from MongoDB
        original_messages = chat_session.get("messages", [])
        
        logger.info(f"Switch successful - {len(original_messages)} messages, {rag_stats.get('total_documents', 0)} documents")
        
        return {
            "status": "success",
            "memory_session_id": memory_session_id,
            "chat_session_id": request.chat_session_id,
            "message_count": len(original_messages),
            "context": {
                "messages": original_messages,  # Return original format messages
                "rag_info": rag_stats
            },
            # Include document access verification
            "document_access": {
                "total_documents": rag_stats.get('total_documents', 0),
                "total_chunks": rag_stats.get('total_chunks', 0),
                "documents": rag_stats.get('documents', []),
                "uploaded_files": session.uploaded_files
            },
            "debug_info": {
                "memory_session_format": memory_session_id,
                "documents_accessible": rag_stats.get('total_documents', 0) > 0,
                "session_loaded": memory_session_id in session_manager.sessions
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching to chat {request.chat_session_id}: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to switch to chat")

@router.post("/new-chat")
async def create_new_chat(
    request: NewChatRequest,
    req: Request,
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new chat with fresh context
    """
    try:
        # Create a completely new session (no chat_session_id means fresh context)
        memory_session_id = await get_or_create_session_for_request_async(req)
        
        # Ensure the session is completely clean
        session = session_manager.get_session(memory_session_id)
        session.clear_all_data()  # This clears both messages and documents
        
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
        logger.error(f"Error creating new chat: {e}")
        raise HTTPException(status_code=500, detail="Failed to create new chat")

@router.post("/chat-sequential")
async def chat_sequential_enhanced(
    message: ChatMessage, 
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """
    Enhanced sequential chat with proper session management, document access, and intelligent persona ordering
    """
    try:
        # Ensure consistent session ID for document retrieval
        if message.chat_session_id:
            # Use the memory session format that matches document storage
            session_id = f"chat_{message.chat_session_id}"
            logger.info(f"Using chat session: {session_id}")
            
            # FIXED: Ensure session exists in memory (load if needed)
            if session_id not in session_manager.sessions:
                logger.warning(f"Chat session {message.chat_session_id} not in memory, loading now")
                
                # FIXED: Pass the user_id parameter to properly load existing session
                loaded_session_id = await get_or_create_session_for_request_async(
                    request, 
                    chat_session_id=message.chat_session_id,
                    user_id=str(current_user.id)
                )
                
                # Use the loaded session ID
                session_id = loaded_session_id
                logger.info(f"Loaded session from database: {session_id}")
        else:
            # No specific chat session, create/use ephemeral session
            session_id = await get_or_create_session_for_request_async(request)
            logger.info(f"Using ephemeral session: {session_id}")

        # Get session from memory
        session = session_manager.get_session(session_id)
        
        # Log session debugging info
        rag_stats = session.get_rag_stats()
        logger.info(f"Session {session_id} has {rag_stats.get('total_documents', 0)} documents available")
        
        # The frontend saves the user message to MongoDB BEFORE calling
        # this endpoint.  If the session was just loaded from MongoDB the
        # message is already present; if the session was already in
        # memory it isn't.  We ensure it exists exactly once so the
        # first-message check in _needs_clarification is reliable.
        already_in_session = (
            session.messages
            and session.messages[-1].get('role') == 'user'
            and session.messages[-1].get('content') == message.user_input
        )
        if not already_in_session:
            session.append_message("user", message.user_input)
        
        # Load user profile as persistent memory context
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
            logger.warning(f"Could not load user profile: {prof_err}")

        # Check if the user's message is vague and needs clarification
        if chat_orchestrator._needs_clarification(session, message.user_input):
            clarification = await chat_orchestrator.generate_contextual_clarification(
                message.user_input
            )
            logger.info(f"Clarification triggered for input: {message.user_input!r}")
            return {
                "status": "clarification_needed",
                "message": clarification["question"],
                "suggestions": clarification["suggestions"],
                "session_debug": {
                    "session_id": session_id,
                    "trigger": "vague_input"
                }
            }

        # ── Orchestrator routing: detect specialist queries ──────────
        query_type = chat_orchestrator.classify_query(message.user_input, session_id=session_id)
        if query_type == "course_db":
            logger.info("Routing to Course Advisor sub-agent for database query")
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

        # Routed to general panel — clear any specialist follow-up state
        chat_orchestrator._clear_agent_route(session_id)

        # Get intelligently ordered personas based on context.
        # Exclude agent-type personas — they are invoked via specialist routing only.
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
        
        logger.info(f"Intelligent persona order for session {session_id}: {top_personas}")
        
        # Generate responses from all selected personas in PARALLEL
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
        
        # Synthesized mode: combine all advisor responses into one
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
        logger.error(f"Error in chat_sequential_enhanced: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@router.post("/chat-stream")
async def chat_stream(
    message: ChatMessage,
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    """
    SSE streaming variant of chat-sequential.
    Sends each advisor response as a server-sent event the moment it's ready,
    so the frontend can display advisors incrementally.

    Event types:
      - event: advisor   → one advisor's complete response
      - event: synthesized → synthesized single answer (when synthesized=true)
      - event: done      → signals end of stream
      - event: error     → top-level error
      - event: clarification → orchestrator needs clarification
    """

    async def _event_generator():
        try:
            # ── session setup (same as chat-sequential) ──────────
            if message.chat_session_id:
                sid = f"chat_{message.chat_session_id}"
                if sid not in session_manager.sessions:
                    sid = await get_or_create_session_for_request_async(
                        request,
                        chat_session_id=message.chat_session_id,
                        user_id=str(current_user.id),
                    )
            else:
                sid = await get_or_create_session_for_request_async(request)

            session = session_manager.get_session(sid)
            rag_stats = session.get_rag_stats()

            already = (
                session.messages
                and session.messages[-1].get("role") == "user"
                and session.messages[-1].get("content") == message.user_input
            )
            if not already:
                session.append_message("user", message.user_input)

            # Load user profile
            try:
                db_ref = get_database()
                user_profile = await db_ref.user_profiles.find_one({"user_id": current_user.id})
                if user_profile:
                    pf = ["major","minor","year","gpa_range","career_goals",
                          "courses_completed","courses_planned","schedule_preferences",
                          "learning_style","extracurriculars"]
                    ps = ", ".join(f"{k}: {user_profile[k]}" for k in pf if user_profile.get(k))
                    if ps:
                        session.user_profile_context = f"USER PROFILE: {ps}"
            except Exception:
                pass

            # ── clarification check ──────────────────────────────
            if chat_orchestrator._needs_clarification(session, message.user_input):
                clar = await chat_orchestrator.generate_contextual_clarification(message.user_input)
                yield f"event: clarification\ndata: {json_mod.dumps({'message': clar['question'], 'suggestions': clar['suggestions']})}\n\n"
                yield "event: done\ndata: {}\n\n"
                return

            # ── specialist routing ───────────────────────────────
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

            # Routed to general panel — clear specialist follow-up state
            chat_orchestrator._clear_agent_route(sid)

            # ── persona selection ────────────────────────────────
            _agent_ids = get_agent_ids()
            all_ids = [pid for pid in chat_orchestrator.personas if pid not in _agent_ids]
            if message.active_advisors:
                all_ids = [pid for pid in all_ids if pid in message.active_advisors]
            k = min(3, len(all_ids))
            top_personas = await chat_orchestrator.get_top_personas(
                session_id=sid, k=k, allowed_ids=all_ids,
            )

            # ── shared RAG retrieval ─────────────────────────────
            doc_ctx = await chat_orchestrator._retrieve_relevant_documents(
                user_input=message.user_input, session_id=sid, persona_id="",
            )

            # ── launch all personas concurrently, stream as each finishes ──
            is_synthesized = bool(message.synthesized)
            done_queue: asyncio.Queue = asyncio.Queue()

            async def _run(pid: str):
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
                    # In synthesized mode, send lightweight progress so the
                    # frontend can update the thinking indicator without
                    # displaying individual advisor messages.
                    yield f"event: progress\ndata: {json_mod.dumps({'persona_id': evt['persona_id'], 'persona_name': evt['persona_name']})}\n\n"
                else:
                    yield f"event: advisor\ndata: {json_mod.dumps(evt)}\n\n"

            await asyncio.gather(*tasks, return_exceptions=True)

            if is_synthesized and len(collected) > 1:
                synth = await chat_orchestrator.synthesize_responses(collected)
                yield f"event: synthesized\ndata: {json_mod.dumps(synth)}\n\n"

            yield "event: done\ndata: {}\n\n"

        except Exception as exc:
            logger.error("chat-stream error: %s", exc)
            import traceback
            logger.error(traceback.format_exc())
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
async def chat_with_specific_advisor(persona_id: str, input: UserInput, request: Request):
    """Chat with a specific advisor - UPDATED"""
    try:
        if persona_id not in chat_orchestrator.personas:
            raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found")

        # Use async session management
        session_id = await get_or_create_session_for_request_async(request)
        
        result = await chat_orchestrator.chat_with_persona(
            user_input=input.user_input,
            persona_id=persona_id,
            session_id=session_id
        )
        
        # Handle response structure
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
        logger.error(f"Error in chat_with_specific_advisor: {e}")
        return {
            "persona": "System",
            "response": "I'm having trouble generating a response right now. Please try again."
        }

@router.post("/reply-to-advisor")
async def reply_to_advisor(reply: ReplyToAdvisor, request: Request):
    """Reply to a specific advisor with proper context - UPDATED"""
    try:
        if reply.advisor_id not in chat_orchestrator.personas:
            raise HTTPException(status_code=404, detail=f"Advisor '{reply.advisor_id}' not found")

        # Handle session management for existing chats
        if reply.chat_session_id:
            session_id = f"chat_{reply.chat_session_id}"
        else:
            session_id = await get_or_create_session_for_request_async(request)
        
        session = session_manager.get_session(session_id)
        
        # Find the original message being replied to for context
        original_message = None
        if reply.original_message_id:
            for msg in session.messages:
                if getattr(msg, 'id', None) == reply.original_message_id:
                    original_message = msg.content
                    break
        
        # Create context-aware input
        contextual_input = reply.user_input
        if original_message:
            contextual_input = f"[Replying to your previous message: '{original_message[:100]}...'] {reply.user_input}"
        
        result = await chat_orchestrator.chat_with_persona(
            user_input=contextual_input,
            persona_id=reply.advisor_id,
            session_id=session_id
        )
        
        # Handle response structure
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
        logger.error(f"Error in reply_to_advisor: {e}")
        return {
            "type": "error",
            "persona": "System",
            "response": "I'm having trouble generating a reply right now. Please try again."
        }

@router.post("/ask/")
async def ask_question(query: PersonaQuery, request: Request):
    """Ask question - UPDATED"""
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
        logger.error(f"Error in ask endpoint: {str(e)}")
        return {"response": "I encountered an error. Please try again."}