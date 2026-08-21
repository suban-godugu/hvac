from __future__ import annotations

from typing import Any, Dict, Tuple

from backend.bms.command_writer import write_point
from backend.agents.runtime.command import set_status
from backend.services.hvac_safety_contract import evaluate_dispatch
from backend.services.logging_service import log_event
from backend.workers.watchdog import allow_autonomous_writes


def apply_setpoint(command_id: str, point_id: str, value: float, context: Dict[str, Any]) -> Tuple[bool, str]:
    ctx = dict(context or {})
    ctx["action"] = "APPLY"
    ok, reason, classified = evaluate_dispatch(ctx)
    if not ok:
        set_status(command_id, "BLOCKED")
        log_event("WARN", "control-worker", "COMMAND_BLOCKED", command_id=command_id, extra={"code": classified.get("code"), "reason": reason})
        return False, reason
    if not allow_autonomous_writes() and (ctx.get("mode") or "").upper() == "AUTO":
        set_status(command_id, "BLOCKED")
        return False, "Worker watchdog is in SAFE HOLD."
    set_status(command_id, "APPLYING")
    outcome = write_point(point_id, value)
    if outcome.success:
        set_status(command_id, "APPLIED")
        log_event("INFO", "control-worker", "COMMAND_APPLIED", command_id=command_id, opportunity=ctx.get("opportunity_id"))
        return True, "APPLIED"
    set_status(command_id, "BLOCKED")
    log_event("WARN", "control-worker", outcome.code or "WRITE_FAILED", command_id=command_id)
    return False, outcome.message or outcome.code
