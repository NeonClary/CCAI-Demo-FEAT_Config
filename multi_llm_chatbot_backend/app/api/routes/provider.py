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
Provider switching, vLLM model discovery, and per-persona LLM assignment.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

import app.core.bootstrap as bootstrap
from app.config import get_settings
from app.llm.vllm_client import discover_all_models

LOG = logging.getLogger(__name__)

router = APIRouter()

# ── Pydantic request models ──────────────────────────────────────────

class ProviderSwitch(BaseModel):
    provider: str


class ModelAssignment(BaseModel):
    model_id: str
    client_id: str
    api_url: str


class OllamaAssignments(BaseModel):
    orchestrator: Optional[ModelAssignment] = None
    default: Optional[ModelAssignment] = None
    personas: Optional[Dict[str, ModelAssignment]] = None


# ── Provider info ────────────────────────────────────────────────────

@router.get("/current-provider")
async def get_current_provider() -> Dict[str, Any]:
    llm = bootstrap.llm
    return {
        "current_provider": bootstrap.CURRENT_PROVIDER,
        "available_providers": bootstrap.AVAILABLE_PROVIDERS,
        "model_info": {
            "name": getattr(llm, "model_name", "unknown"),
            "provider": bootstrap.CURRENT_PROVIDER,
        },
    }


@router.post("/switch-provider")
async def switch_provider(provider_data: ProviderSwitch) -> Dict[str, Any]:
    if provider_data.provider not in bootstrap.AVAILABLE_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider: {provider_data.provider}. "
                   f"Available: {bootstrap.AVAILABLE_PROVIDERS}",
        )

    try:
        bootstrap.CURRENT_PROVIDER = provider_data.provider
        bootstrap.llm = bootstrap.create_llm_client(bootstrap.CURRENT_PROVIDER)

        new_personas = bootstrap.rebuild_personas_for_provider(bootstrap.CURRENT_PROVIDER)
        bootstrap.chat_orchestrator.personas.clear()
        for persona in new_personas:
            bootstrap.chat_orchestrator.register_persona(persona)

        return {
            "message": f"Successfully switched to {bootstrap.CURRENT_PROVIDER}",
            "current_provider": bootstrap.CURRENT_PROVIDER,
            "model_info": {
                "name": getattr(bootstrap.llm, "model_name", "unknown"),
                "provider": bootstrap.CURRENT_PROVIDER,
            },
        }
    except Exception as exc:
        LOG.exception("Failed to switch provider")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/switch-model")
async def switch_model(model_name: str = Body(...)) -> Dict[str, Any]:
    if "gemini" in model_name.lower():
        return await switch_provider(ProviderSwitch(provider="gemini"))
    return await switch_provider(ProviderSwitch(provider="ollama"))


@router.get("/current-model")
async def get_current_model() -> Dict[str, str]:
    return {
        "model": getattr(bootstrap.llm, "model_name", "unknown"),
        "provider": bootstrap.CURRENT_PROVIDER,
    }


# ── vLLM model discovery ────────────────────────────────────────────

@router.get("/ollama/models")
async def list_ollama_models() -> Dict[str, Any]:
    """Query every configured vLLM endpoint and return available models.

    When the active provider is ``hybrid``, a Gemini entry is prepended
    so users can assign Gemini to any role alongside vLLM models.
    """
    settings = get_settings()
    vllm_cfg = settings.llm.vllm

    models: List[Dict[str, Any]] = []

    if bootstrap.CURRENT_PROVIDER == "hybrid":
        models.append({
            "model_id": settings.llm.gemini.model,
            "client_id": "gemini",
            "client_name": "Google Gemini",
            "api_url": "gemini",
        })

    if vllm_cfg.clients:
        clients = [
            {"id": c.id, "name": c.name, "api_url": c.api_url}
            for c in vllm_cfg.clients
        ]
        vllm_models = await discover_all_models(clients, vllm_cfg.api_key)
        models.extend(vllm_models)

    if not models:
        return {"models": [], "message": "No models available."}

    return {"models": models}


# ── Per-persona LLM assignment ───────────────────────────────────────

@router.get("/ollama/assignments")
async def get_ollama_assignments() -> Dict[str, Any]:
    return {"assignments": bootstrap.ollama_assignments}


@router.post("/ollama/assignments")
async def set_ollama_assignments(body: OllamaAssignments) -> Dict[str, Any]:
    """Save per-persona LLM assignments and re-wire personas if Ollama
    is the active provider."""
    assignments: Dict[str, Any] = {}
    if body.orchestrator:
        assignments["orchestrator"] = body.orchestrator.dict()
    if body.default:
        assignments["default"] = body.default.dict()
    if body.personas:
        assignments["personas"] = {
            pid: a.dict() for pid, a in body.personas.items()
        }

    bootstrap.ollama_assignments = assignments

    if bootstrap.CURRENT_PROVIDER in ("ollama", "hybrid"):
        bootstrap.llm = bootstrap.create_llm_client(bootstrap.CURRENT_PROVIDER)
        new_personas = bootstrap.rebuild_personas_for_provider(bootstrap.CURRENT_PROVIDER)
        bootstrap.chat_orchestrator.personas.clear()
        for persona in new_personas:
            bootstrap.chat_orchestrator.register_persona(persona)

    return {
        "message": "Assignments saved",
        "assignments": bootstrap.ollama_assignments,
    }
