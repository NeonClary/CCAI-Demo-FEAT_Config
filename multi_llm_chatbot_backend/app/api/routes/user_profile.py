from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from typing import List, Optional
from bson import ObjectId
from pydantic import BaseModel
from app.models.user import User
from app.models.user_profile import UserProfileUpdate, UserProfileResponse
from app.core.auth import get_current_active_user
from app.core.database import get_database
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

PROFILE_FIELDS = [
    "major", "minor", "year", "gpa_range", "career_goals",
    "courses_completed", "courses_planned", "schedule_preferences",
    "learning_style", "extracurriculars",
]


def _is_field_filled(value) -> bool:
    """A profile field counts as filled only if it has a real value."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return len(value) > 0
    return bool(value)


def _calc_completion(doc: dict) -> int:
    filled = sum(1 for f in PROFILE_FIELDS if _is_field_filled(doc.get(f)))
    return int(filled / len(PROFILE_FIELDS) * 100)


LIST_FIELDS = {"courses_completed", "courses_planned"}

# Canonical values for dropdown / select fields so the UI matches regardless
# of how the data was entered (onboarding chat vs manual form).
_SELECT_OPTIONS: dict[str, list[str]] = {
    "year": ["Freshman", "Sophomore", "Junior", "Senior", "Graduate"],
    "gpa_range": ["Below 2.0", "2.0-2.5", "2.5-3.0", "3.0-3.5", "3.5-4.0"],
}

# Build fast lowercase → canonical lookup
_SELECT_LOOKUP: dict[str, dict[str, str]] = {
    field: {opt.lower(): opt for opt in opts}
    for field, opts in _SELECT_OPTIONS.items()
}


def _normalize_select(key: str, value: str) -> str:
    """Map a free-text value to the nearest canonical dropdown option."""
    lookup = _SELECT_LOOKUP.get(key)
    if not lookup or not isinstance(value, str):
        return value
    v = value.strip()
    # Exact case-insensitive match
    if v.lower() in lookup:
        return lookup[v.lower()]
    # Substring / fuzzy: pick the first option that appears in the value
    for canonical_lower, canonical in lookup.items():
        if canonical_lower in v.lower():
            return canonical
    return v


def _normalize_field(key: str, value):
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
    # Non-list fields: coerce lists back to comma-separated strings
    if isinstance(value, list):
        return ", ".join(str(v) for v in value if v)
    return value


@router.get("/users/me/profile", response_model=UserProfileResponse)
async def get_my_profile(current_user: User = Depends(get_current_active_user)):
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
):
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
):
    """Selectively clear categories of user data and return what was cleared."""
    db = get_database()
    cleared: list[str] = []

    if req.profile:
        await db.user_profiles.delete_many({"user_id": current_user.id})
        await db.onboarding_conversations.delete_many({"user_id": current_user.id})
        cleared.append("profile")
        logger.info("Cleared profile + onboarding conversation for user %s", current_user.id)

    if req.chats:
        result = await db.chat_sessions.update_many(
            {"user_id": current_user.id, "is_active": True},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}},
        )
        cleared.append(f"chats ({result.modified_count})")
        logger.info("Soft-deleted %d chat sessions for user %s",
                     result.modified_count, current_user.id)

    if req.canvas:
        await db.phd_canvases.delete_many({"user_id": str(current_user.id)})
        cleared.append("canvas")
        logger.info("Cleared canvas for user %s", current_user.id)

    return {"cleared": cleared}
