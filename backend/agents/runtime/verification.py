from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from backend.agents.scheduling_supervisory.gateway import get_bms_gateway
from backend.agents.runtime.command import get_command, set_status
from backend.services.logging_service import log_event


def verify_command(command_id: str, expected: Optional[float] = None, tolerance: float = 0.5) -> Tuple[bool, str]:
    cmd = get_command(command_id)
    if not cmd:
        return False, "NOT_FOUND"
    set_status(command_id, "VERIFYING")
    gw = get_bms_gateway()
    point_id = cmd.get("point_id")
    target = expected if expected is not None else cmd.get("new_value")
    if not point_id or target is None:
        set_status(command_id, "VERIFICATION_FAILED")
        return False, "MISSING_VALUES"
    try:
        pt = gw.read_point(point_id)
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
    old = cmd.get("old_value")
    point_id = cmd.get("point_id")
    set_status(command_id, "ROLLBACK")
    if old is None or not point_id:
        set_status(command_id, "ROLLED_BACK")
        return True, "NO_PREVIOUS_VALUE"
    gw = get_bms_gateway()
    result = gw.write_point(point_id, float(old))
    set_status(command_id, "ROLLED_BACK")
    log_event("INFO", "control-worker", "COMMAND_ROLLED_BACK", command_id=command_id)
    return bool(getattr(result, "success", True)), "ROLLED_BACK"
