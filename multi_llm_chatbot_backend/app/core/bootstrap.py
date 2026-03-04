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

from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.llm.llm_client import LLMClient
from app.llm.improved_gemini_client import ImprovedGeminiClient
from app.llm.improved_ollama_client import ImprovedOllamaClient
from app.llm.vllm_client import VLLMClient
from app.core.improved_orchestrator import ImprovedChatOrchestrator
from app.models.default_personas import get_default_personas, get_personas_with_llm_map

settings = get_settings()

CURRENT_PROVIDER: str = "gemini"
AVAILABLE_PROVIDERS: List[str] = ["gemini", "ollama", "hybrid"]

GEMINI_CLIENT_ID = "gemini"

# Per-persona model assignments (used when provider is "ollama" or "hybrid").
# Keys: "orchestrator" -> {client_id, model_id, api_url}
#        "default"     -> same shape (fallback for all personas)
#        "personas"    -> {persona_id: {client_id, model_id, api_url}, ...}
ollama_assignments: Dict[str, Any] = {}


def _is_gemini_assignment(assignment: Optional[Dict]) -> bool:
    return bool(assignment and assignment.get("client_id") == GEMINI_CLIENT_ID)


def _client_from_assignment(assignment: Dict) -> LLMClient:
    """Build the appropriate LLM client from a single assignment dict."""
    if _is_gemini_assignment(assignment):
        return ImprovedGeminiClient(
            model_name=assignment.get("model_id") or settings.llm.gemini.model,
        )
    return VLLMClient(
        api_url=assignment["api_url"],
        api_key=settings.llm.vllm.api_key,
        model_name=assignment["model_id"],
        client_id=assignment.get("client_id", ""),
    )


def create_llm_client(provider: Optional[str] = None) -> LLMClient:
    """
    Create and return an LLM client for the specified provider.

    :param provider: Name of the LLM provider. Falls back to
        ``CURRENT_PROVIDER`` when *None*.
    :returns: Configured LLM client instance.
    """
    if provider is None:
        provider = CURRENT_PROVIDER
    if provider == "gemini":
        return ImprovedGeminiClient(model_name=settings.llm.gemini.model)
    elif provider in ("ollama", "hybrid"):
        return _resolve_assignment("orchestrator")
    else:
        return ImprovedOllamaClient(
            model_name=settings.llm.ollama.model,
            base_url=settings.llm.ollama.base_url,
        )


def _resolve_assignment(role: str) -> LLMClient:
    """Resolve an assignment for *role* and return the correct client.

    Falls back through: persona override -> named role -> default ->
    first configured vLLM client -> local Ollama.
    """
    assignment = (
        ollama_assignments.get("personas", {}).get(role)
        or ollama_assignments.get(role)
        or ollama_assignments.get("default")
    )

    if assignment:
        return _client_from_assignment(assignment)

    vllm_cfg = settings.llm.vllm
    if vllm_cfg.clients:
        first = vllm_cfg.clients[0]
        return VLLMClient(
            api_url=first.api_url,
            api_key=vllm_cfg.api_key,
            model_name="",
            client_id=first.id,
        )

    return ImprovedOllamaClient(
        model_name=settings.llm.ollama.model,
        base_url=settings.llm.ollama.base_url,
    )


def rebuild_personas_for_provider(provider: str) -> List:
    """Create persona objects wired to the correct LLM(s) for *provider*."""
    if provider in ("ollama", "hybrid"):
        default_llm = _resolve_assignment("default")
        persona_overrides = ollama_assignments.get("personas")
        if persona_overrides:
            persona_llm_map: Dict[str, LLMClient] = {
                pid: _client_from_assignment(a)
                for pid, a in persona_overrides.items()
            }
            return get_personas_with_llm_map(default_llm, persona_llm_map)
        return get_default_personas(default_llm)
    else:
        return get_default_personas(create_llm_client(provider))


llm = create_llm_client()
chat_orchestrator = ImprovedChatOrchestrator()

DEFAULT_PERSONAS = get_default_personas(llm)
for persona in DEFAULT_PERSONAS:
    chat_orchestrator.register_persona(persona)
