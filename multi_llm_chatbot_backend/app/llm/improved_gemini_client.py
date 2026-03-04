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
import os
import re
from typing import Dict, List, Optional

import httpx

from app.config import get_settings
from app.core.context_manager import get_context_manager
from app.llm.llm_client import LLMClient

LOG = logging.getLogger(__name__)

_shared_client: Optional[httpx.AsyncClient] = None


def _get_shared_client() -> httpx.AsyncClient:
    """
    Return the module-level shared HTTP client, creating one if needed.

    :returns: The shared async HTTP client.
    """
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(
            timeout=60.0,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
    return _shared_client


async def close_shared_client() -> None:
    """
    Close the shared HTTP client and release resources.
    """
    global _shared_client
    if _shared_client and not _shared_client.is_closed:
        await _shared_client.aclose()
        _shared_client = None


class ImprovedGeminiClient(LLMClient):
    """Gemini LLM client with improved context management."""

    def __init__(self, model_name: Optional[str] = None) -> None:
        """
        Initialize the Gemini client.

        :param model_name: Optional model name override; defaults to the value
            from config.
        """
        settings = get_settings()
        if model_name is None:
            model_name = settings.llm.gemini.model

        self.model_name = model_name
        self.api_key = settings.llm.gemini.api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Gemini API key not set. Provide it in config.yaml "
                "(llm.gemini.api_key) or as GEMINI_API_KEY env var."
            )

        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.context_manager = get_context_manager()

    async def generate(
        self,
        system_prompt: str,
        context: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        Generate a response using improved context management.

        :param system_prompt: The system prompt defining the persona/role.
        :param context: List of conversation messages with 'role' and 'content'
            keys.
        :param temperature: Sampling temperature for generation.
        :param max_tokens: Maximum number of tokens to generate.
        :returns: The generated response text.
        """
        try:
            context_window = self.context_manager.prepare_context_for_llm(
                messages=context,
                system_prompt=system_prompt,
                llm_provider="gemini"
            )

            LOG.debug(
                f"Context prepared: {len(context_window.messages)} messages, "
                f"~{context_window.total_tokens} tokens, "
                f"truncated={context_window.truncated}"
            )

            LOG.debug(f"Gemini payload preview: {str(context_window.messages)[:500]}...")

            payload = {
                "contents": context_window.messages,
                "generationConfig": {
                    "temperature": temperature,
                    "topK": 40,
                    "topP": 0.9,
                    "maxOutputTokens": max_tokens,
                    "stopSequences": [
                        "</END>", "Student:", "Question:",
                        "\n\nStudent:", "\n\nQuestion:",
                    ]
                },
                "safetySettings": [
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    }
                ]
            }

            client = _get_shared_client()
            response = await client.post(
                f"{self.base_url}/{self.model_name}:generateContent",
                json=payload,
                headers={"x-goog-api-key": self.api_key},
            )
            response.raise_for_status()

            result = response.json()

            if "candidates" not in result or not result["candidates"]:
                LOG.error(f"No candidates in Gemini response: {result}")
                return "I apologize, but I'm unable to generate a response right now. Please try again."

            candidate = result["candidates"][0]

            if "content" not in candidate or "parts" not in candidate["content"]:
                LOG.error(f"Invalid candidate structure: {candidate}")
                return "I apologize, but I received an unexpected response format. Please try again."

            parts = candidate["content"]["parts"]
            text = ""
            for part in parts:
                if part.get("thought"):
                    continue
                text = part.get("text", "")

            text = text.strip()

            if not text:
                LOG.warning("Empty response from Gemini")
                return "I apologize, but I couldn't generate a meaningful response. Please try rephrasing your question."

            return self._clean_response(text)

        except httpx.HTTPStatusError as e:
            LOG.error(f"Gemini API HTTP error: {e.response.status_code} - {e.response.text}")
            return "I'm experiencing issues connecting to the AI service. Please try again."
        except httpx.TimeoutException:
            LOG.error("Gemini API timeout")
            return "The AI service is taking too long to respond. Please try again."
        except Exception as e:
            LOG.error(f"Unexpected error in Gemini client: {str(e)}")
            return "I encountered an unexpected error. Please try again."

    @staticmethod
    def _clean_response(response: str) -> str:
        """
        Clean up response text by normalizing whitespace and line breaks.

        :param response: Raw response text from the LLM.
        :returns: Cleaned response text.
        """
        response = response.strip()
        response = response.replace("\r\n", "\n").replace("\r", "\n")
        lines = [ln.rstrip() for ln in response.split("\n")]
        response = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
        return response
