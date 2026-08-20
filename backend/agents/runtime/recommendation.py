from __future__ import annotations

from typing import Any, Dict, Optional

from backend.agents.runtime.approval import record_pending, required as approval_required
from backend.agents.runtime.apply import apply_setpoint
from backend.agents.runtime.audit import audit_command
from backend.agents.runtime.command import propose
from backend.agents.runtime.contracts import CommandContract
from backend.agents.runtime.coordinator import resolve
from backend.agents.runtime.safety import evaluate_safety
from backend.agents.runtime.state_builder import build_state


def recommend_and_maybe_apply(
    *,
    opportunity: str,
    building_id: Optional[str],
    point_id: Optional[str],
    old_value: Optional[float],
    new_value: Optional[float],
    reason: str,
    user: Optional[Dict[str, Any]],
    mode: str = "ADVISORY",
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ctx = dict(context or {})
    ctx.setdefault("telemetry", build_state(building_id, opportunity))
    ctx.setdefault("opportunity_id", opportunity)
    ctx.setdefault("user", user or {})
    ctx.setdefault("target_value", new_value)
    ctx.setdefault("current_value", old_value)
    ctx["point_id"] = point_id
    ctx["building_id"] = building_id

    contract = CommandContract(
        opportunity=opportunity,
        building=building_id,
        equipment=ctx.get("equipment_id"),
        point=point_id,
        old_value=old_value,
        new_value=new_value,
        reason=reason,
        requested_by=(user or {}).get("username"),
    )
    conflict = resolve(contract.as_dict())
    cmd = propose(contract, status="PROPOSED")
    ok, why, classified = evaluate_safety(ctx)
    if not ok:
        from backend.agents.runtime.command import set_status

        set_status(cmd["command_id"], "BLOCKED")
        audit_command(user, "DISPATCH_BLOCKED", cmd, why)
        return {"command": cmd, "allowed": False, "reason": why, "classified": classified, "conflict": conflict}

    if approval_required(mode):
        from backend.agents.runtime.command import set_status

        aid = record_pending(cmd["command_id"], opportunity, building_id, (user or {}).get("username"))
        set_status(cmd["command_id"], "PENDING_APPROVAL")
        cmd["approval_id"] = str(aid)
        audit_command(user, "PENDING_APPROVAL", cmd)
        return {"command": cmd, "allowed": False, "reason": "APPROVAL_REQUIRED", "classified": classified}

    if conflict.get("action") == "HOLD":
        return {"command": cmd, "allowed": False, "reason": "COORDINATOR_HOLD", "conflict": conflict, "classified": classified}

    applied, apply_reason = apply_setpoint(cmd["command_id"], point_id or "", float(new_value or 0), ctx)
    audit_command(user, "DISPATCH" if applied else "DISPATCH_BLOCKED", cmd, apply_reason)
    return {"command": cmd, "allowed": applied, "reason": apply_reason, "classified": classified}
