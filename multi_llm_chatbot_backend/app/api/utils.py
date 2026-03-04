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

from bson import ObjectId
from fastapi import Request

from app.core.database import get_database
from app.core.session_manager import get_session_manager

LOG = logging.getLogger(__name__)
SESSION_MANAGER = get_session_manager()


async def load_chat_session_into_context(
    chat_session_id: str, user_id: str
) -> Optional[str]:
    """Load a chat session from MongoDB into memory context.

    :param chat_session_id: The MongoDB document ID for the chat session.
    :param user_id: The owning user's identifier.
    :returns: The memory session ID on success, or ``None`` on failure.
    """
    try:
        db = get_database()

        LOG.info("=== LOADING CHAT SESSION DEBUG ===")
        LOG.info(f"Attempting to load chat_session_id: {chat_session_id}")
        LOG.info(f"For user_id: {user_id}")

        chat_session = await db.chat_sessions.find_one({
            "_id": ObjectId(chat_session_id),
            "user_id": ObjectId(user_id),
            "deleted_at": {"$exists": False}
        })

        if not chat_session:
            LOG.warning(f"Chat session {chat_session_id} not found for user {user_id}")

            try:
                session_exists = await db.chat_sessions.find_one({"_id": ObjectId(chat_session_id)})
                if session_exists:
                    LOG.warning(f"Session exists but for different user: {session_exists.get('user_id')}")
                    LOG.warning(f"Expected user: {user_id}")
                    LOG.warning(f"Session user: {session_exists.get('user_id')}")
                    LOG.warning(f"User ID types - Expected: {type(user_id)}, Found: {type(session_exists.get('user_id'))}")
                else:
                    LOG.warning(f"Session {chat_session_id} does not exist in database at all")
            except Exception as debug_error:
                LOG.error(f"Error during session debug: {debug_error}")

            try:
                recent_sessions = await db.chat_sessions.find(
                    {"user_id": ObjectId(user_id), "deleted_at": {"$exists": False}}
                ).limit(5).to_list(5)
                LOG.info(f"Recent sessions for user {user_id}: {[str(s['_id']) for s in recent_sessions]}")
            except Exception as debug_error:
                LOG.error(f"Error listing recent sessions: {debug_error}")

            return None

        LOG.info(f"Found chat session: {chat_session.get('title', 'Untitled')}")
        LOG.info(f"Message count: {len(chat_session.get('messages', []))}")

        memory_session_id = f"chat_{chat_session_id}"
        LOG.info(f"Creating memory session: {memory_session_id}")

        session_manager = get_session_manager()
        memory_session = session_manager.get_session(memory_session_id)

        memory_session.clear_all_data()

        messages = chat_session.get('messages', [])
        for msg_data in messages:
            try:
                message = {
                    'id': msg_data.get('id', 'unknown'),
                    'role': 'user' if msg_data.get('type') == 'user' else 'assistant',
                    'content': msg_data.get('content', ''),
                    'timestamp': msg_data.get('timestamp', '')
                }
                memory_session.append_message(message['role'], message['content'])

                if not hasattr(memory_session, 'original_messages'):
                    memory_session.original_messages = []

                memory_session.original_messages.append(message)
            except Exception as msg_error:
                LOG.error(f"Error loading message: {msg_error}")
                continue

        LOG.info(f"Loaded {len(messages)} messages into session {memory_session_id}")
        return memory_session_id

    except Exception as e:
        LOG.error(f"Error loading chat session into context: {e}")
        LOG.error(f"Full traceback: {traceback.format_exc()}")
        return None


async def get_or_create_session_for_request_async(
    request: Request,
    session_id_override: Optional[str] = None,
    chat_session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> str:
    """Resolve or create a memory session for the incoming request.

    :param request: The incoming FastAPI request.
    :param session_id_override: An explicit session ID to use, if any.
    :param chat_session_id: A MongoDB chat session ID to load, if any.
    :param user_id: The user's identifier (required when *chat_session_id*
        is provided).
    :returns: The resolved memory session identifier.
    """
    # Case 1: Loading an existing chat session
    if chat_session_id and user_id:
        memory_session_id = await load_chat_session_into_context(chat_session_id, user_id)
        if memory_session_id:
            return memory_session_id

    # Case 2: Explicit session ID provided
    if session_id_override:
        return session_id_override

    # Case 3: Check for session header
    session_header = request.headers.get("X-Session-ID")
    if session_header:
        return session_header

    # Case 4: Create a truly new session
    new_session_id = SESSION_MANAGER.create_session()
    LOG.info(f"Created new session: {new_session_id}")
    return new_session_id
