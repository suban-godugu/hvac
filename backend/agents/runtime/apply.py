from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from backend.bms.command_writer import write_point as reject_physical
from backend.agents.scheduling_supervisory.gateway import get_bms_gateway
from backend.agents.runtime.command import set_status
from backend.services.hvac_safety_contract import evaluate_dispatch
from backend.services.logging_service import log_event
from backend.workers.watchdog import allow_autonomous_writes


def apply_setpoint(command_id: str, point_id: str, value: float, context: Dict[str, Any]) -> Tuple[bool, str]:
    ok, reason, classified = evaluate_dispatch(context)
    if not ok:
        set_status(command_id, "BLOCKED")
        log_event("WARN", "control-worker", "COMMAND_BLOCKED", command_id=command_id, extra={"code": classified.get("code"), "reason": reason})
        return False, reason
    if not allow_autonomous_writes() and (context.get("mode") or "").upper() == "AUTO":
        set_status(command_id, "BLOCKED")
        return False, "Worker watchdog is in SAFE HOLD."
    blocked = reject_physical(point_id, value)
    if not blocked.success:
        set_status(command_id, "BLOCKED")
        log_event("WARN", "control-worker", "WRITE_DISABLED", command_id=command_id)
        return False, blocked.message
    gw = get_bms_gateway()
    if not getattr(gw, "is_production_connected", lambda: False)():
        set_status(command_id, "BLOCKED")
        return False, "Production BMS gateway is not connected."
    set_status(command_id, "APPLYING")
    result = gw.write_point(point_id, value)
    success = bool(getattr(result, "success", False))
    if success:
        set_status(command_id, "APPLIED")
        log_event("INFO", "control-worker", "COMMAND_APPLIED", command_id=command_id, opportunity=context.get("opportunity_id"))
        return True, "APPLIED"
    set_status(command_id, "BLOCKED")
    return False, "BMS write failed."
