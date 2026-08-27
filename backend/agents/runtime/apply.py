from __future__ import annotations

from typing import Any, Dict, Tuple

from backend.agents.runtime.command import set_status
from backend.services.logging_service import log_event
from backend.workers.watchdog import allow_autonomous_writes


def apply_setpoint(command_id: str, point_id: str, value: float, context: Dict[str, Any]) -> Tuple[bool, str]:
    ctx = dict(context or {})
    ctx["action"] = "APPLY"
    ctx["point_id"] = point_id
    ctx["new_value"] = value
    ctx["target_value"] = value
    if ctx.get("old_value") is None:
        ctx["old_value"] = ctx.get("current_value")
    if ctx.get("decision") is None:
        ctx["decision"] = "OPTIMIZE"
    if ctx.get("safety") is None:
        ctx["safety"] = {"status": "PASS", "passed": True}
    if ctx.get("confidence") is None:
        ctx["confidence"] = 0.9

    from backend.rules.engine import evaluate as rule_engine_evaluate

    verdict = rule_engine_evaluate(ctx)
    if verdict.get("verdict") != "APPROVED":
        set_status(command_id, "BLOCKED")
        code = verdict.get("code")
        reason = verdict.get("reason") or "Rule Engine REJECTED"
        log_event(
            "WARN",
            "control-worker",
            "COMMAND_BLOCKED",
            command_id=command_id,
            extra={"code": code, "reason": reason},
        )
        return False, str(reason)
    if not allow_autonomous_writes() and (ctx.get("mode") or "").upper() == "AUTO":
        set_status(command_id, "BLOCKED")
        return False, "Worker watchdog is in SAFE HOLD."
    set_status(command_id, "APPLYING")
    write_ctx = dict(ctx)
    write_ctx["action"] = "WRITE"
    write_ctx.setdefault("approval_status", "APPROVED")
    from backend.bms.command_writer import write_point

    outcome = write_point(point_id, value, context=write_ctx)
    if outcome is not None and outcome.success:
        set_status(command_id, "APPLIED")
        log_event("INFO", "control-worker", "COMMAND_APPLIED", command_id=command_id, opportunity=ctx.get("opportunity_id"))
        return True, "APPLIED"
    set_status(command_id, "BLOCKED")
    code = (outcome.code if outcome is not None else None) or "WRITE_FAILED"
    message = (outcome.message if outcome is not None else None) or code
    log_event("WARN", "control-worker", code, command_id=command_id)
    return False, message
