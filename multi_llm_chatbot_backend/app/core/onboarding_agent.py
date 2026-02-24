"""
OnboardingAgent — a conversational sub-agent that gathers user profile data
in a natural, friendly way, then extracts structured fields from the replies.
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional
from app.core.database import get_database
from datetime import datetime

logger = logging.getLogger(__name__)

PROFILE_FIELDS = [
    ("major", "What is your major / area of study?",
     "The student's declared or intended major (e.g. 'Computer Science', 'Biology')"),
    ("minor", "Do you have a minor or secondary focus?",
     "The student's minor or secondary area of study"),
    ("year", "What year are you (freshman, sophomore, junior, senior)?",
     "Academic year: freshman, sophomore, junior, senior, or graduate"),
    ("gpa_range", "What GPA range are you in (e.g. 3.0-3.5)?",
     "Approximate GPA range like '3.0-3.5' or 'around 3.5'"),
    ("career_goals", "What career or goals are you working toward after graduation?",
     "Post-graduation career goals, job aspirations, or grad school plans"),
    ("courses_completed", "What key courses have you already completed?",
     "List of courses already taken (course names or codes)"),
    ("courses_planned", "Are there courses you're planning to take next?",
     "Courses the student plans to take next semester or in the future"),
    ("schedule_preferences", "Do you have schedule preferences (morning/afternoon, no Fridays, etc.)?",
     "Time-of-day preferences, day-of-week preferences, or constraints like 'no 8am classes', 'prefer afternoons', 'MWF only', 'mornings', 'no Fridays'"),
    ("learning_style", "How would you describe your learning style?",
     "How the student learns best: visual, hands-on, reading, lectures, group work, etc."),
    ("extracurriculars", "Are you involved in any clubs, sports, or extracurriculars?",
     "Clubs, sports, organizations, volunteer work, or other activities"),
]


class OnboardingAgent:
    def __init__(self, llm):
        self.llm = llm

    SKIP_SENTINEL = "__skipped__"

    @staticmethod
    def _field_has_value(val) -> bool:
        if val is None:
            return False
        if isinstance(val, str):
            return bool(val.strip())
        if isinstance(val, list):
            return len(val) > 0
        return bool(val)

    async def chat(self, user_input: str, user_id, existing_profile: dict) -> Dict[str, Any]:
        """Process one round of onboarding conversation."""
        filled = {k for k, _, _d in PROFILE_FIELDS
                  if self._field_has_value(existing_profile.get(k))}
        missing = [(k, q, desc) for k, q, desc in PROFILE_FIELDS
                   if k not in filled]
        completion = int(len(filled) / len(PROFILE_FIELDS) * 100)

        current_field = missing[0][0] if missing else None

        # 1. Extract structured data from the latest user reply
        extracted = await self._extract_fields(
            user_input, missing, current_field
        )

        db = get_database()
        if extracted:
            from app.api.routes.user_profile import _normalize_field
            real_values = {}
            skipped_keys = set()
            for k, v in extracted.items():
                if v == self.SKIP_SENTINEL:
                    skipped_keys.add(k)
                elif v:
                    real_values[k] = _normalize_field(k, v)

            update = {}
            if real_values:
                update.update(real_values)
            for sk in skipped_keys:
                update[sk] = ""

            if update:
                update["updated_at"] = datetime.utcnow()
                await db.user_profiles.update_one(
                    {"user_id": user_id},
                    {"$set": update, "$setOnInsert": {"user_id": user_id}},
                    upsert=True,
                )
                filled.update(real_values.keys())
                filled.update(skipped_keys)
                missing = [(k, q, desc) for k, q, desc in PROFILE_FIELDS if k not in filled]
                completion = int(len(filled) / len(PROFILE_FIELDS) * 100)

        if not missing:
            return {
                "reply": "Awesome — I've got everything I need! Your profile is all set. "
                         "Your advisors will now use this info to give you more personalized guidance.",
                "progress": 100,
                "complete": True,
            }

        # 2. Generate the next conversational prompt
        reply = await self._generate_next_question(user_input, existing_profile, filled, missing)
        return {"reply": reply, "progress": completion, "complete": False}

    async def _extract_fields(
        self, text: str, missing_fields: list, current_field: Optional[str] = None
    ) -> dict:
        if not text.strip():
            return {}
        skip_instruction = ""
        if current_field:
            skip_instruction = (
                f'\nThe question just asked was about "{current_field}". '
                "If the user declines, refuses, says they don't know, says skip, "
                'says "no", "pass", "rather not say", "n/a", or similar, '
                f'return {{"{current_field}": "__skipped__"}}.'
            )
        field_descriptions = "\n".join(
            f'- "{k}": {desc}' for k, _q, desc in missing_fields
        )
        system = (
            "Extract any of the following profile fields from the user's message. "
            "Return ONLY valid JSON with field names as keys. "
            "If a field isn't mentioned, omit it. For list fields return a JSON array. "
            "Accept ANY reasonable answer for the field being asked about — "
            "the user's answer does not need to use the exact field name."
            f"{skip_instruction}\n"
            f"Fields:\n{field_descriptions}"
        )
        try:
            raw = await self.llm.generate(
                system_prompt=system,
                context=[{"role": "user", "content": text}],
                temperature=0.1,
                max_tokens=512,
            )
            cleaned = re.sub(r"```(?:json)?", "", raw).strip()
            m = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if m:
                return json.loads(m.group(0))
        except Exception as e:
            logger.warning(f"Extraction failed: {e}")
        return {}

    async def _generate_next_question(
        self, user_input: str, profile: dict, filled: set, missing: list
    ) -> str:
        filled_parts = []
        for k in filled:
            val = profile.get(k)
            if val:
                filled_parts.append(f"{k}={val}")
            else:
                filled_parts.append(f"{k}=DECLINED")
        filled_summary = ", ".join(filled_parts) or "nothing yet"
        next_field_key, next_field_q, _ = missing[0]
        system = (
            "You are a friendly onboarding assistant helping a university student "
            "fill out their profile. You chat like a friendly advisor — warm, curious, natural.\n"
            "RULES:\n"
            "- Respond in exactly ONE short paragraph (2-3 sentences).\n"
            "- First, briefly acknowledge what the student just said.\n"
            "- Then IMMEDIATELY ask one clear question about the NEXT topic.\n"
            "- Your response MUST end with a question mark.\n"
            "- NEVER use labels or headings like 'Question:', 'Student:', 'Answer:', or 'Next:'.\n"
            "- NEVER list multiple questions. Ask about ONE topic only.\n"
            "- If the student declined or skipped, say 'No problem!' and move to the next topic.\n"
            "- NEVER repeat a topic already gathered or declined."
        )
        user_prompt = (
            f"Student just said: \"{user_input}\"\n"
            f"Already gathered: {filled_summary}\n"
            f"Next topic to ask about: {next_field_key} — {next_field_q}\n"
            "Write your short, friendly response that acknowledges the student "
            "and then asks about the next topic. End with a question mark."
        )
        try:
            reply = await self.llm.generate(
                system_prompt=system,
                context=[{"role": "user", "content": user_prompt}],
                temperature=0.7,
                max_tokens=300,
            )
            if reply and '?' not in reply:
                reply = f"{reply} {next_field_q}"
            return reply
        except Exception as e:
            logger.error(f"Question generation failed: {e}")
            return missing[0][1] if missing else "Tell me more about yourself!"
