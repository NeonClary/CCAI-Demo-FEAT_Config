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
OnboardingAgent — a conversational sub-agent that gathers user profile data
in a natural, friendly way, then extracts structured fields from the replies.
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.database import get_database

LOG = logging.getLogger(__name__)

PROFILE_FIELDS: List[tuple] = [
    ("major", "What is your primary focus area for this advisory panel?",
     "Primary domain or use case (e.g. customer support, HR operations, project planning)"),
    ("minor", "Do you have a secondary focus area?",
     "Secondary domain, optional"),
    ("year", "What role level best fits you?",
     "Role level such as executive, director, manager, individual contributor, consultant"),
    ("gpa_range", "Which organization stage best describes your context?",
     "Organization stage such as early stage, growth, established, enterprise"),
    ("career_goals", "What outcomes are you trying to achieve with this advisory assistant?",
     "Goals, success metrics, and desired business outcomes"),
    ("courses_completed", "What initiatives have already been started?",
     "Existing initiatives, projects, or workflows already in place"),
    ("courses_planned", "What initiatives are planned next?",
     "Upcoming initiatives or priorities"),
    ("schedule_preferences", "Any collaboration preferences for responses (concise, detailed, weekly planning, etc.)?",
     "Communication and planning preferences"),
    ("learning_style", "How do you prefer information to be presented?",
     "Preferred style such as executive summary, step-by-step, data-driven, visual"),
    ("extracurriculars", "Any additional context, constraints, or stakeholders we should consider?",
     "Extra organizational context"),
]


class OnboardingAgent:
    def __init__(self, llm: Any) -> None:
        self.llm = llm

    SKIP_SENTINEL = "__skipped__"

    @staticmethod
    def _field_has_value(val: Any) -> bool:
        if val is None:
            return False
        if isinstance(val, str):
            return bool(val.strip())
        if isinstance(val, list):
            return len(val) > 0
        return bool(val)

    async def chat(self, user_input: str, user_id: Any, existing_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Process one round of onboarding conversation."""
        filled = {k for k, _, _d in PROFILE_FIELDS
                  if self._field_has_value(existing_profile.get(k))}
        missing = [(k, q, desc) for k, q, desc in PROFILE_FIELDS
                   if k not in filled]
        completion = int(len(filled) / len(PROFILE_FIELDS) * 100)

        current_field = missing[0][0] if missing else None

        extracted = await self._extract_fields(
            user_input, missing, current_field
        )

        db = get_database()
        if extracted:
            from app.api.routes.user_profile import _normalize_field
            real_values: Dict[str, Any] = {}
            skipped_keys: set = set()
            for k, v in extracted.items():
                if v == self.SKIP_SENTINEL:
                    skipped_keys.add(k)
                elif v:
                    real_values[k] = _normalize_field(k, v)

            update: Dict[str, Any] = {}
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
                         "Your personas will now use this info to provide more tailored guidance.",
                "progress": 100,
                "complete": True,
            }

        reply = await self._generate_next_question(user_input, existing_profile, filled, missing)
        return {"reply": reply, "progress": completion, "complete": False}

    async def _extract_fields(
        self, text: str, missing_fields: List[tuple], current_field: Optional[str] = None
    ) -> Dict[str, Any]:
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
            LOG.warning(f"Extraction failed: {e}")
        return {}

    async def _generate_next_question(
        self, user_input: str, profile: Dict[str, Any], filled: set, missing: List[tuple]
    ) -> str:
        filled_parts: List[str] = []
        for k in filled:
            val = profile.get(k)
            if val:
                filled_parts.append(f"{k}={val}")
            else:
                filled_parts.append(f"{k}=DECLINED")
        filled_summary = ", ".join(filled_parts) or "nothing yet"
        next_field_key, next_field_q, _ = missing[0]
        system = (
            "You are a friendly onboarding assistant helping a user "
            "set up a configurable advisory workspace. You chat warmly and naturally.\n"
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
            LOG.error(f"Question generation failed: {e}")
            return missing[0][1] if missing else "Tell me more about yourself!"
