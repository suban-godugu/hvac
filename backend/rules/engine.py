"""Unified Rule Engine evaluate() — Stage F policy gate."""
from __future__ import annotations

from typing import Any, Dict, Optional

from backend.rules.audit import audit_rule_engine
from backend.rules.checks import CHECKLIST, check_dispatch_contract
from backend.rules.context import build_rule_context


def evaluate(
    raw: Optional[Dict[str, Any]] = None,
    *,
    audit: bool = True,
) -> Dict[str, Any]:
    """
    Run F1 checklist R01–R10.
    Returns APPROVED / REJECTED with full checks array.
    Always audits unless skip_audit / audit=False.
    """
    ctx = build_rule_context(raw)
    checks: list = []
    fail_code = None
    fail_reason = None
    dispatch: Dict[str, Any] = {}

    for _rule_id, fn in CHECKLIST:
        c = fn(ctx)
        checks.append(c)
        if c.get("result") != "PASS" and fail_code is None:
            fail_code = c.get("check_name")
            fail_reason = c.get("reason")

    r10, dispatch = check_dispatch_contract(ctx)
    checks.append(r10)
    if r10.get("result") != "PASS" and fail_code is None:
        fail_code = r10.get("check_name")
        fail_reason = r10.get("reason")

    if fail_code:
        verdict = "REJECTED"
        code = fail_code
        reason = fail_reason or "Rule Engine rejected"
    else:
        verdict = "APPROVED"
        code = "APPROVED"
        reason = "All Rule Engine checks PASS"

    result = {
        "verdict": verdict,
        "code": code,
        "reason": reason,
        "checks": checks,
        "dispatch": dispatch,
        "point_id": ctx.get("point_id"),
        "old_value": ctx.get("old_value"),
        "new_value": ctx.get("new_value"),
        "opportunity_id": ctx.get("opportunity_id"),
        "building_id": ctx.get("building_id"),
        "zone_id": ctx.get("zone_id"),
        "action": ctx.get("action"),
        "wrote_setpoints": False,
    }

    do_audit = audit and not ctx.get("skip_audit")
    if do_audit:
        try:
            audit_rule_engine(result, user=ctx.get("user"), building_id=ctx.get("building_id"))
        except Exception:
            pass

    try:
        from backend.workers.watchdog import beat

        beat(note=verdict.lower(), service="rules")
    except Exception:
        pass

    return result
