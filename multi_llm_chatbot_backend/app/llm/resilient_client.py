"""Primary/fallback LLM wrapper with failure failover and optional race-to-first."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

from app.llm.llm_client import LLMClient, ToolCallResult

logger = logging.getLogger(__name__)

_VLLM_ERROR_MARKERS = (
    "unable to connect",
    "encountered an error",
    "unexpected error",
)


def _looks_like_failed_response(text: str) -> bool:
    if not text or not text.strip():
        return True
    lower = text.strip().lower()
    return any(marker in lower for marker in _VLLM_ERROR_MARKERS)


class ResilientLLMClient(LLMClient):
    """Try *primary* first; on failure or slow response, use *fallback*."""

    def __init__(
        self,
        primary: LLMClient,
        fallback: LLMClient,
        race_timeout_seconds: float = 3.0,
        primary_label: str = "primary",
    ):
        self.primary = primary
        self.fallback = fallback
        self.race_timeout_seconds = race_timeout_seconds
        self.primary_label = primary_label

    async def _run_primary(self, coro_factory):
        result = await coro_factory(self.primary)
        if isinstance(result, str) and _looks_like_failed_response(result):
            raise RuntimeError(f"{self.primary_label} returned failure text")
        if isinstance(result, ToolCallResult) and _looks_like_failed_response(result.text):
            raise RuntimeError(f"{self.primary_label} tool call returned failure text")
        return result

    async def _run_fallback(self, coro_factory):
        logger.info("Using fallback LLM for %s", self.primary_label)
        return await coro_factory(self.fallback)

    async def _race_or_fallback(self, coro_factory):
        primary_task = asyncio.create_task(self._run_primary(coro_factory))
        try:
            return await asyncio.wait_for(
                asyncio.shield(primary_task),
                timeout=self.race_timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.info(
                "%s exceeded %.1fs — racing fallback",
                self.primary_label,
                self.race_timeout_seconds,
            )
        except Exception as exc:
            logger.warning("%s failed: %s — using fallback", self.primary_label, exc)
            if not primary_task.done():
                primary_task.cancel()
            return await self._run_fallback(coro_factory)

        if primary_task.done():
            try:
                return primary_task.result()
            except Exception as exc:
                logger.warning("%s failed after wait: %s", self.primary_label, exc)
                return await self._run_fallback(coro_factory)

        fallback_task = asyncio.create_task(self._run_fallback(coro_factory))
        done, pending = await asyncio.wait(
            {primary_task, fallback_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        for task in done:
            if task.cancelled():
                continue
            try:
                return task.result()
            except Exception as exc:
                logger.warning("Race winner failed: %s", exc)
        return await self._run_fallback(coro_factory)

    async def generate(
        self,
        system_prompt: str,
        context: List[dict],
        temperature: float,
        max_tokens: int,
        response_mime_type: str = None,
    ) -> str:
        async def _call(client: LLMClient):
            return await client.generate(
                system_prompt, context, temperature, max_tokens, response_mime_type,
            )

        return await self._race_or_fallback(_call)

    async def generate_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tool_definitions: Optional[List[Dict[str, Any]]] = None,
        tool_executor: Optional[Callable] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> ToolCallResult:
        async def _call(client: LLMClient):
            return await client.generate_with_tools(
                system_prompt=system_prompt,
                user_message=user_message,
                tool_definitions=tool_definitions,
                tool_executor=tool_executor,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        return await self._race_or_fallback(_call)
