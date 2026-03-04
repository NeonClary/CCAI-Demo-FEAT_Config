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

import asyncio
import json
import logging
import re
import traceback
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.core.context_manager import get_context_manager
from app.core.rag_manager import get_rag_manager
from app.core.session_manager import ConversationContext, get_session_manager
from app.llm.llm_client import LLMClient
from app.models.default_personas import is_valid_persona_id
from app.models.persona import Persona

LOG = logging.getLogger(__name__)


class ImprovedChatOrchestrator:
    """Enhanced orchestrator with document awareness and improved context handling."""

    def __init__(self) -> None:
        """Initialise persona registry, session manager, and context manager."""
        self.personas: Dict[str, Persona] = {}
        self.session_manager = get_session_manager()
        self.context_manager = get_context_manager()

    def register_persona(self, persona: Persona) -> None:
        """Register a persona with the orchestrator.

        :param persona: The persona instance to register.
        """
        self.personas[persona.id] = persona
        LOG.info(f"Registered persona: {persona.id} ({persona.name})")

    def get_persona(self, persona_id: str) -> Optional[Persona]:
        """Get a specific persona by its identifier.

        :param persona_id: Unique persona identifier.
        :returns: The matching :class:`Persona`, or ``None``.
        """
        return self.personas.get(persona_id)

    def list_personas(self) -> List[str]:
        """List all available persona IDs.

        :returns: A list of registered persona identifier strings.
        """
        return list(self.personas.keys())

    async def process_message(
        self,
        user_input: str,
        session_id: Optional[str] = None,
        response_length: str = "medium",
    ) -> Dict[str, Any]:
        """Process a user message through the orchestration pipeline.

        :param user_input: The raw message from the user.
        :param session_id: Optional session identifier.
        :param response_length: Desired response verbosity.
        :returns: A dict with status, responses, and session info.
        """
        try:
            session = self.session_manager.get_session(session_id)

            session.append_message("user", user_input)

            needs_clarification = self._needs_clarification(session, user_input)

            if needs_clarification:
                clarification = await self._generate_clarification_question(session)
                session.append_message("system", f"Clarification request: {clarification}")

                return {
                    "status": "clarification_needed",
                    "message": clarification,
                    "suggestions": self._get_clarification_suggestions(),
                    "session_id": session.session_id
                }

            responses = await self._generate_persona_responses(session, response_length)

            return {
                "status": "success",
                "responses": responses,
                "session_id": session.session_id
            }

        except Exception as e:
            LOG.error(f"Error in process_message: {e}")
            return {
                "status": "error",
                "message": "I'm having technical difficulties. Please try again.",
                "error": str(e)
            }

    async def process_message_with_enhanced_context(
        self,
        user_input: str,
        session_id: str,
        response_length: str = "medium",
    ) -> Dict[str, Any]:
        """Enhanced message processing with document awareness and better context management.

        :param user_input: The raw message from the user.
        :param session_id: Session identifier.
        :param response_length: Desired response verbosity.
        :returns: A dict with status, responses, and document info.
        """
        try:
            session = self.session_manager.get_session(session_id)

            session.append_message("user", user_input)

            document_references = self._extract_document_references_from_query(user_input)

            rag_manager = get_rag_manager()
            doc_stats = rag_manager.get_document_stats(session_id)
            available_documents = [doc["filename"] for doc in doc_stats.get("documents", [])]

            responses = await self._generate_persona_responses(session, response_length)

            return {
                "status": "success",
                "responses": responses,
                "document_references_detected": bool(document_references),
                "available_documents": available_documents,
                "session_id": session_id
            }

        except Exception as e:
            LOG.error(f"Error in enhanced message processing: {e}")
            return {
                "status": "error",
                "message": "I'm having technical difficulties processing your request.",
                "suggestions": ["Please try rephrasing your question.", "Check if your documents uploaded successfully."]
            }

    def _extract_document_references_from_query(self, query: str) -> List[str]:
        """Extract document references from a user query.

        :param query: The user's raw query text.
        :returns: Up to three extracted document reference strings.
        """
        query_lower = query.lower()
        references = []

        patterns = [
            r"(?:my|the|in)\s+([a-zA-Z_\-]+\.(?:pdf|docx|txt))",
            r"(?:my|the)\s+(dissertation|thesis|proposal|chapter|manuscript)",
            r"(?:in|from)\s+(?:my\s+)?([a-zA-Z_\-\s]+(?:chapter|section))",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, query_lower)
            references.extend(matches)

        return references[:3]

    def _needs_clarification(self, session: ConversationContext, user_input: str) -> bool:
        """Determine if the user input needs clarification.

        Patterns and keywords are driven by ``config.yaml`` orchestrator
        section.

        The caller guarantees the current message is in the session
        exactly once before calling.  More than one user message means
        this is not the first turn so clarification is skipped.

        :param session: Current conversation context.
        :param user_input: The latest user message.
        :returns: ``True`` when clarification should be requested.
        """
        user_messages = [msg for msg in session.messages if msg.get('role') == 'user']
        if len(user_messages) > 1:
            LOG.info(f"Skipping clarification: session already has {len(user_messages)} user message(s)")
            return False

        orch_cfg = get_settings().orchestrator
        user_lower = user_input.lower().strip()
        word_count = len(user_input.split())

        LOG.info(f"Checking clarification for: {user_input!r} ({word_count} words)")

        has_specific_keywords = any(
            kw in user_lower for kw in orch_cfg.specific_keywords
        )
        if has_specific_keywords:
            LOG.info("NO CLARIFICATION: input contains specific keywords")
            return False

        if word_count >= orch_cfg.min_words_without_keywords:
            LOG.info(f"NO CLARIFICATION: input has {word_count} words (>= {orch_cfg.min_words_without_keywords} threshold)")
            return False

        for pattern in orch_cfg.vague_patterns:
            if re.search(pattern, user_lower):
                LOG.info(f"CLARIFICATION TRIGGERED: pattern {pattern!r} matched {user_input!r}")
                return True

        LOG.info(f"CLARIFICATION TRIGGERED: short input ({word_count} words) without specific keywords")
        return True

    async def generate_contextual_clarification(self, user_input: str) -> Dict[str, Any]:
        """Use the LLM to produce a clarification question and clickable
        suggestions tailored to what the user actually typed.

        Falls back to the static values in ``config.yaml`` if the LLM call
        fails.

        :param user_input: The vague user message.
        :returns: A dict with ``question`` and ``suggestions`` keys.
        """
        orch_cfg = get_settings().orchestrator

        advisor_list = ", ".join(
            f"{p.name} ({p.id})" for p in self.personas.values()
        )

        system_prompt = (
            "You are a helpful routing assistant. The user's message is too "
            "vague to send to the advisors. Produce a short clarifying question "
            "and exactly 4 clickable suggestion buttons the user could press.\n\n"
            "Reply ONLY with valid JSON — no markdown, no extra text:\n"
            '{"question": "...", "suggestions": ["...", "...", "...", "..."]}\n\n'
            "Keep the question to one sentence. Each suggestion should be a "
            "complete sentence the user could send as their next message."
        )

        user_prompt = (
            f"User said: \"{user_input}\"\n"
            f"Available advisors: {advisor_list}\n\n"
            "Generate a clarifying question and 4 suggestion buttons that "
            "relate to what the user said and steer toward the advisors above."
        )

        try:
            llm = next(iter(self.personas.values())).llm
            raw = await llm.generate(
                system_prompt=system_prompt,
                context=[{"role": "user", "content": user_prompt}],
                temperature=0.4,
                max_tokens=1024,
            )

            cleaned = raw.strip()
            cleaned = re.sub(r"```(?:json)?", "", cleaned).strip()

            json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if json_match:
                cleaned = json_match.group(0)

            LOG.debug(f"LLM raw: {raw[:200]} | cleaned: {cleaned[:200]}")
            parsed = json.loads(cleaned)
            question = parsed.get("question", "").strip()
            suggestions = parsed.get("suggestions", [])

            if question and isinstance(suggestions, list) and len(suggestions) >= 2:
                LOG.info(f"LLM clarification generated for: {user_input!r}")
                return {"question": question, "suggestions": suggestions[:4]}

        except Exception as e:
            LOG.warning(f"LLM clarification failed, using config fallback: {e}")

        fallback_questions = orch_cfg.clarification_questions or [
            "Could you provide more details about what you need help with?"
        ]
        fallback_suggestions = orch_cfg.clarification_suggestions or [
            "Provide more details about your question"
        ]
        return {
            "question": fallback_questions[0],
            "suggestions": fallback_suggestions,
        }

    async def _generate_persona_responses(
        self,
        session: ConversationContext,
        response_length: str = "medium",
    ) -> List[Dict[str, Any]]:
        """Generate responses from all personas with enhanced RAG integration.

        :param session: Current conversation context.
        :param response_length: Desired response verbosity.
        :returns: A list of response dicts, one per persona.
        """
        responses = []

        for persona_id, persona in self.personas.items():
            LOG.info(f"Generating response for {persona_id} with enhanced RAG")

            response_data = await self._generate_single_persona_response(session, persona, response_length)

            session.append_message(persona_id, response_data["response"])

            responses.append(response_data)

        return responses

    async def _generate_single_persona_response(
        self,
        session: ConversationContext,
        persona: Persona,
        response_length: str = "medium",
        prefetched_document_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate response from a single persona with enhanced RAG integration.

        If *prefetched_document_context* is provided it is used directly,
        skipping the per-persona RAG retrieval (used by the parallel path).

        :param session: Current conversation context.
        :param persona: The persona that should respond.
        :param response_length: Desired response verbosity.
        :param prefetched_document_context: Pre-retrieved RAG context, if any.
        :returns: A dict describing the persona response and metadata.
        """
        try:
            user_message = ""
            try:
                user_message = session.get_latest_user_message() or ""
            except AttributeError:
                for msg in reversed(session.messages):
                    if msg.get('role') == 'user':
                        user_message = msg.get('content', '')
                        break

            if prefetched_document_context is not None:
                document_context = prefetched_document_context
            else:
                document_context = ""
                if user_message:
                    document_context = await self._retrieve_relevant_documents(
                        user_input=user_message,
                        session_id=session.session_id,
                        persona_id=persona.id,
                    )

            if persona.id == "course_advisor" and user_message:
                course_data_context = await self._query_course_database(user_message)
                if course_data_context:
                    document_context = (document_context or "") + "\n\n" + course_data_context

            enhanced_context = await self._build_enhanced_context_for_persona(
                session, persona, user_message, document_context
            )

            response = await persona.respond(enhanced_context, response_length)

            if not self._is_valid_response(response, persona.id):
                LOG.warning(f"Invalid response from {persona.id}, using fallback")
                response = self._get_persona_fallback(persona.id)

            used_documents = bool(document_context and len(document_context.strip()) > 100)
            document_chunks_used = document_context.count("[Source:") if document_context else 0

            return {
                "persona_id": persona.id,
                "persona_name": persona.name,
                "response": response,
                "used_documents": used_documents,
                "document_chunks_used": document_chunks_used,
                "response_length": response_length,
                "context_quality": "high" if document_context else "conversation_only"
            }

        except Exception as e:
            LOG.error(f"Error generating response for {persona.id}: {e}")
            return {
                "persona_id": persona.id,
                "persona_name": persona.name,
                "response": f"I apologize, but I'm having technical difficulties. {self._get_persona_fallback(persona.id)}",
                "used_documents": False,
                "document_chunks_used": 0,
                "response_length": response_length,
                "context_quality": "error"
            }

    # ── Parallel multi-persona generation ────────────────────────────

    async def generate_parallel_responses(
        self,
        persona_ids: List[str],
        session_id: str,
        user_input: str,
        response_length: str = "medium",
    ) -> List[Dict[str, Any]]:
        """Generate responses from multiple personas **concurrently**.

        RAG document retrieval is done once and shared across all personas.

        :param persona_ids: Identifiers of the personas to query.
        :param session_id: Current session identifier.
        :param user_input: The user's message.
        :param response_length: Desired response verbosity.
        :returns: A list of response dicts, one per persona.
        """
        session = self.session_manager.get_session(session_id)

        document_context = await self._retrieve_relevant_documents(
            user_input=user_input,
            session_id=session_id,
            persona_id="",
        )
        LOG.info(
            f"Shared RAG retrieval complete ({len(document_context or '')} chars) for {len(persona_ids)} personas"
        )

        async def _run_one(pid: str) -> Dict[str, Any]:
            persona = self.get_persona(pid)
            if not persona:
                return {
                    "persona_id": pid,
                    "persona_name": "Unknown",
                    "response": "Persona not found.",
                    "used_documents": False,
                    "document_chunks_used": 0,
                    "response_length": response_length,
                    "context_quality": "error",
                }
            return await self._generate_single_persona_response(
                session,
                persona,
                response_length,
                prefetched_document_context=document_context,
            )

        results = await asyncio.gather(
            *[_run_one(pid) for pid in persona_ids],
            return_exceptions=True,
        )

        responses: List[Dict[str, Any]] = []
        for pid, result in zip(persona_ids, results):
            if isinstance(result, Exception):
                LOG.error(f"Parallel persona {pid} raised: {result}")
                persona = self.get_persona(pid)
                responses.append({
                    "persona_id": pid,
                    "persona_name": persona.name if persona else pid,
                    "response": "I encountered an error while processing your question. Please try again.",
                    "used_documents": False,
                    "document_chunks_used": 0,
                    "response_length": response_length,
                    "context_quality": "error",
                })
            else:
                responses.append(result)
                session.append_message(pid, result["response"])

        return responses

    async def _query_course_database(self, user_message: str) -> str:
        """Query the courses and professor_ratings MongoDB collections.

        Returns a formatted text block that can be injected into the
        ``course_advisor`` persona's context.

        :param user_message: The user's course-related query.
        :returns: Formatted course data string, or empty string on failure.
        """
        try:
            from app.core.course_query_engine import smart_course_search
            from app.core.bootstrap import create_llm_client

            llm = create_llm_client()
            result = await smart_course_search(user_message, llm)

            lines: List[str] = []
            lines.append("=== COURSE & PROFESSOR DATABASE RESULTS ===")

            if result.get("message"):
                lines.append(result["message"])

            for course in result.get("results", []):
                sched = course.get("schedule", {})
                line = (
                    f"- {course.get('course_code')} sec {course.get('section')}: "
                    f"{course.get('title')} | Instructor: {course.get('instructor')} "
                    f"| Schedule: {sched.get('raw', 'TBA')} | Location: {course.get('location', 'TBA')} "
                    f"| Seats: {course.get('seats_available', '?')} "
                    f"| Prof Rating: {course.get('professor_rating', 'N/A')}/5 "
                    f"| Difficulty: {course.get('professor_difficulty', 'N/A')}/5 "
                    f"| Would Take Again: {course.get('would_take_again_pct', 'N/A')}%"
                )
                lines.append(line)

            if result.get("filters_used"):
                lines.append(f"Parsed filters: {json.dumps(result['filters_used'])}")

            for alt in result.get("alternatives", []):
                param = alt.get("relaxed_parameter", "some constraints")
                lines.append(f"\n--- ALTERNATIVE (with {param} relaxed): ---")
                if alt.get("relaxation_detail"):
                    lines.append(f"  Change: {alt['relaxation_detail']}")
                for course in alt.get("results", []):
                    sched = course.get("schedule", {})
                    line = (
                        f"- {course.get('course_code')} sec {course.get('section')}: "
                        f"{course.get('title')} | Instructor: {course.get('instructor')} "
                        f"| Schedule: {sched.get('raw', 'TBA')} "
                        f"| Prof Rating: {course.get('professor_rating', 'N/A')}/5 "
                        f"| Difficulty: {course.get('professor_difficulty', 'N/A')}/5 "
                        f"| Would Take Again: {course.get('would_take_again_pct', 'N/A')}%"
                    )
                    lines.append(line)

            lines.append("=== END DATABASE RESULTS ===")
            lines.append(
                "Use the above real data in your response. Cite specific section numbers, "
                "professor ratings, and schedules. If no exact matches were found but alternatives "
                "exist, present the best options from each relaxation path. For example: "
                "'No classes match exactly, but Section 006 at 8am has a 4.3-star professor, "
                "and Section 004 at 1pm has a 3.9-star professor.' "
                "If no results at all, suggest trying different criteria."
            )
            return "\n".join(lines)

        except Exception as e:
            LOG.warning(f"Course database query failed: {e}")
            return ""

    # ── Orchestrator routing ─────────────────────────────────────────────

    def classify_query(self, user_input: str, session_id: Optional[str] = None) -> str:
        """Classify whether a query should be routed to the course-database
        sub-agent instead of the normal multi-persona panel.

        Uses conversation history to detect follow-up questions that should
        stay with the same specialist agent even when the wording alone
        would not trigger specialist routing.

        :param user_input: The user's raw message.
        :param session_id: Optional session identifier for follow-up detection.
        :returns: ``"course_db"`` or ``"general"``.
        """
        input_lower = user_input.lower()

        has_course_code = bool(
            re.search(r'\b[A-Z]{2,4}\s*\d{3,4}\b', user_input)
        )

        db_patterns = [
            r"professor\s+rat(ed|ing)", r"\d+\s*star",
            r"star\s*(professor|rating)", r"best\s+professor",
            r"(which|what)\s+(section|class|option)",
            r"start(s|ing)?\s+(at|after|before)",
            r"no\s+\d+\s*am", r"no\s+(morning|8am|8\s*am|early)",
            r"(schedule|time)\s+(for|preference)",
            r"take\s+again", r"difficulty\s+rat",
            r"seats?\s+available", r"(open|available)\s+section",
        ]
        has_db_indicator = any(
            re.search(p, input_lower) for p in db_patterns
        )

        course_words = ["class", "course", "section", "lecture", "lab"]
        sched_rate_words = [
            "schedule", "time", "morning", "afternoon", "evening",
            "rating", "rated", "star", "difficulty",
            "professor", "instructor", "start", "available",
        ]
        has_course_word = any(w in input_lower for w in course_words)
        has_sched_rate = any(w in input_lower for w in sched_rate_words)

        if has_course_code or has_db_indicator or (has_course_word and has_sched_rate):
            LOG.info(f"Query classified as course_db (explicit signals): {user_input[:80]!r}")
            return "course_db"

        # ── Context-aware follow-up detection ────────────────────────
        if session_id:
            last_route = self._get_last_agent_route(session_id)
            if last_route and self._is_follow_up(user_input, last_route):
                LOG.info(
                    f"Query classified as {last_route} (follow-up detected): {user_input[:80]!r}"
                )
                return last_route

        return "general"

    def _get_last_agent_route(self, session_id: str) -> Optional[str]:
        """Check session metadata for the most recent specialist route.

        :param session_id: Session identifier to inspect.
        :returns: The last specialist route string, or ``None``.
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            return None
        return getattr(session, "_last_agent_route", None)

    def _set_last_agent_route(self, session_id: str, route: str) -> None:
        """Record which specialist route was used so follow-ups can reuse it.

        :param session_id: Session identifier to update.
        :param route: The specialist route string to store.
        """
        session = self.session_manager.get_session(session_id)
        if session:
            session._last_agent_route = route

    def _clear_agent_route(self, session_id: str) -> None:
        """Clear the specialist route when the conversation clearly changes topic.

        :param session_id: Session identifier to clear.
        """
        session = self.session_manager.get_session(session_id)
        if session and hasattr(session, "_last_agent_route"):
            del session._last_agent_route

    @staticmethod
    def _is_follow_up(user_input: str, last_route: str) -> bool:
        """Detect whether *user_input* is a conversational follow-up to the
        previous specialist turn rather than a brand-new topic.

        Heuristics:

        - Short messages (<15 words) that contain referential language
          (``"what about"``, ``"how about"``, ``"instead"``, ``"also"``, etc.)
        - Semester / time references when the last route was ``course_db``
        - Pronoun-heavy starts (``"that"``, ``"those"``, ``"it"``, ``"them"``)
        - Comparative / alternative phrasing

        :param user_input: The user's latest message.
        :param last_route: The previous specialist route.
        :returns: ``True`` if the message appears to be a follow-up.
        """
        lower = user_input.lower().strip()
        words = lower.split()

        follow_up_phrases = [
            r"^what about\b", r"^how about\b", r"^and\b",
            r"^what if\b", r"^can you\b", r"^could you\b",
            r"^show me\b", r"^any\b",
            r"\binstead\b", r"\balso\b", r"\btoo\b",
            r"^same\b", r"^that\b", r"^those\b", r"^these\b",
            r"^them\b", r"^it\b",
            r"^yes\b", r"^no\b", r"^yeah\b",
            r"^okay\b", r"^ok\b", r"^sure\b",
            r"\bother\b", r"\balternative", r"\bdifferent\b",
            r"\bmore\b", r"\bless\b", r"\bcheaper\b",
        ]

        if len(words) <= 15:
            if any(re.search(p, lower) for p in follow_up_phrases):
                return True

        if last_route == "course_db":
            course_followup_patterns = [
                r"\b(spring|summer|fall|winter)\b",
                r"\bsemester\b", r"\bterm\b",
                r"\b(next|this|last)\s+(year|semester|term)\b",
                r"\b(earlier|later)\b",
                r"\bmorning\b", r"\bafternoon\b", r"\bevening\b",
                r"\b(mon|tue|wed|thu|fri|mwf|tth)\b",
                r"\b(online|in\s*person|hybrid)\b",
                r"\b(easier|harder)\b",
                r"\b(another|different)\s+(section|professor|time)\b",
            ]
            if any(re.search(p, lower) for p in course_followup_patterns):
                return True

        return False

    async def handle_course_query(
        self,
        user_message: str,
        session_id: str,
        response_length: str = "medium",
    ) -> Dict[str, Any]:
        """Specialised sub-agent: queries the course / professor database and
        returns a single, data-driven response.

        Bypasses the multi-persona panel and compact-markdown formatting so the
        answer can include detailed section-by-section recommendations.

        For follow-up messages the LLM is given the conversation history so it
        can resolve references like *"What about Fall semester?"* against the
        previous query's parameters.

        :param user_message: The course-related user query.
        :param session_id: Current session identifier.
        :param response_length: Desired response verbosity.
        :returns: A dict with the course advisor response and metadata.
        """
        try:
            session = self.session_manager.get_session(session_id)

            effective_query = await self._resolve_course_followup(
                user_message, session
            )

            course_data = await self._query_course_database(effective_query)

            persona = self.get_persona("course_advisor")
            base_prompt = (
                persona.system_prompt if persona
                else "You are a CU Boulder course advisor with access to the course database."
            )

            profile_block = ""
            if hasattr(session, "user_profile_context") and session.user_profile_context:
                profile_block = f"\n\nSTUDENT PROFILE:\n{session.user_profile_context}\n"

            system_prompt = (
                f"{base_prompt}{profile_block}\n\n"
                f"{course_data or 'No course data available for this query.'}\n\n"
                "RESPONSE FORMAT — follow this EXACTLY (no other sections):\n"
                "\n"
                "### Top Pick\n"
                "Identify the single best option from the results and present it with\n"
                "section number, professor name, rating, schedule, and a brief reason\n"
                "why it is the best match.\n"
                "\n"
                "### Search Results\n"
                "List ALL matching options (including the top pick) with section number,\n"
                "professor name, rating, schedule, and seat availability. Use a numbered\n"
                "list. When criteria were relaxed, note what changed.\n"
                "\n"
                "RULES:\n"
                "- You have REAL data above. NEVER say you cannot access schedules or ratings.\n"
                "- Do NOT include 'Thought', 'What to do', or 'Next step' sections.\n"
                "- If no data was found, say so and suggest different criteria.\n"
            )

            context = []
            recent = session.messages[-8:] if len(session.messages) > 8 else session.messages
            for msg in recent:
                if msg.get("role") != "system":
                    context.append({"role": msg["role"], "content": msg["content"]})

            from app.core.bootstrap import create_llm_client
            llm = create_llm_client()
            token_map = {"short": 800, "medium": 1500, "long": 2000}

            response_text = await llm.generate(
                system_prompt=system_prompt,
                context=context,
                temperature=0.4,
                max_tokens=token_map.get(response_length, 1024),
            )

            session.append_message("course_advisor", response_text)

            self._set_last_agent_route(session_id, "course_db")

            return {
                "persona_id": "course_advisor",
                "persona_name": "Course Advisor",
                "content": response_text,
                "used_documents": True,
                "document_chunks_used": 0,
                "route": "course_db",
            }

        except Exception as e:
            LOG.error(f"Course query sub-agent failed: {e}")
            LOG.error(traceback.format_exc())
            return {
                "persona_id": "course_advisor",
                "persona_name": "Course Advisor",
                "content": "I'm having trouble accessing the course database right now. Please try again.",
                "used_documents": False,
                "document_chunks_used": 0,
                "route": "course_db",
            }

    async def _resolve_course_followup(
        self, user_message: str, session: ConversationContext
    ) -> str:
        """Turn a short follow-up into a fully-qualified course query by
        merging it with the previous turn's parameters.

        If the message already looks self-contained (has a course code or is
        long), return it unchanged.

        :param user_message: The user's latest message.
        :param session: Current conversation context.
        :returns: The expanded (or original) query string.
        """
        if re.search(r'\b[A-Z]{2,4}\s*\d{3,4}\b', user_message):
            return user_message
        if len(user_message.split()) >= 20:
            return user_message

        recent_turns = []
        for msg in session.messages[-10:]:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role in ("user", "course_advisor"):
                recent_turns.append(f"{role}: {content[:500]}")

        if not recent_turns:
            return user_message

        conversation_block = "\n".join(recent_turns)

        from app.core.bootstrap import create_llm_client
        from app.scrapers.course_scraper import KNOWN_TERMS
        llm = create_llm_client()

        terms_str = ", ".join(KNOWN_TERMS)
        system = (
            "You help resolve follow-up questions about CU Boulder courses.\n"
            "Given the conversation history and the user's latest message, "
            "produce a SINGLE self-contained course search query that keeps "
            "all parameters from the previous query but applies the "
            "modification the user is asking about.\n\n"
            f"AVAILABLE SEMESTERS IN THE DATABASE: {terms_str}\n"
            "When the user says a season like 'Fall' without a year, pick the "
            "matching semester from the available list above.\n\n"
            "Examples:\n"
            "  Previous: 'Find CSCI 1300 sections with professors rated 4+'\n"
            "  Follow-up: 'What about Fall semester?'\n"
            "  Output: 'Find CSCI 1300 sections for Fall 2025 with professors rated 4+'\n\n"
            "  Previous: 'ENES 1010 no 8am classes'\n"
            "  Follow-up: 'What about summer?'\n"
            "  Output: 'ENES 1010 no 8am classes for Summer 2026'\n\n"
            "  Previous: 'CSCI 2270 for Spring 2026'\n"
            "  Follow-up: 'Any sections with higher rated professors?'\n"
            "  Output: 'CSCI 2270 for Spring 2026 with professors rated 4+'\n\n"
            "Return ONLY the expanded query, nothing else. No explanation, "
            "no markdown, just the query string."
        )

        try:
            expanded = await llm.generate(
                system_prompt=system,
                context=[{
                    "role": "user",
                    "content": (
                        f"Conversation so far:\n{conversation_block}\n\n"
                        f"Latest message: {user_message}\n\n"
                        "Produce the expanded, self-contained query:"
                    ),
                }],
                temperature=0.1,
                max_tokens=200,
            )
            expanded = expanded.strip().strip('"').strip("'")
            if expanded and len(expanded) > 5:
                LOG.info(
                    f"Resolved follow-up: {user_message!r} -> {expanded!r}"
                )
                return expanded
        except Exception as e:
            LOG.warning(f"Follow-up resolution failed: {e}")

        return user_message

    async def _retrieve_relevant_documents(self, user_input: str, session_id: str, persona_id: str = "") -> str:
        """Enhanced document retrieval with document awareness and better attribution.

        :param user_input: The user's query text.
        :param session_id: Current session identifier.
        :param persona_id: Optional persona identifier for retrieval tuning.
        :returns: Formatted document context string, or empty string.
        """
        try:
            LOG.info(f"Retrieving documents for session_id: {session_id}")
            LOG.info(f"User input: {user_input[:100]}...")

            rag_manager = get_rag_manager()

            doc_stats = rag_manager.get_document_stats(session_id)
            LOG.info(f"Available documents for {session_id}: {doc_stats.get('total_documents', 0)} documents, {doc_stats.get('total_chunks', 0)} chunks")

            if doc_stats.get('documents'):
                for doc in doc_stats['documents']:
                    LOG.info(f"  - Document: {doc.get('filename', 'unknown')} ({doc.get('chunks', 0)} chunks)")

            if doc_stats.get('total_documents', 0) == 0:
                if session_id.startswith('chat_'):
                    LOG.warning(f"No documents found for chat session {session_id} - this may indicate session ID mismatch during upload")

                    alternative_formats = [
                        session_id.replace('chat_', ''),
                        session_id,
                    ]

                    for alt_session_id in alternative_formats:
                        if alt_session_id != session_id:
                            alt_stats = rag_manager.get_document_stats(alt_session_id)
                            if alt_stats.get('total_documents', 0) > 0:
                                LOG.warning(f"Found documents under alternative session ID {alt_session_id}: {alt_stats}")
                else:
                    LOG.info(f"No documents found for new session {session_id} - this is normal for new chats")

                return ""

            document_hint = self._extract_document_hint_from_query(user_input)
            LOG.info(f"Document hint extracted from query: {document_hint}")

            persona_context = self._get_enhanced_persona_context_keywords(persona_id)

            LOG.info(f"Searching with persona context: {persona_context[:100]}...")
            relevant_chunks = rag_manager.search_documents_with_context(
                query=user_input,
                session_id=session_id,
                persona_context=persona_context,
                n_results=6,
                document_hint=document_hint
            )

            LOG.info(f"Retrieved {len(relevant_chunks)} chunks for {persona_id}")

            if relevant_chunks:
                for i, chunk in enumerate(relevant_chunks):
                    relevance = chunk.get("relevance_score", 0)
                    doc_source = chunk.get("document_source", {})
                    filename = doc_source.get("filename", "unknown")
                    LOG.info(f"  Chunk {i+1}: {filename} (relevance: {relevance:.3f})")

            try:
                from app.core.global_rag import query_global_documents
                global_chunks = query_global_documents(user_input, n_results=3)
                if global_chunks:
                    relevant_chunks = (relevant_chunks or []) + global_chunks
                    LOG.info(f"Added {len(global_chunks)} global doc chunks")
            except Exception as ge:
                LOG.debug(f"Global RAG query skipped: {ge}")

            if not relevant_chunks:
                LOG.info(f"No relevant document chunks found for query: {user_input[:50]}...")
                return ""

            formatted_context = self._format_document_context_with_attribution(relevant_chunks, persona_id)

            LOG.info(f"Final document context length: {len(formatted_context)} characters")

            return formatted_context

        except Exception as e:
            LOG.error(f"Error retrieving documents for {persona_id} in session {session_id}: {e}")
            LOG.error(f"Error type: {type(e).__name__}")
            LOG.error(f"Full traceback: {traceback.format_exc()}")
            return ""

    def _extract_document_hint_from_query(self, query: str) -> Optional[str]:
        """Extract document name hints from user queries.

        :param query: The user's raw query text.
        :returns: A normalised document hint string, or ``None``.
        """
        query_lower = query.lower()

        document_indicators = [
            r"(?:my|the|in|from)\s+([a-zA-Z_\-]+\.(?:pdf|docx|txt|doc))",
            r"(?:my|the)\s+(dissertation|thesis|proposal|chapter|manuscript|paper)",
            r"(?:in|from)\s+(?:my\s+)?([a-zA-Z_\-\s]+(?:chapter|section|proposal))",
            r"(?:the|my)\s+([a-zA-Z_\-\s]+(?:document|file))",
        ]

        for pattern in document_indicators:
            matches = re.findall(pattern, query_lower)
            if matches:
                return matches[0].strip().replace(" ", "_")

        return None

    def _get_enhanced_persona_context_keywords(self, persona_id: str) -> str:
        """Return enhanced persona-specific keywords for better document retrieval.

        :param persona_id: Persona identifier to look up.
        :returns: A space-separated keyword string, or empty string.
        """
        enhanced_keywords = {
            "methodologist": "methodology research design experimental approach data collection sampling validity reliability statistical analysis quantitative qualitative mixed-methods procedures protocol IRB ethics",
            "theorist": "theory theoretical framework conceptual model literature review philosophy epistemology ontology paradigm abstract concepts hypothesis proposition postulate axiom",
            "pragmatist": "practical application implementation action steps next steps recommendation solution strategy timeline concrete advice roadmap execution deliverables milestones",
            "course_advisor": "course schedule class professor rating section enrollment registration prerequisite semester credit GPA degree requirement elective catalog",
        }
        return enhanced_keywords.get(persona_id, "")

    def _format_document_context_with_attribution(self, chunks: List[Dict], persona_id: str) -> str:
        """Format document context with clear attribution and source information.

        :param chunks: Retrieved document chunks with metadata.
        :param persona_id: The persona consuming this context.
        :returns: A formatted context string ready for prompt injection.
        """
        if not chunks:
            return ""

        high_quality_chunks = [
            chunk for chunk in chunks
            if chunk.get("relevance_score", 0) > 0.4
        ]

        if not high_quality_chunks:
            high_quality_chunks = chunks[:2]

        formatted_sections = []

        documents = {}
        for chunk in high_quality_chunks:
            doc_source = chunk.get("document_source", {})
            filename = doc_source.get("filename", "unknown")

            if filename not in documents:
                documents[filename] = {
                    "title": doc_source.get("document_title", filename),
                    "chunks": []
                }
            documents[filename]["chunks"].append(chunk)

        for filename, doc_data in documents.items():
            doc_title = doc_data["title"]
            doc_chunks = doc_data["chunks"]

            formatted_sections.append(f"=== FROM DOCUMENT: {doc_title} ===")

            for i, chunk in enumerate(doc_chunks):
                doc_source = chunk.get("document_source", {})
                section = doc_source.get("section", "unknown section")
                position = doc_source.get("chunk_position", "unknown position")
                relevance = chunk.get("relevance_score", 0)

                chunk_intro = f"[Source: {section}, Part {position}, Relevance: {relevance:.2f}]"
                formatted_sections.append(f"{chunk_intro}\n{chunk['text']}\n")

        total_docs = len(documents)
        total_chunks = len(high_quality_chunks)

        context_header = f"""
DOCUMENT CONTEXT FOR {persona_id.upper()} ANALYSIS:
Found {total_chunks} relevant passages from {total_docs} document(s).
Use this context to inform your response, and cite specific documents when referencing information.

"""

        formatted_context = context_header + "\n".join(formatted_sections)

        persona_instructions = self._get_persona_document_instructions(persona_id)
        formatted_context += f"\n\nSPECIAL INSTRUCTIONS FOR {persona_id.upper()}:\n{persona_instructions}"

        return formatted_context

    def _get_persona_document_instructions(self, persona_id: str) -> str:
        """Get persona-specific instructions for handling document context.

        :param persona_id: Persona identifier to look up.
        :returns: Instruction text for the given persona.
        """
        instructions = {
            "methodologist": """
When analyzing the document context:
- Focus on methodological rigor and research design elements
- Identify potential validity threats or methodological gaps
- Suggest specific improvements to research procedures
- Reference exact methodological frameworks mentioned in their documents
- Connect their approach to established research standards""",

            "theorist": """
When analyzing the document context:
- Examine theoretical positioning and conceptual clarity
- Identify theoretical gaps or inconsistencies
- Suggest theoretical frameworks that align with their work
- Evaluate the coherence between theory and research questions
- Reference specific theoretical concepts mentioned in their documents""",

            "pragmatist": """
When analyzing the document context:
- Extract actionable next steps from their current progress
- Identify immediate bottlenecks or decision points
- Prioritize tasks based on their timeline and constraints
- Translate theoretical concepts into practical implementation steps
- Reference specific deadlines or milestones mentioned in their documents"""
        }

        instructions["course_advisor"] = """
When analyzing the document context:
- Search for specific course codes, professor names, and scheduling details
- Cross-reference professor ratings with available sections
- Account for time preference buffers (8:15am is functionally the same as 8:00am)
- When exact matches aren't found, progressively relax constraints and offer alternatives
- Always include professor rating and schedule details in recommendations"""

        return instructions.get(persona_id, "Provide helpful guidance based on the document context.")

    async def _build_enhanced_context_for_persona(
        self,
        session: ConversationContext,
        persona: Persona,
        user_message: str,
        document_context: str,
    ) -> List[Dict[str, str]]:
        """Build enhanced context that properly integrates document information
        with conversation history.

        Ensures document context is properly preserved for both providers.

        :param session: Current conversation context.
        :param persona: The persona that will consume the context.
        :param user_message: The latest user message.
        :param document_context: Pre-formatted document context string.
        :returns: A list of message dicts suitable for LLM consumption.
        """
        enhanced_context = []

        recent_messages = session.messages[-6:] if len(session.messages) > 6 else session.messages

        has_documents = bool(document_context and document_context.strip() and len(document_context.strip()) > 50)

        user_profile_block = ""
        if hasattr(session, 'user_profile_context') and session.user_profile_context:
            user_profile_block = f"\n\nSTUDENT PROFILE:\n{session.user_profile_context}\nUse this background to personalise your advice.\n"

        if has_documents:
            uploaded_docs = session.uploaded_files if hasattr(session, 'uploaded_files') else []
            doc_list = ", ".join(uploaded_docs) if uploaded_docs else "uploaded documents"

            system_message = f"""{persona.system_prompt}{user_profile_block}

    CURRENT SESSION CONTEXT:
    The student has uploaded the following documents: {doc_list}

    DOCUMENT CONTENT:
    {document_context}

    IMPORTANT: When the student refers to "my document," "my dissertation," "my proposal," etc., they are referring to one of their uploaded documents. Use the document context above to understand which specific document they mean and reference it by name in your response.

    Always cite your sources when referencing information from their documents using the format: "According to your [document_name]..." or "In your [section_name] from [document_name]..."
    """

            enhanced_context.append({
                "role": "system",
                "content": system_message
            })
        else:
            system_message = f"""{persona.system_prompt}{user_profile_block}

    IMPORTANT: The student has NOT uploaded any documents yet. Do not reference any specific documents, files, or assume you have access to their research materials.

    If they mention "my document," "my dissertation," "my proposal," etc., you should:
    1. Acknowledge that you don't have access to their specific documents
    2. Ask them to upload the relevant files for more targeted advice
    3. Provide general guidance based on best practices in your area of expertise

    Do NOT make up document names or pretend to have access to files that don't exist."""

            enhanced_context.append({
                "role": "system",
                "content": system_message
            })

        for message in recent_messages:
            if message.get('role') != 'system':
                enhanced_context.append({
                    "role": message['role'],
                    "content": message['content']
                })

        return enhanced_context

    def _is_valid_response(self, response: str, persona_id: str) -> bool:
        """Validate response quality.

        :param response: The generated response text.
        :param persona_id: Identifier of the responding persona.
        :returns: ``True`` if the response passes quality checks.
        """
        if len(response) < 10 or len(response) > 5000:
            return False

        confusion_indicators = [
            f"Thank you, Dr. {persona_id.title()}",
            "Assistant:",
            f"Dr. {persona_id.title()} Advisor:",
            "excellent discussion, Assistant"
        ]

        return not any(indicator in response for indicator in confusion_indicators)

    def _get_persona_fallback(self, persona_id: str) -> str:
        """Get persona-specific fallback responses.

        :param persona_id: Persona identifier to look up.
        :returns: A fallback response string.
        """
        fallbacks = {
            "methodologist": "I'd be happy to help with your research methodology. What specific methodological approach are you considering?",
            "theorist": "I'd like to explore the theoretical foundation of your work. What conceptual framework guides your research?",
            "pragmatist": "Let's take a practical approach. What's the most pressing decision you need to make about your research right now?"
        }
        return fallbacks.get(persona_id, "I'd be happy to help. Could you provide more specific details about your question?")

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a session.

        :param session_id: Session identifier to inspect.
        :returns: A dict of session metadata, or ``None``.
        """
        session = self.session_manager.get_session(session_id)
        if session:
            return {
                "session_id": session.session_id,
                "message_count": len(session.messages),
                "uploaded_files": session.uploaded_files,
                "created_at": session.created_at.isoformat(),
                "last_accessed": session.last_accessed.isoformat(),
                "context_summary": self.context_manager.get_context_summary(session.messages)
            }
        return None

    def reset_session(self, session_id: str) -> bool:
        """Reset a session (clear messages but keep metadata).

        :param session_id: Session identifier to reset.
        :returns: ``True`` if the session was found and reset.
        """
        session = self.session_manager.get_session(session_id)
        if session:
            session.clear_messages()
            return True
        return False

    def delete_session(self, session_id: str) -> bool:
        """Delete a session completely.

        :param session_id: Session identifier to delete.
        :returns: ``True`` if the session was deleted.
        """
        return self.session_manager.delete_session(session_id)

    # TODO: Remove once all callers use _get_enhanced_persona_context_keywords
    def _get_persona_context_keywords(self, persona_id: str) -> str:
        """Legacy method -- use :meth:`_get_enhanced_persona_context_keywords` instead.

        :param persona_id: Persona identifier to look up.
        :returns: A space-separated keyword string.
        """
        return self._get_enhanced_persona_context_keywords(persona_id)

    async def chat_with_persona(self, user_input: str, persona_id: str, session_id: str, response_length: str = "medium") -> Dict[str, Any]:
        """Chat with a specific persona directly with consistent document access.

        :param user_input: The user's message.
        :param persona_id: Target persona identifier.
        :param session_id: Current session identifier.
        :param response_length: Desired response verbosity.
        :returns: A dict with the persona response and metadata.
        """
        try:
            persona = self.get_persona(persona_id)
            if not persona:
                return {
                    "error": f"Persona {persona_id} not found",
                    "available_personas": list(self.personas.keys()),
                    "persona_id": persona_id,
                    "persona_name": "Unknown"
                }

            session = self.session_manager.get_session(session_id)
            LOG.info(f"Chat with {persona_id} using session {session_id}")

            session.append_message("user", user_input)

            LOG.info(f"Generating response for {persona_id} with session {session_id}")

            response_data = await self._generate_single_persona_response(session, persona, response_length)

            session.append_message(persona_id, response_data["response"])

            return {
                "persona_id": persona_id,
                "persona_name": persona.name,
                "response": response_data.get("response", "I'm having trouble generating a response."),
                "used_documents": response_data.get("used_documents", False),
                "document_chunks_used": response_data.get("document_chunks_used", 0),
                "response_length": response_length,
                "context_quality": response_data.get("context_quality", "unknown"),
                "session_id": session_id,
                "type": "single_persona_response",
                "persona": {
                    "persona_id": persona_id,
                    "persona_name": persona.name,
                    "response": response_data.get("response", "I'm having trouble generating a response."),
                    "used_documents": response_data.get("used_documents", False),
                    "document_chunks_used": response_data.get("document_chunks_used", 0)
                }
            }

        except Exception as e:
            LOG.error(f"Error in chat_with_persona for {persona_id}: {e}")
            LOG.error(f"Session ID: {session_id}")
            LOG.error(f"Full traceback: {traceback.format_exc()}")

            return {
                "error": f"Error processing request: {str(e)}",
                "persona_id": persona_id,
                "persona_name": self.personas.get(persona_id, {}).name if persona_id in self.personas else "Unknown",
                "response": "I encountered an error while processing your request. Please try again.",
                "used_documents": False,
                "document_chunks_used": 0,
                "response_length": response_length,
                "context_quality": "error",
                "session_id": session_id,
                "type": "error"
            }

    async def synthesize_responses(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine multiple advisor responses into a single synthesised answer.

        :param responses: A list of advisor response dicts.
        :returns: A synthesised response dict.
        """
        try:
            llm = next(iter(self.personas.values())).llm
            advisor_texts = "\n\n".join(
                f"**{r['persona_name']}:** {r['content']}" for r in responses
            )
            system_prompt = (
                "You are a synthesis assistant. You receive multiple advisor responses to "
                "the same student question. Your job is to merge them into ONE comprehensive "
                "answer using exactly this structure:\n\n"
                "### Thought\n"
                "A single paragraph (2-4 sentences) that weaves together the key insights "
                "from every advisor. Include all distinct reasons and perspectives; do not "
                "drop any advisor's unique angle.\n\n"
                "### What to do\n"
                "A merged bullet list. If two advisors gave similar advice, combine them "
                "into one bullet. If an advisor offered a unique idea, keep it as its own "
                "bullet. Aim for 4-6 bullets total.\n\n"
                "### Next steps\n"
                "A bullet list of concrete, immediate actions. Merge similar next-step ideas "
                "into single bullets; keep unique ones separate. Each bullet should be one "
                "imperative sentence.\n\n"
                "Rules:\n"
                "- Use GitHub-Flavored Markdown, `###` headings, `-` bullets.\n"
                "- Do NOT mention advisor names or say 'the Career Coach suggested...'.\n"
                "- Write as one unified voice.\n"
                "- Never repeat the same idea in different sections."
            )
            result = await llm.generate(
                system_prompt=system_prompt,
                context=[{"role": "user", "content": advisor_texts}],
                temperature=0.3,
                max_tokens=2048,
            )
            return {
                "persona_id": "orchestrator",
                "persona_name": "Synthesized Answer",
                "content": result,
                "used_documents": any(r.get("used_documents") for r in responses),
                "document_chunks_used": sum(r.get("document_chunks_used", 0) for r in responses),
            }
        except Exception as e:
            LOG.error(f"Synthesis failed: {e}")
            return responses[0] if responses else {
                "persona_id": "orchestrator",
                "persona_name": "Synthesized Answer",
                "content": "Unable to synthesize responses.",
                "used_documents": False,
                "document_chunks_used": 0,
            }

    @staticmethod
    def _extract_identity(persona: Persona) -> str:
        """Extract just the role description and expertise bullets from a
        persona's system prompt -- enough for routing, not the full prompt.

        :param persona: The persona to extract identity from.
        :returns: A compact identity string.
        """
        prompt = persona.system_prompt or ""
        lines = prompt.split("\n")
        identity_lines: List[str] = []
        in_expertise = False
        for line in lines:
            stripped = line.strip()
            if not identity_lines and stripped and not stripped.startswith("**"):
                identity_lines.append(stripped)
                continue
            if stripped.upper().startswith("**YOUR EXPERTISE"):
                in_expertise = True
                continue
            if in_expertise:
                if stripped.startswith("- "):
                    identity_lines.append(stripped)
                elif stripped.startswith("**") or (stripped and not stripped.startswith("-")):
                    break
        return "\n".join(identity_lines) if identity_lines else persona.name

    async def get_top_personas(self, session_id: str, k: int = 3, allowed_ids: Optional[List[str]] = None) -> List[str]:
        """Select advisors using a diversity-aware strategy.

        Picks one advisor most directly relevant to the user's query and
        two with deliberately different but potentially useful perspectives.
        Falls back to default persona order if the LLM call fails.

        :param session_id: Current session identifier.
        :param k: Number of personas to select.
        :param allowed_ids: Optional whitelist of persona identifiers.
        :returns: An ordered list of selected persona identifiers.
        """
        try:
            session = self.session_manager.get_session(session_id)

            pool = {pid: p for pid, p in self.personas.items()
                    if allowed_ids is None or pid in allowed_ids}
            if not pool:
                LOG.warning("No personas in allowed pool.")
                return list(self.personas.keys())[:k]

            if len(pool) <= k:
                return list(pool.keys())

            llm = next(iter(pool.values())).llm

            recent_context = "\n".join(
                msg['content'] for msg in session.get_recent_messages(5)
            )

            persona_descriptions = "\n".join([
                f"- ID: {p.id} | {p.name}\n  {self._extract_identity(p)}"
                for p in pool.values()
            ])

            app_title = get_settings().app.title

            prompt = (
                f"A student is using {app_title}. Based on the conversation, "
                "select 3 advisors to respond.\n\n"
                "SELECTION RULES:\n"
                "1. Pick the 1 advisor whose expertise is MOST directly relevant "
                "to what the student is asking about. Place them first.\n"
                "2. Then pick 2 MORE advisors whose expertise is DIFFERENT from "
                "the first and from each other, but who could offer a useful "
                "alternative angle the student might not have considered.\n"
                "   - Prefer advisors whose perspective CONTRASTS with the top pick "
                "(e.g. if #1 is academic, pick a wellness or career voice).\n\n"
                "Respond ONLY with a JSON list of exactly 3 advisor IDs.\n"
                'Example: ["academic_planner", "wellness_advisor", "career_coach"]\n\n'
                f"--- Conversation ---\n{recent_context}\n\n"
                f"--- Available Advisors ---\n{persona_descriptions}"
            )

            llm_response = await llm.generate(
                system_prompt="You select advisors for a student advising app. Return only JSON.",
                context=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=150,
            )

            try:
                top_ids = json.loads(llm_response.strip())
            except json.JSONDecodeError:
                top_ids = re.findall(r'"(.*?)"', llm_response)
                LOG.warning(f"Fallback JSON extraction used: {top_ids}")

            valid_ids = [pid for pid in top_ids if pid in pool]

            if len(valid_ids) < k:
                LOG.warning(f"LLM returned insufficient or invalid IDs ({valid_ids}), padding with remaining")
                remaining = [pid for pid in pool if pid not in valid_ids]
                valid_ids.extend(remaining[: k - len(valid_ids)])

            return valid_ids[:k]

        except Exception as e:
            LOG.error(f"Error selecting top personas: {e}")
            return list(pool.keys())[:k]
