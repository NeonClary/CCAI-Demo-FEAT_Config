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
import re
from typing import Dict, List, Optional

import httpx

from app.core.context_manager import get_context_manager
from app.llm.llm_client import LLMClient

LOG = logging.getLogger(__name__)

_shared_client: Optional[httpx.AsyncClient] = None


def _get_shared_client(base_url: str) -> httpx.AsyncClient:
    """
    Return the module-level shared HTTP client, creating one if needed.

    :param base_url: The base URL for the Ollama API server.
    :returns: The shared async HTTP client.
    """
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(
            timeout=60.0,
            base_url=base_url,
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


class ImprovedOllamaClient(LLMClient):
    """Ollama LLM client with improved context management."""

    def __init__(
        self,
        model_name: str = "llama3.2:1b",
        base_url: str = "http://localhost:11434",
    ) -> None:
        """
        Initialize the Ollama client.

        :param model_name: Name of the Ollama model to use.
        :param base_url: Base URL of the Ollama API server.
        """
        self.model_name = model_name
        self.base_url = base_url
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
                llm_provider="ollama"
            )

            LOG.debug(
                f"Context prepared: ~{context_window.total_tokens} tokens, "
                f"truncated={context_window.truncated}"
            )

            formatted_prompt = context_window.messages

            payload = {
                "model": self.model_name,
                "prompt": formatted_prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "top_p": 0.9,
                    "top_k": 40,
                    "num_predict": max_tokens,
                    "repeat_penalty": 1.1,
                    "stop": [
                        "</END>", "\n\nStudent:", "\n\nUser:",
                        "Question:", "Student:",
                    ]
                }
            }

            client = _get_shared_client(self.base_url)
            response = await client.post("/api/generate", json=payload)
            response.raise_for_status()

            result = response.json()
            text = result.get("response", "").strip()

            return self._clean_response(text)

        except httpx.ConnectError:
            LOG.error(f"Cannot connect to Ollama at {self.base_url}")
            return "I'm unable to connect to the local AI service. Please ensure Ollama is running."
        except httpx.TimeoutException:
            LOG.error("Ollama request timeout")
            return "The AI service is taking too long to respond. Please try again."
        except httpx.HTTPStatusError as e:
            LOG.error(f"Ollama HTTP error: {e.response.status_code}")
            return "The AI service encountered an error. Please try again."
        except Exception as e:
            LOG.error(f"Unexpected error in Ollama client: {str(e)}")
            return "I encountered an unexpected error. Please try again."

    @staticmethod
    def _clean_response(response: str) -> str:
        """
        Clean up common response issues such as unwanted prefixes and fluff.

        :param response: Raw response text from the LLM.
        :returns: Cleaned response text.
        """
        prefixes_to_remove = [
            "Here are 2-3 sentence", "Here's an expansion", "Assistant:",
            "Dr. Methodologist:", "Dr. Theorist:", "Dr. Pragmatist:",
            "Methodologist Advisor:", "Theorist Advisor:", "Pragmatist Advisor:",
        ]

        for prefix in prefixes_to_remove:
            if response.startswith(prefix):
                response = response[len(prefix):].strip()

        sentences = response.split('.')
        if len(sentences) > 1 and len(sentences[-1].strip()) < 10:
            response = '.'.join(sentences[:-1]) + '.'

        fluff_patterns = [
            "conceptual insights:", "actionable advice:", "my inquisitive student",
            "excellent question", "thank you for", "assistant!"
        ]

        for pattern in fluff_patterns:
            response = response.replace(pattern, "").strip()

        response = response.replace("\r\n", "\n").replace("\r", "\n")
        lines = [ln.rstrip() for ln in response.split("\n")]
        response = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
        return response

    @staticmethod
    def _is_poor_quality(response: str) -> bool:
        """
        Check if response quality is poor based on common indicators.

        :param response: Response text to evaluate.
        :returns: True if the response shows poor quality indicators.
        """
        poor_indicators = [
            "Thank you, Dr." in response,
            "Assistant:" in response,
            len(response.split()) > 150,
            response.count("?") > 3,
        ]
        return any(poor_indicators)
