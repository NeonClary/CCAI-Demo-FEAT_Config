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

from typing import List, Optional

from app.config import get_settings
from app.models.persona import Persona


def _build_personas_dict() -> dict:
    """Build the ``{id: {name, system_prompt, temperature}}`` registry from
    the YAML configuration."""
    cfg = get_settings()
    base_prompt = cfg.personas.base_prompt.strip()
    registry: dict = {}
    for p in cfg.personas.items:
        # Combine the persona-specific prompt with the shared base prompt
        full_prompt = p.persona_prompt.strip()
        if base_prompt:
            full_prompt = f"{full_prompt}\n\n{base_prompt}"
        registry[p.id] = {
            "name": p.name,
            "system_prompt": full_prompt,
            "default_temperature": p.temperature,
        }
    return registry


# Lazy singleton — built once on first access
_DEFAULT_PERSONAS: Optional[dict] = None


def _get_registry() -> dict:
    global _DEFAULT_PERSONAS
    if _DEFAULT_PERSONAS is None:
        _DEFAULT_PERSONAS = _build_personas_dict()
    return _DEFAULT_PERSONAS


# ------------------------------------------------------------------
# Public API — unchanged signatures so existing callers keep working
# ------------------------------------------------------------------

def get_default_personas(llm) -> List[Persona]:
    """Return a list of :class:`Persona` objects wired to *llm*."""
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


def get_default_persona_prompt(persona_id: str) -> Optional[str]:
    data = _get_registry().get(persona_id)
    return data["system_prompt"] if data else None


def is_valid_persona_id(pid: str) -> bool:
    return pid in _get_registry()


def list_available_personas() -> List[str]:
    return list(_get_registry().keys())
