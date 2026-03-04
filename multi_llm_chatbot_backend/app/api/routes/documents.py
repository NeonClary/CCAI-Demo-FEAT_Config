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
import re
import string
from html import unescape
from typing import Dict, List, Optional, Union

from bson import ObjectId
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import StreamingResponse

from app.api.utils import get_or_create_session_for_request_async
from app.core.auth import get_current_active_user
from app.core.bootstrap import chat_orchestrator
from app.core.database import get_database
from app.core.rag_manager import get_rag_manager
from app.core.session_manager import get_session_manager
from app.models.user import User
from app.utils.chat_summary import (
    format_summary_for_text_export,
    generate_summary_from_messages,
    parse_summary_to_blocks,
)
from app.utils.document_extractor import extract_text_from_file
from app.utils.file_export import generate_pdf_file_from_blocks, prepare_export_response

LOG = logging.getLogger(__name__)

router = APIRouter()

SESSION_MANAGER = get_session_manager()


def sanitize_html_content(content: Optional[str]) -> Optional[str]:
    """
    Clean up HTML content by removing or fixing malformed tags.
    This prevents PDF export errors caused by invalid HTML structure.
    """
    if not content:
        return content

    try:
        LOG.debug(f"Sanitizing content (first 200 chars): {content[:200]}")

        content = unescape(content)

        content = re.sub(r'<[^>]*>', '', content)

        content = re.sub(r'\s+', ' ', content)
        content = content.strip()

        content = re.sub(r'&[a-zA-Z0-9#]+;', '', content)

        content = content.replace('<', '').replace('>', '')

        LOG.debug(f"Sanitized content (first 200 chars): {content[:200]}")
        return content

    except Exception as e:
        LOG.error(f"Error sanitizing HTML content: {str(e)}")
        try:
            allowed_chars = string.ascii_letters + string.digits + string.punctuation + ' \n\r\t'
            cleaned = ''.join(c for c in content if c in allowed_chars)
            return re.sub(r'\s+', ' ', cleaned).strip()
        except:
            return "Content could not be sanitized for export"


def convert_messages_for_export(messages: List[dict]) -> List[dict]:
    """
    Convert stored message format to export-compatible format.
    Stored format uses 'type', export functions expect 'role' and specific structure.
    """
    converted_messages: List[dict] = []

    for i, msg in enumerate(messages):
        try:
            raw_content = msg.get('content', '')
            sanitized_content = sanitize_html_content(raw_content)

            if i < 5 or '<' in raw_content or '>' in raw_content:
                LOG.debug(f"Message {i}: Original length: {len(raw_content)}, Sanitized length: {len(sanitized_content)}")
                if raw_content != sanitized_content:
                    LOG.debug(f"Content changed during sanitization for message {msg.get('id', 'unknown')}")

            converted_msg: Dict[str, str] = {
                'id': msg.get('id', 'unknown'),
                'timestamp': msg.get('timestamp', ''),
                'content': sanitized_content,
            }

            msg_type = msg.get('type', 'unknown')

            if msg_type == 'user':
                converted_msg['role'] = 'user'
                if 'replyTo' in msg:
                    reply_to = msg['replyTo']
                    converted_msg['content'] = f"[Reply to {reply_to.get('advisorName', 'advisor')}] {converted_msg['content']}"

            elif msg_type == 'advisor':
                converted_msg['role'] = 'assistant'
                advisor_name = msg.get('advisorName', msg.get('persona', 'Advisor'))
                converted_msg['advisor_name'] = advisor_name
                converted_msg['advisor_id'] = msg.get('advisorId', msg.get('persona_id', 'unknown'))

                if msg.get('isReply'):
                    converted_msg['content'] = f"[{advisor_name} replies] {converted_msg['content']}"
                elif msg.get('isExpansion'):
                    converted_msg['content'] = f"[{advisor_name} expands] {converted_msg['content']}"
                else:
                    converted_msg['content'] = f"[{advisor_name}] {converted_msg['content']}"

            elif msg_type == 'system':
                converted_msg['role'] = 'system'

            elif msg_type == 'document_upload':
                converted_msg['role'] = 'system'
                converted_msg['content'] = f"\U0001f4c4 {converted_msg['content']}"

            elif msg_type == 'error':
                converted_msg['role'] = 'system'
                converted_msg['content'] = f"\u274c Error: {converted_msg['content']}"

            else:
                converted_msg['role'] = 'system'
                converted_msg['content'] = f"[{msg_type}] {converted_msg['content']}"

            converted_messages.append(converted_msg)

        except Exception as e:
            LOG.error(f"Error converting message {msg.get('id', 'unknown')}: {str(e)}")
            converted_messages.append({
                'id': msg.get('id', 'unknown'),
                'role': 'system',
                'content': f"[Message conversion error: {str(e)}]",
                'timestamp': msg.get('timestamp', '')
            })

    LOG.info(f"Converted {len(messages)} messages for export")
    return converted_messages


@router.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    request: Request = None,
    chat_session_id: str = Query(None, description="Chat session ID if uploading to specific chat"),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    try:
        if chat_session_id:
            session_id = f"chat_{chat_session_id}"
            LOG.info(f"Uploading document to specific chat session: {session_id}")
        else:
            session_id = await get_or_create_session_for_request_async(request)
            LOG.info(f"Uploading document to new session: {session_id}")

        LOG.info(f"Document upload - chat_session_id parameter: {chat_session_id}")
        LOG.info(f"Document upload - final session_id: {session_id}")
        LOG.info(f"Document upload - user_id: {current_user.id}")

        session = SESSION_MANAGER.get_session(session_id)

        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        if file.size and file.size > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File size exceeds 10MB limit")

        file_bytes = await file.read()
        content = extract_text_from_file(file_bytes, file.content_type)
        if not content.strip():
            raise HTTPException(status_code=400, detail="Document is empty or unreadable.")

        rag_manager = get_rag_manager()
        file_type_map = {
            "application/pdf": "pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
            "text/plain": "txt"
        }
        file_type = file_type_map.get(file.content_type, "unknown")

        LOG.info(f"Adding document {file.filename} to session {session_id}")
        rag_result = rag_manager.add_document(
            content=content,
            filename=file.filename,
            session_id=session_id,
            file_type=file_type
        )

        if not rag_result["success"]:
            raise HTTPException(status_code=500, detail=f"Failed to process document: {rag_result.get('error', 'Unknown error')}")

        session.uploaded_files.append(file.filename)
        session.total_upload_size += len(file_bytes)

        doc_metadata = rag_result.get("document_metadata", {})
        doc_title = doc_metadata.get("title", file.filename)

        session.append_message(
            "system",
            f"Document uploaded: '{doc_title}' ({file.filename}) - {rag_result['chunks_created']} sections processed, ~{rag_result['total_tokens']} tokens analyzed. You can now ask questions about this document by referencing it by name."
        )

        return {
            "message": f"Document '{file.filename}' uploaded and processed successfully.",
            "filename": file.filename,
            "document_title": doc_title,
            "chunks_created": rag_result['chunks_created'],
            "total_tokens": rag_result['total_tokens'],
            "file_type": file_type,
            "can_reference_by_name": True,
            "session_id": session_id,
            "chat_session_id": chat_session_id,
            "user_id": str(current_user.id)
        }

    except HTTPException:
        raise
    except Exception as e:
        LOG.error(f"Error processing document upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")


@router.post("/search-documents")
async def search_documents(
    request: Request,
    query: str = Body(..., embed=True),
    persona: str = Body("", embed=True),
) -> dict:
    try:
        session_id = await get_or_create_session_for_request_async(request)
        rag_manager = get_rag_manager()

        persona_contexts = {
            "methodologist": "methodology research design analysis",
            "theorist": "theory theoretical framework conceptual",
            "pragmatist": "practical application implementation"
        }
        persona_context = persona_contexts.get(persona, "")

        results = rag_manager.search_documents(
            query=query,
            session_id=session_id,
            persona_context=persona_context,
            n_results=5
        )

        return {
            "query": query,
            "persona_filter": persona,
            "results_count": len(results),
            "results": results
        }

    except Exception as e:
        LOG.error(f"Error searching documents: {str(e)}")
        return {"query": query, "results_count": 0, "results": [], "error": str(e)}


@router.get("/document-stats")
async def get_document_stats(request: Request) -> dict:
    try:
        session_id = await get_or_create_session_for_request_async(request)
        rag_manager = get_rag_manager()
        return rag_manager.get_document_stats(session_id)
    except Exception as e:
        LOG.error(f"Error getting document stats: {str(e)}")
        return {"total_chunks": 0, "total_documents": 0, "documents": []}


@router.get("/uploaded-files")
async def get_uploaded_filenames(request: Request) -> dict:
    try:
        session_id = await get_or_create_session_for_request_async(request)
        session = SESSION_MANAGER.get_session(session_id)
        return {"files": session.uploaded_files}
    except Exception as e:
        LOG.error(f"Error getting uploaded files: {str(e)}")
        return {"files": []}


@router.get("/document-insights/{filename}")
async def get_document_insights(filename: str, request: Request) -> dict:
    try:
        session_id = await get_or_create_session_for_request_async(request)
        rag_manager = get_rag_manager()
        stats = rag_manager.get_document_stats(session_id)
        document_info = next((doc for doc in stats.get("documents", []) if doc["filename"] == filename), None)

        if not document_info:
            raise HTTPException(status_code=404, detail=f"Document {filename} not found")

        results = rag_manager.collection.get(
            where={"session_id": session_id, "filename": filename},
            limit=3,
            include=["documents", "metadatas"]
        )

        sample_sections: List[dict] = []
        if results["documents"]:
            for doc, metadata in zip(results["documents"], results["metadatas"]):
                sample_sections.append({
                    "section": metadata.get("document_section", "unknown"),
                    "content_preview": doc[:200] + "..." if len(doc) > 200 else doc,
                    "keywords": metadata.get("keywords", "")
                })

        return {
            "filename": filename,
            "document_title": document_info.get("title", filename),
            "file_type": document_info.get("file_type", "unknown"),
            "statistics": {
                "total_chunks": document_info["chunks"],
                "estimated_tokens": document_info["estimated_tokens"],
                "sections_identified": document_info["sections"]
            },
            "content_analysis": {
                "has_methodology": document_info.get("has_methodology", False),
                "has_theory": document_info.get("has_theory", False),
                "has_references": document_info.get("has_references", False)
            },
            "sample_sections": sample_sections
        }

    except HTTPException:
        raise
    except Exception as e:
        LOG.error(f"Error getting document insights: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing document: {str(e)}")


@router.get("/export-chat", response_model=None)
async def export_chat(
    request: Request,
    format: str = Query(..., regex="^(txt|pdf|docx)$"),
    chat_session_id: str = Query(None, description="Optional: specific chat session ID to export"),
    current_user: User = Depends(get_current_active_user),
) -> Union[dict, StreamingResponse]:
    """
    Export chat messages.
    If chat_session_id is provided, exports that specific stored chat session.
    Otherwise, exports the current in-memory session.
    """
    try:
        messages: List[dict] = []

        if chat_session_id:
            db = get_database()
            session_data = await db.chat_sessions.find_one({
                "_id": ObjectId(chat_session_id),
                "user_id": current_user.id,
                "is_active": True
            })

            if not session_data:
                raise HTTPException(
                    status_code=404,
                    detail="Chat session not found or you don't have permission to access it"
                )

            raw_messages = session_data.get("messages", [])
            messages = convert_messages_for_export(raw_messages)
        else:
            session_id = await get_or_create_session_for_request_async(request)
            session = SESSION_MANAGER.get_session(session_id)
            messages = convert_messages_for_export(session.messages)

        if not messages:
            return {"error": "No messages in this session."}

        try:
            return prepare_export_response(messages, format)
        except Exception as export_error:
            LOG.error(f"Error in prepare_export_response: {str(export_error)}")
            try:
                simplified_messages: List[dict] = []
                for msg in messages:
                    simplified_msg: Dict[str, str] = {
                        'id': msg.get('id', 'unknown'),
                        'role': msg.get('role', 'system'),
                        'content': str(msg.get('content', '')).replace('\n', ' ').strip(),
                        'timestamp': msg.get('timestamp', '')
                    }
                    if 'advisor_name' in msg:
                        simplified_msg['advisor_name'] = msg['advisor_name']
                    simplified_messages.append(simplified_msg)

                return prepare_export_response(simplified_messages, format)
            except Exception as fallback_error:
                LOG.error(f"Fallback export also failed: {str(fallback_error)}")
                raise HTTPException(
                    status_code=500,
                    detail="Export failed due to content formatting issues. Please try a different format or contact support."
                )

    except HTTPException:
        raise
    except Exception as e:
        LOG.error(f"Error exporting chat: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export chat: {str(e)}"
        )


@router.get("/chat-summary", response_model=None)
async def chat_summary(
    request: Request,
    format: str = Query("text", regex="^(txt|pdf|docx)$"),
    chat_session_id: str = Query(None, description="Optional: specific chat session ID to summarize"),
    current_user: User = Depends(get_current_active_user),
) -> Union[dict, StreamingResponse]:
    """
    Generate and return a summary of chat messages.
    If chat_session_id is provided, summarizes that specific stored chat session.
    Otherwise, summarizes the current in-memory session.
    Can return as plain txt, PDF, or DOCX.
    """
    try:
        messages: List[dict] = []

        if chat_session_id:
            db = get_database()
            session_data = await db.chat_sessions.find_one({
                "_id": ObjectId(chat_session_id),
                "user_id": current_user.id,
                "is_active": True
            })

            if not session_data:
                raise HTTPException(
                    status_code=404,
                    detail="Chat session not found or you don't have permission to access it"
                )

            raw_messages = session_data.get("messages", [])
            messages = convert_messages_for_export(raw_messages)
        else:
            session_id = await get_or_create_session_for_request_async(request)
            session = SESSION_MANAGER.get_session(session_id)
            messages = convert_messages_for_export(session.messages)

        if not messages:
            return {"error": "No messages in this session."}

        try:
            llm = next(iter(chat_orchestrator.personas.values())).llm
            summary_text = await generate_summary_from_messages(messages, llm)

            if format == "txt":
                formatted_summary = format_summary_for_text_export(summary_text)
                return prepare_export_response(formatted_summary, "txt", filename_prefix="chat_summary")

            elif format == "docx":
                formatted_summary = format_summary_for_text_export(summary_text)
                return prepare_export_response(formatted_summary, "docx", filename_prefix="chat_summary")

            elif format == "pdf":
                blocks = [{"type": "heading", "text": "Chat Summary"}] + parse_summary_to_blocks(summary_text)

                file_stream = generate_pdf_file_from_blocks(blocks)
                return StreamingResponse(
                    file_stream,
                    media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=chat_summary.pdf"}
                )
        except Exception as summary_error:
            LOG.error(f"Error generating summary: {str(summary_error)}")
            try:
                basic_summary = "Chat Summary\n\n"
                for msg in messages:
                    if msg.get('role') == 'user':
                        basic_summary += f"User: {msg.get('content', '')[:200]}...\n\n"
                    elif msg.get('role') == 'assistant':
                        advisor_name = msg.get('advisor_name', 'Advisor')
                        basic_summary += f"{advisor_name}: {msg.get('content', '')[:200]}...\n\n"

                if format == "txt":
                    return prepare_export_response(basic_summary, "txt", filename_prefix="chat_summary")
                elif format == "docx":
                    return prepare_export_response(basic_summary, "docx", filename_prefix="chat_summary")
                elif format == "pdf":
                    blocks = [{"type": "heading", "text": "Chat Summary"}, {"type": "paragraph", "text": basic_summary}]
                    file_stream = generate_pdf_file_from_blocks(blocks)
                    return StreamingResponse(
                        file_stream,
                        media_type="application/pdf",
                        headers={"Content-Disposition": "attachment; filename=chat_summary.pdf"}
                    )
            except Exception as fallback_error:
                LOG.error(f"Fallback summary export also failed: {str(fallback_error)}")
                raise HTTPException(
                    status_code=500,
                    detail="Summary generation failed due to content formatting issues. Please try a different format."
                )

    except HTTPException:
        raise
    except Exception as e:
        LOG.error(f"Error in chat-summary endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Summary generation failed: {str(e)}"
        )
