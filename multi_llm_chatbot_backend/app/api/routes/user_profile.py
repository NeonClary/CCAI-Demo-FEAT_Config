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
from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_active_user
from app.core.database import get_database
from app.models.user import User
from app.models.user_profile import UserProfileResponse, UserProfileUpdate

LOG = logging.getLogger(__name__)

router = APIRouter()

PROFILE_FIELDS = [
    "major", "minor", "year", "gpa_range", "career_goals",
    "courses_completed", "courses_planned", "schedule_preferences",
    "learning_style", "extracurriculars",
]


def _is_field_filled(value: Any) -> bool:
    """A profile field counts as filled only if it has a real value."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return len(value) > 0
    return bool(value)


def _calc_completion(doc: Dict[str, Any]) -> int:
    filled = sum(1 for f in PROFILE_FIELDS if _is_field_filled(doc.get(f)))
    return int(filled / len(PROFILE_FIELDS) * 100)


LIST_FIELDS = {"courses_completed", "courses_planned"}

_SELECT_OPTIONS: Dict[str, List[str]] = {
    "year": ["Freshman", "Sophomore", "Junior", "Senior", "Graduate"],
    "gpa_range": ["Below 2.0", "2.0-2.5", "2.5-3.0", "3.0-3.5", "3.5-4.0"],
}

_SELECT_LOOKUP: Dict[str, Dict[str, str]] = {
    field: {opt.lower(): opt for opt in opts}
    for field, opts in _SELECT_OPTIONS.items()
}


def _normalize_select(key: str, value: str) -> str:
    """Map a free-text value to the nearest canonical dropdown option."""
    lookup = _SELECT_LOOKUP.get(key)
    if not lookup or not isinstance(value, str):
        return value
    v = value.strip()
    if v.lower() in lookup:
        return lookup[v.lower()]
    for canonical_lower, canonical in lookup.items():
        if canonical_lower in v.lower():
            return canonical
    return v


def _normalize_field(key: str, value: Any) -> Any:
    """Ensure list fields are lists, select fields match canonical options,
    and string fields are strings."""
    if key in LIST_FIELDS:
        if isinstance(value, str):
            return [s.strip() for s in value.split(",") if s.strip()]
        if isinstance(value, list):
            return value
        return []
    if key in _SELECT_OPTIONS:
        return _normalize_select(key, value)
    if isinstance(value, list):
        return ", ".join(str(v) for v in value if v)
    return value


@router.get("/users/me/profile", response_model=UserProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_active_user),
) -> UserProfileResponse:
    db = get_database()
    doc = await db.user_profiles.find_one({"user_id": current_user.id})
    if not doc:
        return UserProfileResponse(user_id=str(current_user.id))
    fields = {k: _normalize_field(k, doc.get(k)) for k in PROFILE_FIELDS}
    return UserProfileResponse(
        user_id=str(doc["user_id"]),
        **fields,
        advisor_notes=doc.get("advisor_notes"),
        updated_at=doc.get("updated_at"),
        completion_pct=_calc_completion(doc),
    )


@router.put("/users/me/profile", response_model=UserProfileResponse)
async def update_my_profile(
    updates: UserProfileUpdate,
    current_user: User = Depends(get_current_active_user),
) -> UserProfileResponse:
    db = get_database()
    update_data = {k: v for k, v in updates.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    await db.user_profiles.update_one(
        {"user_id": current_user.id},
        {"$set": update_data, "$setOnInsert": {"user_id": current_user.id}},
        upsert=True,
    )
    doc = await db.user_profiles.find_one({"user_id": current_user.id})
    fields = {k: _normalize_field(k, doc.get(k)) for k in PROFILE_FIELDS}
    return UserProfileResponse(
        user_id=str(doc["user_id"]),
        **fields,
        advisor_notes=doc.get("advisor_notes"),
        updated_at=doc.get("updated_at"),
        completion_pct=_calc_completion(doc),
    )


# ---------------------------------------------------------------------------
# Bulk clear user data
# ---------------------------------------------------------------------------

class ClearDataRequest(BaseModel):
    profile: bool = False
    chats: bool = False
    canvas: bool = False


@router.post("/users/me/clear-data")
async def clear_user_data(
    req: ClearDataRequest,
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, List[str]]:
    """Selectively clear categories of user data and return what was cleared."""
    db = get_database()
    cleared: List[str] = []

    if req.profile:
        await db.user_profiles.delete_many({"user_id": current_user.id})
        await db.onboarding_conversations.delete_many({"user_id": current_user.id})
        cleared.append("profile")
        LOG.info(f"Cleared profile + onboarding conversation for user {current_user.id}")

    if req.chats:
        result = await db.chat_sessions.update_many(
            {"user_id": current_user.id, "is_active": True},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}},
        )
        cleared.append(f"chats ({result.modified_count})")
        LOG.info(f"Soft-deleted {result.modified_count} chat sessions for user {current_user.id}")

    if req.canvas:
        await db.phd_canvases.delete_many({"user_id": str(current_user.id)})
        cleared.append("canvas")
        LOG.info(f"Cleared canvas for user {current_user.id}")

    return {"cleared": cleared}
