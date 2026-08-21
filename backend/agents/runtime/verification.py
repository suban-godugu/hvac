from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from backend.bms.command_writer import write_point
from backend.bms.connection_manager import get_connection_manager
from backend.agents.runtime.command import get_command, set_status
from backend.services.hvac_safety_contract import evaluate_dispatch
from backend.services.logging_service import log_event


def _context_for(cmd: Dict[str, Any], action: str) -> Dict[str, Any]:
    from backend.services.platform_bms_service import platform_snapshot

    snap = platform_snapshot()
    tel = snap.get("telemetry") or {}
    payload = cmd.get("payload_json") if isinstance(cmd.get("payload_json"), dict) else {}
    return {
        "action": action,
        "opportunity_id": cmd.get("opportunity") or payload.get("opportunity"),
        "point_id": cmd.get("point_id"),
        "current_value": cmd.get("old_value"),
        "target_value": cmd.get("old_value") if action == "ROLLBACK" else cmd.get("new_value"),
        "source": tel.get("source"),
        "telemetry": {
            "source": tel.get("source"),
            "quality": tel.get("quality"),
            "age_seconds": tel.get("ageSeconds"),
            "raw": tel.get("status"),
        },
        "supervisory": {"decision": "OPTIMIZE", "confidence": 0.99},
        "safety": {"status": snap.get("safety"), "passed": snap.get("safety") == "PASS"},
    }


def verify_command(command_id: str, expected: Optional[float] = None, tolerance: float = 0.5) -> Tuple[bool, str]:
    cmd = get_command(command_id)
    if not cmd:
        return False, "NOT_FOUND"
    ok, reason, classified = evaluate_dispatch(_context_for(cmd, "VERIFY"))
    if not ok:
        set_status(command_id, "VERIFICATION_FAILED")
        return False, classified.get("code") or reason
    set_status(command_id, "VERIFYING")
    mgr = get_connection_manager()
    adapter = mgr.adapter()
    point_id = cmd.get("point_id")
    target = expected if expected is not None else cmd.get("new_value")
    if adapter is None or not mgr.is_production_connected() or not point_id or target is None:
        set_status(command_id, "VERIFICATION_FAILED")
        return False, "MISSING_VALUES"
    try:
        pt = adapter.read_point(point_id)
        val = getattr(pt, "value", None)
        if val is None:
            set_status(command_id, "VERIFICATION_FAILED")
            return False, "NO_FEEDBACK"
        if abs(float(val) - float(target)) <= tolerance:
            set_status(command_id, "VERIFIED")
            log_event("INFO", "control-worker", "COMMAND_VERIFIED", command_id=command_id)
            return True, "VERIFIED"
    except Exception as exc:
        set_status(command_id, "VERIFICATION_FAILED")
        return False, str(type(exc).__name__)
    set_status(command_id, "VERIFICATION_FAILED")
    return False, "OUT_OF_TOLERANCE"


def rollback_command(command_id: str) -> Tuple[bool, str]:
    cmd = get_command(command_id)
    if not cmd:
        return False, "NOT_FOUND"
    ok, reason, classified = evaluate_dispatch(_context_for(cmd, "ROLLBACK"))
    if not ok:
        set_status(command_id, "BLOCKED")
        return False, classified.get("code") or reason
    old = cmd.get("old_value")
    point_id = cmd.get("point_id")
    set_status(command_id, "ROLLBACK")
    if old is None or not point_id:
        set_status(command_id, "ROLLED_BACK")
        return True, "NO_PREVIOUS_VALUE"
    outcome = write_point(str(point_id), float(old))
    if not outcome.success:
        set_status(command_id, "BLOCKED")
        return False, outcome.code
    set_status(command_id, "ROLLED_BACK")
    log_event("INFO", "control-worker", "COMMAND_ROLLED_BACK", command_id=command_id)
    return True, "ROLLED_BACK"
