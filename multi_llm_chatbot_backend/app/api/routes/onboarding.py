from fastapi import APIRouter, Depends
from pydantic import BaseModel
from datetime import datetime
from app.models.user import User
from app.core.auth import get_current_active_user
from app.core.database import get_database
from app.core.onboarding_agent import OnboardingAgent, PROFILE_FIELDS
from app.api.routes.user_profile import _is_field_filled
from app.core.bootstrap import create_llm_client
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

ONBOARDING_COLLECTION = "onboarding_conversations"


class OnboardingMessage(BaseModel):
    user_input: str


def _progress(profile: dict) -> int:
    filled = sum(1 for k, *_ in PROFILE_FIELDS if _is_field_filled(profile.get(k)))
    return int(filled / len(PROFILE_FIELDS) * 100)


def _next_missing_question(profile: dict) -> str | None:
    """Return the human-friendly question for the first unfilled field."""
    for key, question, _desc in PROFILE_FIELDS:
        if not _is_field_filled(profile.get(key)):
            return question
    return None


@router.get("/onboarding/start")
async def onboarding_start(current_user: User = Depends(get_current_active_user)):
    """Return conversation history (if any) and current progress.

    If the user has an in-progress conversation it is returned so the
    frontend can restore the chat.  Otherwise a fresh contextual welcome
    message is generated based on which fields are still missing.
    """
    db = get_database()
    profile = await db.user_profiles.find_one({"user_id": current_user.id}) or {}
    progress = _progress(profile)

    if progress >= 100:
        await db[ONBOARDING_COLLECTION].delete_many({"user_id": current_user.id})
        return {
            "messages": [{"role": "agent",
                          "text": "Your profile is already complete! Feel free to update anything by chatting here."}],
            "progress": 100,
            "complete": True,
        }

    conv = await db[ONBOARDING_COLLECTION].find_one({"user_id": current_user.id})

    if conv and conv.get("messages"):
        return {
            "messages": conv["messages"],
            "progress": progress,
            "complete": False,
        }

    next_q = _next_missing_question(profile)
    if progress == 0:
        greeting = (
            f"Hey {current_user.firstName}! I'd love to get to know you a bit so "
            "your advisors can give you more personalized help. "
            f"Let's start simple — {next_q.lower() if next_q else 'tell me about yourself!'}"
        )
    else:
        greeting = (
            f"Welcome back, {current_user.firstName}! You're {progress}% done. "
            f"Let's pick up where we left off — {next_q.lower() if next_q else 'what else can you tell me?'}"
        )

    messages = [{"role": "agent", "text": greeting}]
    await db[ONBOARDING_COLLECTION].update_one(
        {"user_id": current_user.id},
        {"$set": {"messages": messages, "updated_at": datetime.utcnow()},
         "$setOnInsert": {"user_id": current_user.id}},
        upsert=True,
    )

    return {"messages": messages, "progress": progress, "complete": False}


@router.post("/onboarding/chat")
async def onboarding_chat(
    msg: OnboardingMessage,
    current_user: User = Depends(get_current_active_user),
):
    db = get_database()
    profile = await db.user_profiles.find_one({"user_id": current_user.id}) or {}

    agent = OnboardingAgent(create_llm_client())
    result = await agent.chat(msg.user_input, current_user.id, profile)

    user_msg = {"role": "user", "text": msg.user_input}
    agent_msg = {"role": "agent", "text": result["reply"]}

    await db[ONBOARDING_COLLECTION].update_one(
        {"user_id": current_user.id},
        {"$push": {"messages": {"$each": [user_msg, agent_msg]}},
         "$set": {"updated_at": datetime.utcnow()},
         "$setOnInsert": {"user_id": current_user.id}},
        upsert=True,
    )

    if result.get("complete"):
        await db[ONBOARDING_COLLECTION].delete_many({"user_id": current_user.id})

    return result
