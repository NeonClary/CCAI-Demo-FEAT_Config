from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from app.models.user import User
from app.core.auth import get_current_active_user
from app.core.database import get_database
from app.core.onboarding_agent import OnboardingAgent
from app.core.bootstrap import create_llm_client
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class OnboardingMessage(BaseModel):
    user_input: str


@router.post("/onboarding/chat")
async def onboarding_chat(
    msg: OnboardingMessage,
    current_user: User = Depends(get_current_active_user),
):
    db = get_database()
    profile = await db.user_profiles.find_one({"user_id": current_user.id}) or {}
    agent = OnboardingAgent(create_llm_client())
    result = await agent.chat(msg.user_input, current_user.id, profile)
    return result


@router.get("/onboarding/start")
async def onboarding_start(current_user: User = Depends(get_current_active_user)):
    """Return a welcome message to kick off the onboarding conversation."""
    db = get_database()
    profile = await db.user_profiles.find_one({"user_id": current_user.id}) or {}

    from app.core.onboarding_agent import PROFILE_FIELDS
    filled = sum(1 for k, *_ in PROFILE_FIELDS if k in profile)
    progress = int(filled / len(PROFILE_FIELDS) * 100)

    if progress >= 100:
        return {
            "reply": "Your profile is already complete! Feel free to update anything by chatting here.",
            "progress": 100,
            "complete": True,
        }

    return {
        "reply": (
            f"Hey {current_user.firstName}! I'd love to get to know you a bit so your advisors "
            "can give you more personalized help. Let's start simple — what are you studying?"
        ),
        "progress": progress,
        "complete": False,
    }
