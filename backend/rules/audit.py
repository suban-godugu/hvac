"""Always audit Rule Engine verdicts to control_audit_logs."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.services.platform_ops_service import record_control_audit


def audit_rule_engine(
    result: Dict[str, Any],
    *,
    user: Optional[Dict[str, Any]] = None,
    building_id: Optional[str] = None,
) -> str:
    verdict = result.get("verdict") or "REJECTED"
    action = "RULE_ENGINE_APPROVED" if verdict == "APPROVED" else "RULE_ENGINE_REJECTED"
    return record_control_audit(
        user=user or {},
        action=action,
        opportunity_id=result.get("opportunity_id"),
        previous_value=result.get("old_value"),
        requested_value=result.get("new_value"),
        decision=verdict,
        safety_status=verdict,
        telemetry_status=(result.get("dispatch") or {}).get("status"),
        approval_status=None,
        reason=result.get("reason"),
        building_id=building_id or result.get("building_id"),
        payload_json={
            "checks": result.get("checks"),
            "code": result.get("code"),
            "point_id": result.get("point_id"),
            "old_value": result.get("old_value"),
            "new_value": result.get("new_value"),
            "opportunity_id": result.get("opportunity_id"),
            "zone_id": result.get("zone_id"),
            "action": result.get("action"),
        },
    )


def list_rule_audits(limit: int = 20) -> List[Dict[str, Any]]:
    from database.session import SessionLocal
    from database.models_platform import ControlAuditLogDB

    db = SessionLocal()
    try:
        rows = (
            db.query(ControlAuditLogDB)
            .filter(ControlAuditLogDB.action.in_(["RULE_ENGINE_APPROVED", "RULE_ENGINE_REJECTED"]))
            .order_by(ControlAuditLogDB.timestamp.desc())
            .limit(max(1, min(100, int(limit))))
            .all()
        )
        out = []
        for r in rows:
            out.append(
                {
                    "id": r.id,
                    "request_id": r.request_id,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                    "action": r.action,
                    "opportunity_id": r.opportunity_id,
                    "decision": r.decision,
                    "safety_status": r.safety_status,
                    "reason": r.reason,
                    "previous_value": r.previous_value,
                    "requested_value": r.requested_value,
                    "building_id": r.building_id,
                    "payload_json": r.payload_json,
                }
            )
        return out
    finally:
        db.close()
