"""Debug-mode NDJSON logger. Writes to the agent debug log file."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_LOG_PATH = Path(r"C:\Users\dream\.cursor\projects\Ask-A-Neon-LLM-Demos\debug-1d5c0f.log")
_SESSION_ID = "1d5c0f"


def dlog(location: str, message: str, data: Any = None, hypothesis_id: str = "") -> None:
    try:
        entry = {
            "sessionId": _SESSION_ID,
            "timestamp": int(time.time() * 1000),
            "location": location,
            "message": message,
            "data": data or {},
        }
        if hypothesis_id:
            entry["hypothesisId"] = hypothesis_id
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, default=str) + "\n")
    except Exception:
        pass
