import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import get_current_active_user
from app.core.database import get_database
from app.models.user import User
from app.models.user_profile import UserProfileResponse, UserProfileUpdate

LOG = logging.getLogger(__name__)

router = APIRouter()

PROFILE_FIELDS = [
    "cyber_role",
    "organization_type",
    "primary_domains",
    "certifications",
    "tools_stack",
    "compliance_focus",
    "current_goals",
    "learning_preferences",
    "timezone",
]

LIST_FIELDS = {"primary_domains", "certifications", "tools_stack"}

_SELECT_OPTIONS: Dict[str, List[str]] = {
    "cyber_role": [
        "Student / Learner",
        "Career changer",
        "SOC analyst",
        "Security engineer",
        "Architect / lead",
        "Manager / director",
        "Consultant",
        "Other",
    ],
    "organization_type": [
        "Startup",
        "Mid-size company",
        "Enterprise",
        "Government / public sector",
        "Education",
        "MSP / MSSP",
        "Independent / job seeker",
    ],
}


def _is_field_filled(value: Any) -> bool:
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


_SELECT_LOOKUP: Dict[str, Dict[str, str]] = {
    field: {opt.lower(): opt for opt in opts}
    for field, opts in _SELECT_OPTIONS.items()
}


def _normalize_select(key: str, value: str) -> str:
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
        resp = UserProfileResponse(user_id=str(current_user.id))
        if current_user.researchArea:
            resp.timezone = current_user.researchArea
        return resp
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


class ClearDataRequest(BaseModel):
    profile: bool = False
    chats: bool = False
    canvas: bool = False


@router.post("/users/me/clear-data")
async def clear_user_data(
    req: ClearDataRequest,
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, List[str]]:
    db = get_database()
    cleared: List[str] = []

    if req.profile:
        await db.user_profiles.delete_many({"user_id": current_user.id})
        await db.onboarding_conversations.delete_many({"user_id": current_user.id})
        cleared.append("profile")

    if req.chats:
        result = await db.chat_sessions.update_many(
            {"user_id": current_user.id, "is_active": True},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}},
        )
        cleared.append(f"chats ({result.modified_count})")

    if req.canvas:
        await db.phd_canvases.delete_many({"user_id": str(current_user.id)})
        cleared.append("canvas")

    return {"cleared": cleared}
