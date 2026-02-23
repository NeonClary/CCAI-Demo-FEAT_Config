from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from bson import ObjectId
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


def _calc_completion(doc: dict) -> int:
    filled = sum(1 for f in PROFILE_FIELDS if doc.get(f))
    return int(filled / len(PROFILE_FIELDS) * 100)


LIST_FIELDS = {"courses_completed", "courses_planned"}


def _normalize_field(key: str, value):
    """Ensure list fields are lists and string fields are strings."""
    if key in LIST_FIELDS:
        if isinstance(value, str):
            return [s.strip() for s in value.split(",") if s.strip()]
        if isinstance(value, list):
            return value
        return []
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
