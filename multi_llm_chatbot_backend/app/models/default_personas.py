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
Persona registry — now driven by ``config.yaml``.

The heavy persona definitions have moved into ``config.yaml`` (under the
``personas`` key).  This module reads them via :func:`app.config.get_settings`
and exposes the same public API the rest of the codebase already relies on.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from app.config import get_settings
from app.llm.llm_client import LLMClient
from app.models.persona import Persona


def _build_personas_dict() -> Dict[str, Any]:
    """Build the ``{id: {name, system_prompt, temperature}}`` registry from
    the YAML configuration.

    :returns: Mapping of persona ID to its configuration dict.
    :rtype:   dict
    """
    cfg = get_settings()
    base_prompt = cfg.personas.base_prompt.strip()
    registry: Dict[str, Any] = {}
    for p in cfg.personas.items:
        full_prompt = p.persona_prompt.strip()
        if base_prompt:
            full_prompt = f"{full_prompt}\n\n{base_prompt}"
        registry[p.id] = {
            "name": p.name,
            "type": getattr(p, "type", "advisor"),
            "system_prompt": full_prompt,
            "default_temperature": p.temperature,
        }
    return registry


_DEFAULT_PERSONAS: Optional[Dict[str, Any]] = None


def _get_registry() -> Dict[str, Any]:
    """Return the lazily-initialised persona registry singleton.

    :returns: Mapping of persona ID to its configuration dict.
    :rtype:   dict
    """
    global _DEFAULT_PERSONAS
    if _DEFAULT_PERSONAS is None:
        _DEFAULT_PERSONAS = _build_personas_dict()
    return _DEFAULT_PERSONAS


# ------------------------------------------------------------------
# Public API — unchanged signatures so existing callers keep working
# ------------------------------------------------------------------


def get_default_personas(llm: LLMClient) -> List[Persona]:
    """Return a list of :class:`Persona` objects wired to *llm*.

    :param llm: LLM client backend to attach to each persona.
    :returns:   List of fully-constructed persona instances.
    """
    return [
        Persona(
            id=pid,
            name=data["name"],
            system_prompt=data["system_prompt"],
            llm=llm,
            temperature=data.get("default_temperature", 5),
        )
        for pid, data in _get_registry().items()
    ]


def get_personas_with_llm_map(
    default_llm: LLMClient,
    llm_map: Optional[Dict[str, LLMClient]] = None,
) -> List[Persona]:
    """Create personas allowing per-persona LLM overrides.

    :param default_llm: Fallback LLM for personas not in *llm_map*.
    :param llm_map:     ``{persona_id: LLMClient}`` overrides.
    :returns:           List of fully-constructed persona instances.
    """
    if not llm_map:
        return get_default_personas(default_llm)
    return [
        Persona(
            id=pid,
            name=data["name"],
            system_prompt=data["system_prompt"],
            llm=llm_map.get(pid, default_llm),
            temperature=data.get("default_temperature", 5),
        )
        for pid, data in _get_registry().items()
    ]


def get_default_persona_prompt(persona_id: str) -> Optional[str]:
    """Return the system prompt for *persona_id*, or ``None`` if unknown.

    :param persona_id: Persona identifier.
    :returns:          System prompt string, or ``None``.
    """
    data = _get_registry().get(persona_id)
    return data["system_prompt"] if data else None


def is_valid_persona_id(pid: str) -> bool:
    """Check whether *pid* is a recognised persona identifier.

    :param pid: Persona identifier to look up.
    :returns:   ``True`` if the persona exists.
    """
    return pid in _get_registry()


def list_available_personas() -> List[str]:
    """Return all registered persona IDs.

    :returns: List of persona identifier strings.
    """
    return list(_get_registry().keys())


def get_agent_ids() -> Set[str]:
    """Return the set of persona IDs whose type is ``'agent'`` (not ``'advisor'``).

    :returns: Set of agent persona IDs.
    """
    return {pid for pid, data in _get_registry().items()
            if data.get("type") == "agent"}
