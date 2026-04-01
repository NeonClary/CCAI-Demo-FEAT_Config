"""
Timer query engine for natural-language countdown requests.

This module parses requests such as:
- "Set me a timer for 5 minutes"
- "Tell me when it's been 10 minutes"
- "How much time is left?"
- "Cancel my timer"
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional


def _parse_duration_seconds(text: str) -> Optional[int]:
    lower = (text or "").lower()
    m = re.search(
        r"(\d+)\s*(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h)\b",
        lower,
    )
    if not m:
        return None
    amount = int(m.group(1))
    unit = m.group(2)
    if amount <= 0:
        return None
    if unit.startswith(("hour", "hr")) or unit == "h":
        return amount * 3600
    if unit.startswith(("minute", "min")) or unit == "m":
        return amount * 60
    return amount


def _format_human_duration(total_seconds: int) -> str:
    total_seconds = max(0, int(total_seconds))
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    parts = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds or not parts:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    return ", ".join(parts)


def classify_timer_intent(text: str) -> str:
    lower = (text or "").lower().strip()
    if any(k in lower for k in ["cancel timer", "stop timer", "clear timer"]):
        return "cancel"
    if any(
        k in lower
        for k in [
            "time left",
            "time is left",
            "how much longer",
            "has it been",
            "is my timer done",
            "timer status",
            "remaining",
        ]
    ):
        return "status"
    if any(k in lower for k in ["timer", "countdown", "remind me", "tell me when"]):
        return "set"
    return "unknown"


def build_timer_result(
    query: str,
    existing_timer: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    now = datetime.utcnow()
    intent = classify_timer_intent(query)

    if intent == "cancel":
        if existing_timer:
            return {
                "status": "ok",
                "action": "cancelled",
                "message": "Timer cancelled.",
                "timer": None,
            }
        return {
            "status": "ok",
            "action": "none",
            "message": "There is no active timer to cancel.",
            "timer": None,
        }

    if intent == "status":
        if not existing_timer:
            return {
                "status": "ok",
                "action": "none",
                "message": "You do not have an active timer. Ask me to set one, for example: 'Set a timer for 10 minutes.'",
                "timer": None,
            }
        due_at = datetime.fromisoformat(existing_timer["due_at"])
        remaining_seconds = int((due_at - now).total_seconds())
        if remaining_seconds <= 0:
            return {
                "status": "ok",
                "action": "expired",
                "message": "Your timer has finished.",
                "timer": existing_timer,
                "remaining_seconds": 0,
            }
        return {
            "status": "ok",
            "action": "status",
            "message": f"Your timer is running. Time remaining: {_format_human_duration(remaining_seconds)}.",
            "timer": existing_timer,
            "remaining_seconds": remaining_seconds,
        }

    if intent == "set":
        duration_seconds = _parse_duration_seconds(query)
        if duration_seconds is None:
            return {
                "status": "need_duration",
                "action": "none",
                "message": "Please include a duration, for example: 'Set a timer for 5 minutes.'",
                "timer": None,
            }
        due_at = now + timedelta(seconds=duration_seconds)
        timer_id = str(uuid.uuid4())
        timer = {
            "timer_id": timer_id,
            "created_at": now.isoformat(),
            "due_at": due_at.isoformat(),
            "duration_seconds": duration_seconds,
            "source_query": query,
        }
        return {
            "status": "ok",
            "action": "set",
            "message": (
                f"Timer set for {_format_human_duration(duration_seconds)}. "
                f"It will finish at {due_at.strftime('%H:%M:%S UTC')}."
            ),
            "timer": timer,
        }

    return {
        "status": "not_timer",
        "action": "none",
        "message": "This doesn't look like a timer request.",
        "timer": None,
    }
