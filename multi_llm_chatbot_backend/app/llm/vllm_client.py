# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All Rights Reserved 2008-2025
# Licensed under the BSD 3-Clause License
# https://opensource.org/licenses/BSD-3-Clause
#
# Copyright (c) 2008-2025, Neongecko.com Inc.
"""
OpenAI-compatible vLLM client for self-hosted inference servers.

Each configured vLLM endpoint exposes ``/v1/chat/completions`` and
``/v1/models``, matching the OpenAI wire format.  This client wraps
those two operations and implements :class:`LLMClient` so it can be
used as a drop-in replacement for Gemini or Ollama.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from app.llm.llm_client import LLMClient

LOG = logging.getLogger(__name__)

_http_clients: Dict[str, httpx.AsyncClient] = {}


def _get_http_client(base_url: str) -> httpx.AsyncClient:
    """Return (or create) a shared :class:`httpx.AsyncClient` per base URL."""
    if base_url not in _http_clients or _http_clients[base_url].is_closed:
        _http_clients[base_url] = httpx.AsyncClient(
            timeout=120.0,
            base_url=base_url,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
    return _http_clients[base_url]


async def close_all_vllm_clients() -> None:
    """Cleanly shut down every cached HTTP client."""
    for url, client in list(_http_clients.items()):
        if not client.is_closed:
            await client.aclose()
    _http_clients.clear()


# ------------------------------------------------------------------
# Model discovery
# ------------------------------------------------------------------

async def discover_models_for_client(
    api_url: str,
    api_key: str,
    client_id: str,
    client_name: str,
) -> List[Dict[str, Any]]:
    """Query a single vLLM endpoint's ``/v1/models`` and return metadata.

    :returns: List of dicts with ``model_id``, ``client_id``,
        ``client_name``, and ``api_url`` keys.
    """
    client = _get_http_client(api_url)
    headers: Dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        resp = await client.get("/v1/models", headers=headers)
        resp.raise_for_status()
        data = resp.json()
        models = data.get("data", [])
        return [
            {
                "model_id": m["id"],
                "client_id": client_id,
                "client_name": client_name,
                "api_url": api_url,
            }
            for m in models
        ]
    except Exception as exc:
        LOG.warning("Model discovery failed for %s (%s): %s", client_name, api_url, exc)
        return []


async def discover_all_models(
    clients: List[Dict[str, str]],
    api_key: str,
) -> List[Dict[str, Any]]:
    """Query every configured vLLM endpoint in parallel and return a
    combined, deduplicated list of available models.

    *clients* is a list of dicts with ``id``, ``name``, and ``api_url``.
    """
    tasks = [
        discover_models_for_client(
            api_url=c["api_url"],
            api_key=api_key,
            client_id=c["id"],
            client_name=c["name"],
        )
        for c in clients
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    combined: List[Dict[str, Any]] = []
    for result in results:
        if isinstance(result, list):
            combined.extend(result)
    return combined


# ------------------------------------------------------------------
# LLM Client
# ------------------------------------------------------------------

class VLLMClient(LLMClient):
    """OpenAI-compatible chat-completions client for a vLLM endpoint."""

    def __init__(
        self,
        api_url: str,
        api_key: str = "",
        model_name: str = "",
        client_id: str = "",
    ) -> None:
        self.api_url = api_url
        self.api_key = api_key
        self.model_name = model_name
        self.client_id = client_id

    async def generate(
        self,
        system_prompt: str,
        context: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
        ]
        for msg in context:
            role = msg.get("role", "user")
            if role not in ("user", "assistant", "system"):
                role = "user"
            messages.append({"role": role, "content": msg.get("content", "")})

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        client = _get_http_client(self.api_url)
        try:
            resp = await client.post("/v1/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                LOG.warning("vLLM returned empty choices for model %s", self.model_name)
                return "The model did not return a response. Please try again."
            text = choices[0].get("message", {}).get("content", "").strip()
            return self._clean_response(text)

        except httpx.ConnectError:
            LOG.error("Cannot connect to vLLM at %s", self.api_url)
            return "Unable to reach the AI inference server. Please verify it is online."
        except httpx.TimeoutException:
            LOG.error("vLLM request timeout (%s)", self.api_url)
            return "The AI server is taking too long to respond. Please try again."
        except httpx.HTTPStatusError as exc:
            LOG.error("vLLM HTTP %s from %s: %s", exc.response.status_code, self.api_url, exc.response.text[:300])
            return "The AI server returned an error. Please try again."
        except Exception as exc:
            LOG.exception("Unexpected vLLM error: %s", exc)
            return "An unexpected error occurred. Please try again."

    @staticmethod
    def _clean_response(text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [ln.rstrip() for ln in text.split("\n")]
        return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
