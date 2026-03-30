"""
Contractor scheduling engine.

Reads contractor availability from ``data/contractor_schedules.json`` and
exposes functions to find available contractors for a given service + date
and to plan multi-day task sequences.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

LOG = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _load_data() -> Dict[str, Any]:
    path = _DATA_DIR / "contractor_schedules.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _is_available(contractor: Dict, date_str: str) -> Tuple[bool, Optional[str]]:
    """Check whether *contractor* has a full-day available slot on *date_str*.

    :returns: ``(available, reason_if_not)``
    """
    blocks = contractor.get("schedule", {}).get(date_str)
    if blocks is None:
        return False, "No schedule data for this date"
    for block in blocks:
        if block["status"] == "unavailable":
            return False, block.get("reason", "Unavailable")
    return True, None


def _flex_note(contractor: Dict, date_str: str) -> Optional[str]:
    """Return a flex-availability note if the contractor could work via incentive."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None
    flex = contractor.get("flex_availability", {})
    weekday = dt.weekday()
    if weekday == 6:  # Sunday
        info = flex.get("weekends", {})
        if info.get("available"):
            return info.get("note", "Available on weekends for extra rate")
    if weekday == 5:  # Saturday
        info = flex.get("weekends", {})
        if info.get("available"):
            return info.get("note", "Available on Saturdays for extra rate")
    ah = flex.get("after_hours", {})
    if ah.get("available"):
        return ah.get("note")
    return None


def find_available_contractors(
    service_id: str,
    date_str: str,
) -> Dict[str, Any]:
    """Find contractors available for *service_id* on *date_str*.

    Returns a structured dict with ``top_choice``, ``other_options``, and
    ``flex_options`` (contractors available with incentives).
    """
    data = _load_data()
    contractors = data.get("contractors", [])
    services = data.get("services", {})
    svc = services.get(service_id)
    svc_label = svc["label"] if svc else service_id

    capable = [c for c in contractors if service_id in c.get("services", [])]
    if not capable:
        return {
            "service": service_id,
            "service_label": svc_label,
            "date": date_str,
            "top_choice": None,
            "other_options": [],
            "flex_options": [],
            "message": f"No contractors in the system provide {svc_label}.",
        }

    available: List[Dict[str, Any]] = []
    flex: List[Dict[str, Any]] = []
    unavailable_reasons: List[Dict[str, Any]] = []

    for c in capable:
        ok, reason = _is_available(c, date_str)
        if ok:
            available.append({
                "id": c["id"],
                "name": c["name"],
                "preferred": c.get("preferred", False),
                "hours": f"{c['standard_hours']['start']}–{c['standard_hours']['end']}",
            })
        else:
            note = _flex_note(c, date_str)
            if note:
                flex.append({
                    "id": c["id"],
                    "name": c["name"],
                    "preferred": c.get("preferred", False),
                    "flex_note": note,
                    "unavailable_reason": reason,
                })
            else:
                unavailable_reasons.append({
                    "id": c["id"],
                    "name": c["name"],
                    "reason": reason,
                })

    available.sort(key=lambda x: (not x["preferred"], x["name"]))

    top = available[0] if available else None
    others = available[1:] if len(available) > 1 else []

    return {
        "service": service_id,
        "service_label": svc_label,
        "date": date_str,
        "top_choice": top,
        "other_options": others,
        "flex_options": flex,
        "unavailable": unavailable_reasons,
    }


def schedule_multi_day(
    tasks: List[str],
    start_date: str,
    prefer_same_contractor: bool = True,
) -> Dict[str, Any]:
    """Schedule a sequence of tasks across consecutive days starting from *start_date*.

    :param tasks: Ordered list of service IDs.
    :param start_date: ISO date for the first task.
    :param prefer_same_contractor: Try to use the same contractor across days.
    :returns: A structured plan dict.
    """
    data = _load_data()
    contractors = data.get("contractors", [])
    services = data.get("services", {})

    dt = datetime.strptime(start_date, "%Y-%m-%d")
    dates = [(dt + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(len(tasks))]

    plan: List[Dict[str, Any]] = []
    chosen_id: Optional[str] = None

    for task, tdate in zip(tasks, dates):
        result = find_available_contractors(task, tdate)

        pick = None
        if prefer_same_contractor and chosen_id:
            all_opts = [result["top_choice"]] + result.get("other_options", []) if result["top_choice"] else result.get("other_options", [])
            for opt in all_opts:
                if opt and opt["id"] == chosen_id:
                    pick = opt
                    break

        if not pick and result["top_choice"]:
            pick = result["top_choice"]

        if pick and not chosen_id:
            chosen_id = pick["id"]

        plan.append({
            "date": tdate,
            "task": task,
            "task_label": services.get(task, {}).get("label", task),
            "assigned": pick,
            "alternatives": result.get("other_options", []),
            "flex_options": result.get("flex_options", []),
        })

    return {
        "tasks": [services.get(t, {}).get("label", t) for t in tasks],
        "dates": dates,
        "plan": plan,
        "preferred_contractor": chosen_id,
    }


def format_single_schedule(result: Dict[str, Any]) -> str:
    """Render a single-task scheduling result as readable markdown."""
    lines = [f"### Contractor Scheduling: {result['service_label']} on {result['date']}", ""]
    top = result.get("top_choice")
    if top:
        pref = " *(preferred contractor)*" if top.get("preferred") else ""
        lines.append(f"**Top Choice:** {top['name']}{pref}")
        lines.append(f"- Available hours: {top['hours']}")
        lines.append("")
    else:
        lines.append("**No contractors available** for this service on this date during standard hours.")
        lines.append("")

    others = result.get("other_options", [])
    if others:
        lines.append("**Other Available Options:**")
        for o in others:
            pref = " *(preferred)*" if o.get("preferred") else ""
            lines.append(f"- {o['name']}{pref} — {o['hours']}")
        lines.append("")

    flex = result.get("flex_options", [])
    if flex:
        lines.append("**Available with Incentives:**")
        for f in flex:
            lines.append(f"- {f['name']} — {f['flex_note']} (currently: {f['unavailable_reason']})")
        lines.append("")

    unavail = result.get("unavailable", [])
    if unavail:
        lines.append("**Unavailable:**")
        for u in unavail:
            lines.append(f"- {u['name']} — {u['reason']}")

    msg = result.get("message")
    if msg:
        lines.append(f"\n*{msg}*")

    return "\n".join(lines)


def format_multi_day_plan(plan: Dict[str, Any]) -> str:
    """Render a multi-day scheduling plan as readable markdown."""
    lines = [f"### Multi-Day Schedule Plan", ""]
    pref = plan.get("preferred_contractor")
    if pref:
        lines.append(f"*Preferred contractor across days: **{pref}***")
        lines.append("")

    for entry in plan.get("plan", []):
        assigned = entry.get("assigned")
        if assigned:
            pref_tag = " *(preferred)*" if assigned.get("preferred") else ""
            lines.append(f"**{entry['date']}** — {entry['task_label']}")
            lines.append(f"- Assigned: {assigned['name']}{pref_tag} ({assigned['hours']})")
        else:
            lines.append(f"**{entry['date']}** — {entry['task_label']}")
            lines.append("- **No contractor available** during standard hours")

        alts = entry.get("alternatives", [])
        if alts:
            alt_names = ", ".join(a["name"] for a in alts)
            lines.append(f"- Alternatives: {alt_names}")

        flex = entry.get("flex_options", [])
        if flex:
            for f in flex:
                lines.append(f"- With incentive: {f['name']} — {f['flex_note']}")
        lines.append("")

    return "\n".join(lines)


def normalize_service_name(raw: str) -> Optional[str]:
    """Best-effort mapping from natural-language task name to a service ID."""
    data = _load_data()
    services = data.get("services", {})
    lower = raw.lower().strip()

    for sid, svc in services.items():
        if sid == lower or lower == svc.get("label", "").lower():
            return sid

    keyword_map = {
        "cement": "cement_pouring", "concrete": "cement_pouring", "pour": "cement_pouring",
        "roof": "roofing", "shingle": "roofing",
        "window": "window_installation", "glass": "window_installation",
        "asphalt": "asphalt_paving", "paving": "asphalt_paving", "pave": "asphalt_paving",
        "excavat": "excavation", "grad": "excavation", "dig": "excavation", "trench": "excavation",
        "electric": "electrical_work", "wiring": "electrical_work",
        "plumb": "plumbing", "pipe": "plumbing",
        "fram": "framing", "carpent": "framing", "lumber": "framing",
        "paint": "painting_exterior", "coat": "painting_exterior",
        "inspect": "site_inspection", "survey": "site_inspection",
    }
    for kw, sid in keyword_map.items():
        if kw in lower:
            return sid
    return None
