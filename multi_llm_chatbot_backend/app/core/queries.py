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
Centralised MongoDB query functions.

All database queries should be routed through this module so that
query logic is defined in one place and can be maintained, optimised,
or swapped for an ORM independently of the route handlers.
"""

import logging
from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.core.database import get_database

LOG = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# User queries
# ---------------------------------------------------------------------------

async def find_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Look up a user document by email address.

    :param email: The user's email.
    :returns: User document or ``None``.
    """
    db = get_database()
    return await db.users.find_one({"email": email})


async def find_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Look up a user document by its ObjectId string.

    :param user_id: String representation of the user's ``_id``.
    :returns: User document or ``None``.
    """
    db = get_database()
    return await db.users.find_one({"_id": ObjectId(user_id)})


async def insert_user(user_doc: Dict[str, Any]) -> Any:
    """
    Insert a new user document.

    :param user_doc: The document to insert.
    :returns: The insert result (contains ``inserted_id``).
    """
    db = get_database()
    return await db.users.insert_one(user_doc)


# ---------------------------------------------------------------------------
# Chat-session queries
# ---------------------------------------------------------------------------

async def find_chat_session(
    chat_session_id: str,
    user_id: str,
    *,
    active_only: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Retrieve a single chat session by ID, scoped to a user.

    :param chat_session_id: String ObjectId of the chat session.
    :param user_id: String ObjectId of the owning user.
    :param active_only: When *True*, excludes soft-deleted sessions.
    :returns: Session document or ``None``.
    """
    db = get_database()
    query: Dict[str, Any] = {
        "_id": ObjectId(chat_session_id),
        "user_id": ObjectId(user_id),
    }
    if active_only:
        query["deleted_at"] = {"$exists": False}
    return await db.chat_sessions.find_one(query)


async def find_chat_sessions_for_user(
    user_id: str,
    *,
    active_only: bool = True,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    List chat sessions belonging to a user, newest first.

    :param user_id: String ObjectId of the user.
    :param active_only: Exclude soft-deleted sessions.
    :param limit: Maximum number of sessions to return.
    :returns: List of session documents.
    """
    db = get_database()
    query: Dict[str, Any] = {"user_id": ObjectId(user_id)}
    if active_only:
        query["deleted_at"] = {"$exists": False}
    cursor = db.chat_sessions.find(query).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def insert_chat_session(session_doc: Dict[str, Any]) -> Any:
    """
    Insert a new chat session document.

    :param session_doc: The document to insert.
    :returns: The insert result.
    """
    db = get_database()
    return await db.chat_sessions.insert_one(session_doc)


async def update_chat_session(
    chat_session_id: str,
    update_fields: Dict[str, Any],
) -> Any:
    """
    Update fields on a chat session.

    :param chat_session_id: String ObjectId of the session.
    :param update_fields: Dictionary of fields to ``$set``.
    :returns: The update result.
    """
    db = get_database()
    return await db.chat_sessions.update_one(
        {"_id": ObjectId(chat_session_id)},
        {"$set": update_fields},
    )


# ---------------------------------------------------------------------------
# User-profile queries
# ---------------------------------------------------------------------------

async def find_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve the user profile for a given user.

    :param user_id: The user's ID string (stored as-is, not ObjectId).
    :returns: Profile document or ``None``.
    """
    db = get_database()
    return await db.user_profiles.find_one({"user_id": user_id})


async def upsert_user_profile(
    user_id: str,
    profile_data: Dict[str, Any],
) -> Any:
    """
    Create or replace the user profile for *user_id*.

    :param user_id: The user's ID string.
    :param profile_data: Full profile document (``user_id`` key is set
        automatically).
    :returns: The update result.
    """
    db = get_database()
    profile_data["user_id"] = user_id
    return await db.user_profiles.update_one(
        {"user_id": user_id},
        {"$set": profile_data},
        upsert=True,
    )


# ---------------------------------------------------------------------------
# Course & professor queries
# ---------------------------------------------------------------------------

async def find_courses(
    filters: Dict[str, Any],
    *,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Search for courses matching *filters*.

    :param filters: MongoDB query filter.
    :param limit: Maximum results.
    :returns: List of course documents.
    """
    db = get_database()
    cursor = db.courses.find(filters).limit(limit)
    return await cursor.to_list(length=limit)


async def find_professor_rating(name: str) -> Optional[Dict[str, Any]]:
    """
    Look up a professor's rating by name (case-insensitive regex).

    :param name: Professor name to search.
    :returns: Rating document or ``None``.
    """
    db = get_database()
    import re
    return await db.professor_ratings.find_one(
        {"name": {"$regex": re.escape(name), "$options": "i"}}
    )


async def upsert_courses(courses: List[Dict[str, Any]], semester: str) -> int:
    """
    Bulk upsert course documents for a semester.

    :param courses: List of course documents to upsert.
    :param semester: Semester identifier (e.g. ``"Spring 2026"``).
    :returns: Number of upserted/modified documents.
    """
    db = get_database()
    count = 0
    for course in courses:
        result = await db.courses.update_one(
            {
                "course_code": course.get("course_code"),
                "section": course.get("section"),
                "semester": semester,
            },
            {"$set": course},
            upsert=True,
        )
        if result.upserted_id or result.modified_count:
            count += 1
    return count
