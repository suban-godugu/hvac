"""Public HVAC Operations & Maintenance API for O17–O20 only."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from backend.services.platform_ops_service import record_control_audit
from backend.services.hvac_operations_maintenance_module import (
    canonical_oid,
    get_opportunity,
    get_opportunities,
    get_dashboard,
    dispatch_gate,
    dispatch_conflict,
)
from backend.services.operations_maintenance_opportunity_service import (
    record_action,
    record_verify,
    record_rollback,
)

router = APIRouter(prefix="/api/hvac/operations-maintenance", tags=["HVAC Operations & Maintenance O17–O20"])


class ActionRequest(BaseModel):
    topic: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    target_value: Optional[float] = None
    context: Optional[Dict[str, Any]] = None


def _oid(raw: str) -> str:
    code = canonical_oid(raw)
    if not code:
        raise HTTPException(
            status_code=404,
            detail={"code": "UNKNOWN_OPPORTUNITY", "message": "Supported: O17, O18, O19, O20.", "opportunityId": raw},
        )
    return code


@router.get("/opportunities")
async def list_opportunities():
    return get_opportunities()


@router.get("/dashboard")
async def dashboard():
    return get_dashboard()


@router.get("/{oid}")
async def get_one(oid: str):
    code = _oid(oid)
    try:
        return get_opportunity(code)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail={"code": "DATA_SOURCE_ERROR", "message": "O&M evaluation failed.", "opportunityId": code},
        )


@router.post("/{oid}/dispatch")
async def dispatch(oid: str, req: ActionRequest):
    code = _oid(oid)
    body = get_opportunity(code)
    ok, reason = dispatch_gate(body)
    if not ok:
        conflict = dispatch_conflict(body)
        conflict["reason"] = reason
        conflict["message"] = conflict.get("message") or reason
        conflict["code"] = conflict.get("code") or "DISPATCH_BLOCKED"
        conflict["dispatchable"] = False
        record_control_audit(user=None, action="DISPATCH_BLOCKED", opportunity_id=code, reason=reason, decision=(body.get("supervisory") or {}).get("decision"), telemetry_status=(body.get("telemetry") or {}).get("state"), safety_status=(body.get("safety") or {}).get("status"), requested_value=req.target_value)
        raise HTTPException(status_code=409, detail=conflict)
    rec = record_action(code, "PLAN_DISPATCH", {"target_value": req.target_value, **(req.context or {})})
    record_control_audit(user=None, action="PLAN_DISPATCH", opportunity_id=code, requested_value=req.target_value, decision="OPTIMIZE", approval_status="NOT_REQUIRED")
    return rec


@router.post("/{oid}/verify")
async def verify(oid: str):
    code = _oid(oid)
    rec = record_verify(code)
    record_control_audit(user=None, action="VERIFY", opportunity_id=code)
    return rec


@router.post("/{oid}/rollback")
async def rollback(oid: str):
    code = _oid(oid)
    if code not in ("O17", "O19"):
        raise HTTPException(status_code=409, detail={"code": "ROLLBACK_UNSUPPORTED", "message": "Rollback is not applicable.", "opportunityId": code})
    rec = record_rollback(code)
    record_control_audit(user=None, action="ROLLBACK", opportunity_id=code)
    return rec


@router.post("/{oid}/training-action")
async def training_action(oid: str, req: ActionRequest):
    code = _oid(oid)
    if code != "O18":
        raise HTTPException(status_code=404, detail={"code": "UNKNOWN_OPPORTUNITY", "message": "training-action is O18 only.", "opportunityId": code})
    rec = record_action(code, "TRAINING_ACTION", {"topic": req.topic, **(req.details or {})})
    record_control_audit(user=None, action="TRAINING_ACTION", opportunity_id=code, requested_value=req.topic)
    return rec


@router.post("/{oid}/maintenance-action")
async def maintenance_action(oid: str, req: ActionRequest):
    code = _oid(oid)
    if code != "O19":
        raise HTTPException(status_code=404, detail={"code": "UNKNOWN_OPPORTUNITY", "message": "maintenance-action is O19 only.", "opportunityId": code})
    rec = record_action(code, "MAINTENANCE_ACTION", req.details or {})
    record_control_audit(user=None, action="MAINTENANCE_ACTION", opportunity_id=code)
    return rec


@router.post("/{oid}/change-request")
async def change_request(oid: str, req: ActionRequest):
    code = _oid(oid)
    if code != "O20":
        raise HTTPException(status_code=404, detail={"code": "UNKNOWN_OPPORTUNITY", "message": "change-request is O20 only.", "opportunityId": code})
    rec = record_action(code, "CHANGE_REQUEST", req.details or {"status": "REVIEW_REQUIRED"})
    record_control_audit(user=None, action="CHANGE_REQUEST", opportunity_id=code)
    return rec
