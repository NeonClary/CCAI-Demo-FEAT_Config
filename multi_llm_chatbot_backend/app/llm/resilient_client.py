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
        # #region agent log
        from app.core._debug_log import dlog
        preview = (result if isinstance(result, str) else getattr(result, "text", ""))[:200]
        dlog("resilient_client.py:_run_primary", "primary returned", {
            "label": self.primary_label,
            "result_type": type(result).__name__,
            "preview": preview,
        }, "E")
        # #endregion
        if isinstance(result, str) and _looks_like_failed_response(result):
            raise RuntimeError(f"{self.primary_label} returned failure text")
        if isinstance(result, ToolCallResult) and _looks_like_failed_response(result.text):
            raise RuntimeError(f"{self.primary_label} tool call returned failure text")
        return result

    async def _run_fallback(self, coro_factory):
        logger.info("Using fallback LLM for %s", self.primary_label)
        # #region agent log
        from app.core._debug_log import dlog
        dlog("resilient_client.py:_run_fallback.start", "invoking fallback", {
            "label": self.primary_label,
        }, "B")
        # #endregion
        try:
            result = await coro_factory(self.fallback)
            # #region agent log
            preview = (result if isinstance(result, str) else getattr(result, "text", ""))[:200]
            dlog("resilient_client.py:_run_fallback.ok", "fallback returned", {
                "label": self.primary_label,
                "preview": preview,
            }, "B")
            # #endregion
            return result
        except Exception as fe:
            # #region agent log
            dlog("resilient_client.py:_run_fallback.error", "fallback raised", {
                "label": self.primary_label,
                "exc_type": type(fe).__name__,
                "exc_msg": str(fe)[:500],
            }, "B")
            # #endregion
            raise

    async def _race_or_fallback(self, coro_factory):
        """Spec:
        - Start *primary* immediately.
        - If primary returns successfully → use it.
        - If primary fails (raises, returns recognised failure text) → run
          *fallback* sequentially and return its result.
        - If primary takes longer than ``race_timeout_seconds`` without
          completing → start *fallback* in parallel and return whichever
          finishes first (primary or fallback).
        """
        # #region agent log
        from app.core._debug_log import dlog
        dlog("resilient_client.py:_race_or_fallback.enter", "starting primary", {
            "label": self.primary_label,
            "timeout_s": self.race_timeout_seconds,
        }, "B")
        # #endregion

        primary_task = asyncio.create_task(self._run_primary(coro_factory))

        try:
            result = await asyncio.wait_for(
                asyncio.shield(primary_task),
                timeout=self.race_timeout_seconds,
            )
            # #region agent log
            preview = (result if isinstance(result, str) else getattr(result, "text", ""))[:200]
            dlog("resilient_client.py:_race_or_fallback.primary_ok", "primary succeeded", {
                "label": self.primary_label,
                "preview": preview,
            }, "B")
            # #endregion
            return result
        except asyncio.TimeoutError:
            logger.info(
                "%s slower than %.1fs — racing fallback in parallel",
                self.primary_label,
                self.race_timeout_seconds,
            )
            # #region agent log
            dlog("resilient_client.py:_race_or_fallback.timeout_race", "racing fallback in parallel", {
                "label": self.primary_label,
                "timeout_s": self.race_timeout_seconds,
            }, "B")
            # #endregion
            return await self._race_first_successful(primary_task, coro_factory)
        except Exception as exc:
            logger.warning("%s failed: %s — using fallback sequentially", self.primary_label, exc)
            # #region agent log
            dlog("resilient_client.py:_race_or_fallback.primary_fail", "primary raised", {
                "label": self.primary_label,
                "exc_type": type(exc).__name__,
                "exc_msg": str(exc)[:500],
            }, "B")
            # #endregion
            if not primary_task.done():
                primary_task.cancel()

        try:
            return await self._run_fallback(coro_factory)
        except Exception as fb_exc:
            logger.error(
                "Both primary (%s) and fallback failed for this request: %s",
                self.primary_label, fb_exc,
            )
            raise

    async def _race_first_successful(self, primary_task: asyncio.Task, coro_factory):
        """Primary is still running past the soft timeout. Start fallback in
        parallel and return whichever completes successfully first. If the
        first one to complete failed, await the other; if both fail, raise.
        """
        # #region agent log
        from app.core._debug_log import dlog
        # #endregion
        fallback_task = asyncio.create_task(self._run_fallback(coro_factory))
        pending = {primary_task, fallback_task}

        winner_text: str | None = None
        winner_obj: Any = None
        last_exc: Exception | None = None

        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                which = "primary" if task is primary_task else "fallback"
                try:
                    result = task.result()
                except Exception as exc:
                    last_exc = exc
                    # #region agent log
                    dlog("resilient_client.py:_race_first_successful.loser", "task failed", {
                        "which": which,
                        "exc_type": type(exc).__name__,
                        "exc_msg": str(exc)[:300],
                    }, "B")
                    # #endregion
                    continue
                # #region agent log
                preview = (result if isinstance(result, str) else getattr(result, "text", ""))[:200]
                dlog("resilient_client.py:_race_first_successful.winner", "task succeeded", {
                    "which": which,
                    "preview": preview,
                }, "B")
                # #endregion
                winner_obj = result
                winner_text = preview
                break
            if winner_obj is not None:
                break

        for t in pending:
            if not t.done():
                t.cancel()

        if winner_obj is not None:
            return winner_obj
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("race produced no result and no exception")

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
