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
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
import re
from datetime import datetime

LOG = logging.getLogger(__name__)


@dataclass
class ContextWindow:
    """Represents a context window for LLM processing."""

    messages: List[Dict]
    total_tokens: int
    truncated: bool = False


class ContextManager:
    """Unified context management for consistent LLM behavior."""

    def __init__(
        self,
        max_context_tokens: int = 8000,
        preserve_recent_messages: int = 5,
        chars_per_token: float = 4.0,
    ) -> None:
        self.max_context_tokens: int = max_context_tokens
        self.preserve_recent_messages: int = preserve_recent_messages
        self.chars_per_token: float = chars_per_token

    def prepare_context_for_llm(
        self,
        messages: List[Dict],
        system_prompt: str,
        llm_provider: str = "gemini",
    ) -> ContextWindow:
        """
        Prepare context for LLM with intelligent windowing and formatting.

        :param messages: Conversation message history.
        :param system_prompt: System prompt to prepend.
        :param llm_provider: Target LLM provider name.
        :returns: A :class:`ContextWindow` ready for the provider.
        """
        system_tokens: int = self._estimate_tokens(system_prompt)
        available_tokens: int = self.max_context_tokens - system_tokens - 500

        context_messages: List[Dict] = self._get_optimal_context_window(
            messages, available_tokens
        )

        formatted_messages: List[Dict] = self._format_for_provider(
            context_messages, system_prompt, llm_provider
        )

        return ContextWindow(
            messages=formatted_messages,
            total_tokens=self._estimate_tokens_for_messages(formatted_messages),
            truncated=len(context_messages) < len(messages),
        )

    def _get_optimal_context_window(
        self, messages: List[Dict], token_budget: int
    ) -> List[Dict]:
        """
        Select optimal messages for context window using recency + relevance.

        :param messages: Full message history.
        :param token_budget: Maximum token count to fit within.
        :returns: Subset of messages fitting the budget.
        """
        if not messages:
            return []

        recent_messages: List[Dict] = messages[-self.preserve_recent_messages:]
        recent_tokens: int = self._estimate_tokens_for_messages(recent_messages)

        if recent_tokens >= token_budget:
            return self._truncate_to_fit(recent_messages, token_budget)

        remaining_budget: int = token_budget - recent_tokens
        older_messages: List[Dict] = (
            messages[: -self.preserve_recent_messages]
            if len(messages) > self.preserve_recent_messages
            else []
        )

        scored_messages: List[Tuple[Dict, float]] = (
            self._score_messages_for_relevance(
                older_messages, messages[-1]["content"] if messages else ""
            )
        )

        selected_older: List[Dict] = []
        for message, score in scored_messages:
            message_tokens: int = self._estimate_tokens(message["content"])
            if message_tokens <= remaining_budget:
                selected_older.append(message)
                remaining_budget -= message_tokens
            else:
                break

        return selected_older + recent_messages

    def _score_messages_for_relevance(
        self, messages: List[Dict], current_query: str
    ) -> List[Tuple[Dict, float]]:
        """
        Score messages by relevance to current query and recency.

        :param messages: Older messages to score.
        :param current_query: The latest user query for keyword overlap.
        :returns: List of ``(message, score)`` tuples sorted descending.
        """
        scored: List[Tuple[Dict, float]] = []
        current_query_lower: str = current_query.lower()

        for i, message in enumerate(messages):
            score: float = 0.0
            content_lower: str = message["content"].lower()

            recency_score: float = (i + 1) / len(messages) * 0.3

            current_words = set(current_query_lower.split())
            message_words = set(content_lower.split())
            overlap: int = len(current_words.intersection(message_words))
            keyword_score: float = min(
                overlap / max(len(current_words), 1) * 0.4, 0.4
            )

            role_score: float = (
                0.3 if message["role"] in ["user", "document"] else 0.1
            )

            score = recency_score + keyword_score + role_score
            scored.append((message, score))

        return sorted(scored, key=lambda x: x[1], reverse=True)

    def _truncate_to_fit(
        self, messages: List[Dict], token_budget: int
    ) -> List[Dict]:
        """
        Truncate messages to fit within token budget, preserving most recent.

        :param messages: Messages to truncate.
        :param token_budget: Token budget to honour.
        :returns: Truncated list of messages.
        """
        result: List[Dict] = []
        current_tokens: int = 0

        for message in reversed(messages):
            message_tokens: int = self._estimate_tokens(message["content"])
            if current_tokens + message_tokens <= token_budget:
                result.insert(0, message)
                current_tokens += message_tokens
            else:
                break

        return result

    def _format_for_provider(
        self,
        messages: List[Dict],
        system_prompt: str,
        provider: str,
    ) -> List[Dict]:
        """
        Format messages for a specific LLM provider.

        :param messages: Conversation messages.
        :param system_prompt: System prompt text.
        :param provider: Target provider name.
        :returns: Provider-formatted message list.
        """
        if provider.lower() == "gemini":
            return self._format_for_gemini(messages, system_prompt)
        elif provider.lower() in ["ollama", "mistral"]:
            return self._format_for_ollama(messages, system_prompt)
        else:
            return [{"role": "system", "content": system_prompt}] + messages

    def _format_for_gemini(
        self, messages: List[Dict], system_prompt: str
    ) -> List[Dict]:
        """
        Format messages for Gemini API.

        Uses ``user``/``model`` roles with the ``parts`` structure.
        Properly handles system messages and document context.

        :param messages: Conversation messages.
        :param system_prompt: System prompt text.
        :returns: Gemini-formatted message list.
        """
        formatted: List[Dict] = []

        system_message_content: str = ""
        conversation_messages: List[Dict] = []

        if system_prompt:
            system_message_content = system_prompt

        for message in messages:
            role: str = message["role"]
            content: str = message["content"]

            if role == "system":
                if system_message_content:
                    system_message_content += f"\n\n{content}"
                else:
                    system_message_content = content
            else:
                conversation_messages.append(message)

        if system_message_content:
            formatted.extend(
                [
                    {
                        "role": "user",
                        "parts": [{"text": system_message_content}],
                    },
                    {
                        "role": "model",
                        "parts": [
                            {
                                "text": "I understand. I'll follow these instructions and use the document context you've provided."
                            }
                        ],
                    },
                ]
            )

        for message in conversation_messages:
            role = message["role"]
            content = message["content"]

            if role == "user":
                formatted.append(
                    {"role": "user", "parts": [{"text": content}]}
                )
            elif role in [
                "assistant",
                "methodologist",
                "theorist",
                "pragmatist",
            ]:
                formatted.append(
                    {"role": "model", "parts": [{"text": content}]}
                )
            elif role == "document":
                formatted.append(
                    {
                        "role": "user",
                        "parts": [{"text": f"[Context Document] {content}"}],
                    }
                )

        return formatted

    def _format_for_ollama(
        self, messages: List[Dict], system_prompt: str
    ) -> str:
        """
        Format messages for Ollama (returns formatted prompt string).

        :param messages: Conversation messages.
        :param system_prompt: System prompt text.
        :returns: Newline-separated prompt string.
        """
        parts: List[str] = [system_prompt] if system_prompt else []

        for message in messages:
            role: str = message["role"].capitalize()
            content: str = message["content"]

            if role == "Document":
                parts.append(f"Context: {content}")
            else:
                parts.append(f"{role}: {content}")

        parts.append("Assistant:")
        return "\n\n".join(parts)

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        :param text: Input text.
        :returns: Estimated token count.
        """
        return int(len(text) / self.chars_per_token)

    def _estimate_tokens_for_messages(self, messages: List[Dict]) -> int:
        """
        Estimate total tokens for a list of messages.

        :param messages: Messages (dicts or a single string).
        :returns: Estimated total token count.
        """
        if isinstance(messages, str):
            return self._estimate_tokens(messages)

        total: int = 0
        for message in messages:
            if isinstance(message, dict):
                if "content" in message:
                    total += self._estimate_tokens(message["content"])
                elif "parts" in message:
                    for part in message["parts"]:
                        if "text" in part:
                            total += self._estimate_tokens(part["text"])
            else:
                total += self._estimate_tokens(str(message))

        return total

    def get_context_summary(self, messages: List[Dict]) -> Dict[str, Any]:
        """
        Get summary information about context.

        :param messages: Conversation messages.
        :returns: Dictionary with message counts, token estimate, and role
            breakdown.
        """
        if not messages:
            return {"total_messages": 0, "estimated_tokens": 0, "roles": {}}

        role_counts: Dict[str, int] = {}
        for message in messages:
            role: str = message.get("role", "unknown")
            role_counts[role] = role_counts.get(role, 0) + 1

        return {
            "total_messages": len(messages),
            "estimated_tokens": self._estimate_tokens_for_messages(messages),
            "roles": role_counts,
            "oldest_message": (
                messages[0].get("timestamp", "unknown") if messages else None
            ),
            "newest_message": (
                messages[-1].get("timestamp", "unknown") if messages else None
            ),
        }


context_manager = ContextManager()


def get_context_manager() -> ContextManager:
    """
    Get the global context manager instance.

    :returns: Singleton :class:`ContextManager`.
    """
    return context_manager
