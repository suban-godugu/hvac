"""O20 control software / BMS health from controller records only."""
from __future__ import annotations

from typing import Any, Dict

from backend.agents.official_opportunities._common import agent_envelope, text


def evaluate_control_software(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    row = snapshot.get("controller") or {}
    if not row:
        return agent_envelope(
            "O20",
            False,
            recommendation=None,
            reason="No controller software status records.",
        )
    comm = (text(row, "comm_status") or "").upper()
    health = (text(row, "health_status") or "").upper()
    quality = (text(row, "point_quality") or "").upper()
    overrides = text(row, "override_state")
    alarms = text(row, "alarm_state")
    rec = "MAINTAIN"
    reason = "Controller communication and software health are within expected range."
    if comm not in ("ONLINE", "CONNECTED", "OK"):
        rec = "RESTORE_COMMUNICATION"
        reason = f"Controller communication is {comm or 'UNKNOWN'}."
    elif quality in ("BAD", "STALE", "UNCERTAIN"):
        rec = "INVESTIGATE_POINT_QUALITY"
        reason = f"Point quality is {quality}."
    elif overrides and overrides.upper() not in ("NONE", "OFF", "NORMAL"):
        rec = "REVIEW_OVERRIDES"
        reason = f"Manual override present: {overrides}."
    return agent_envelope(
        "O20",
        True,
        current_state={
            "bms_status": comm or None,
            "controller_id": row.get("controller_id"),
            "software_version": row.get("software_version"),
            "firmware_version": row.get("firmware_version"),
            "control_loop_state": row.get("control_loop_state"),
            "point_quality": quality or None,
            "communication_health": comm or None,
            "override_status": overrides,
            "alarm_status": alarms,
            "last_update": row.get("last_communication") or row.get("updated_at"),
            "software_health": health or None,
        },
        optimized_state={"target_health": "HEALTHY"},
        recommendation=rec,
        reason=reason,
        confidence=0.8 if comm in ("ONLINE", "CONNECTED") else 0.45,
        extra={"current_value": None, "optimized_value": None},
    )
