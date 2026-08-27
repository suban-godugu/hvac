"""BMS platform APIs. Supervised writes go through evaluate_dispatch()."""
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.bms.command_writer import disable_supervised_writes, enable_supervised_writes, write_disabled_body, write_point
from backend.bms.connection_manager import get_connection_manager
from backend.middleware.request_id import current_request_id
from backend.services import platform_bms_service as bms

router = APIRouter(prefix="/api/platform/bms", tags=["BMS"])
safety_router = APIRouter(prefix="/api/platform", tags=["Platform"])
agents_router = APIRouter(prefix="/api", tags=["Agents"])


class ConnectRequest(BaseModel):
    protocol: str = "bacnet"
    host: str
    port: int = 47808
    building_id: Optional[str] = None
    test_only: bool = False


class MappingRequest(BaseModel):
    equipment_id: str
    canonical_point: str
    bms_point_id: str
    direction: str = "READ"
    safety_enabled: bool = True


class WriteEnableRequest(BaseModel):
    confirm: bool = False


class DispatchApplyRequest(BaseModel):
    opportunity_id: str
    point_id: Optional[str] = None
    equipment_id: Optional[str] = None
    current_value: Optional[float] = None
    target_value: Optional[float] = None
    confidence: Optional[float] = None
    decision: Optional[str] = "OPTIMIZE"


class SafetyEvaluateRequest(BaseModel):
    opportunity_id: Optional[str] = None
    current_value: Optional[float] = None
    target_value: Optional[float] = None
    confidence: Optional[float] = None
    decision: Optional[str] = "OPTIMIZE"


@router.get("/status")
async def get_status():
    return bms.bms_status()


@router.post("/connect")
async def connect(req: ConnectRequest):
    mgr = get_connection_manager()
    return mgr.connect(req.protocol, req.host, req.port, building_id=req.building_id, test_only=req.test_only)


@router.post("/disconnect")
async def disconnect():
    return get_connection_manager().disconnect()


@router.post("/discover")
async def discover():
    return get_connection_manager().discover()


@router.get("/devices")
async def devices():
    rows = bms.list_devices()
    return {"devices": rows, "count": len(rows)}


@router.get("/devices/{device_id}/points")
async def device_points(device_id: str):
    pts = bms.list_points(device_id)
    return {"points": pts, "count": len(pts)}


@router.get("/mappings")
async def get_mappings():
    return {"mappings": bms.list_mappings(), "catalog": bms.catalog()}


@router.put("/mappings")
async def put_mappings(req: MappingRequest):
    try:
        row = bms.put_mapping(req.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "MAPPING_INVALID", "message": str(exc)})
    return row


@router.get("/telemetry")
async def telemetry():
    return {"points": bms.mapped_telemetry()}


@router.get("/plant")
async def plant():
    return bms.plant_overview()


@router.get("/stage-g/status")
async def stage_g_status(point_id: Optional[str] = None):
    from backend.bms.stage_g import stage_g_status as _status

    return _status(point_id)


@router.post("/write-enable")
async def write_enable(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    body = enable_supervised_writes(confirm=bool((payload or {}).get("confirm")))
    if not body.get("enabled"):
        raise HTTPException(status_code=409, detail=body)
    return body


@router.post("/write-disable")
async def write_disable():
    return disable_supervised_writes()


@router.post("/write")
async def write(payload: Dict[str, Any]):
    from backend.services.hvac_safety_contract import evaluate_dispatch
    from backend.services.platform_bms_service import platform_snapshot

    snap = platform_snapshot()
    tel = snap.get("telemetry") or {}
    ctx = {
        "action": "APPLY",
        "opportunity_id": payload.get("opportunity_id") or payload.get("opportunity"),
        "source": tel.get("source"),
        "telemetry": {
            "source": tel.get("source"),
            "quality": tel.get("quality"),
            "age_seconds": tel.get("ageSeconds"),
            "raw": tel.get("status"),
        },
        "supervisory": {"decision": payload.get("decision") or "OPTIMIZE", "confidence": payload.get("confidence")},
        "safety": {"status": snap.get("safety"), "passed": snap.get("safety") == "PASS"},
        "current_value": payload.get("current_value"),
        "target_value": payload.get("value") if payload.get("target_value") is None else payload.get("target_value"),
    }
    ok, reason, classified = evaluate_dispatch(ctx)
    if not ok:
        raise HTTPException(status_code=409, detail={**write_disabled_body(reason, classified.get("code") or "DISPATCH_BLOCKED"), "reason": reason})
    outcome = write_point(str(payload.get("point_id") or ""), float(payload.get("value") or 0))
    if not outcome.success:
        raise HTTPException(status_code=409, detail={**write_disabled_body(outcome.message, outcome.code), **outcome.as_dict()})
    return outcome.as_dict()


@safety_router.post("/commands/apply")
async def command_apply(req: DispatchApplyRequest):
    from backend.agents.runtime.recommendation import recommend_and_maybe_apply
    from backend.services.platform_bms_service import platform_snapshot

    snap = platform_snapshot()
    tel = snap.get("telemetry") or {}
    result = recommend_and_maybe_apply(
        opportunity=req.opportunity_id,
        building_id=None,
        point_id=req.point_id,
        old_value=req.current_value,
        new_value=req.target_value,
        reason="SUPERVISED_APPLY",
        user={},
        mode="SUPERVISED",
        context={
            "source": tel.get("source"),
            "telemetry": {
                "source": tel.get("source"),
                "quality": tel.get("quality"),
                "age_seconds": tel.get("ageSeconds"),
                "raw": tel.get("status"),
            },
            "supervisory": {"decision": req.decision or "OPTIMIZE", "confidence": req.confidence},
            "safety": {"status": snap.get("safety"), "passed": snap.get("safety") == "PASS"},
            "equipment_id": req.equipment_id,
            "confidence": req.confidence,
        },
    )
    if not result.get("allowed"):
        raise HTTPException(
            status_code=409,
            detail={
                "code": (result.get("classified") or {}).get("code") or "DISPATCH_BLOCKED",
                "message": result.get("reason") or "Dispatch blocked.",
                "command": result.get("command"),
            },
        )
    return result


@safety_router.post("/commands/{command_id}/approve")
async def command_approve(command_id: str):
    from backend.agents.runtime.approval import approve_command

    ok, reason, cmd = approve_command(command_id)
    if not ok:
        raise HTTPException(status_code=409, detail={"code": reason, "message": reason, "command_id": command_id, "command": cmd})
    return {"ok": True, "status": reason, "command_id": command_id, "command": cmd}


@safety_router.post("/commands/{command_id}/apply")
async def command_apply_existing(command_id: str):
    """Stage G: apply an existing APPROVED control_commands row (Safe RL / O*)."""
    from backend.agents.runtime.apply import apply_setpoint
    from backend.agents.runtime.command import get_command
    from backend.bms.stage_g import point_allowed, prerequisites_ok
    from backend.services.platform_bms_service import platform_snapshot

    cmd = get_command(command_id)
    if not cmd:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Command not found", "command_id": command_id})
    status = (cmd.get("status") or "").upper()
    if status != "APPROVED":
        raise HTTPException(
            status_code=409,
            detail={"code": "NOT_APPROVED", "message": f"Command status is {status}; APPROVED required", "command": cmd},
        )
    point_id = str(cmd.get("point_id") or "")
    if not point_allowed(point_id):
        raise HTTPException(
            status_code=409,
            detail={"code": "STAGE_G_POINT_NOT_ALLOWED", "message": f"{point_id} not on Stage G allowlist", "command": cmd},
        )
    gate = prerequisites_ok(point_id)
    if not gate.get("ok"):
        raise HTTPException(
            status_code=409,
            detail={"code": "STAGE_G_PREREQS", "message": "Stage G prerequisites not met", "prerequisites": gate, "command": cmd},
        )
    new_value = cmd.get("new_value")
    if new_value is None:
        raise HTTPException(status_code=409, detail={"code": "MISSING_VALUES", "message": "new_value required", "command": cmd})

    snap = platform_snapshot()
    tel = snap.get("telemetry") or {}
    context = {
        "action": "APPLY",
        "opportunity_id": cmd.get("opportunity"),
        "point_id": point_id,
        "old_value": cmd.get("old_value"),
        "current_value": cmd.get("old_value"),
        "new_value": float(new_value),
        "target_value": float(new_value),
        "approval_status": "APPROVED",
        "mode": "SUPERVISED",
        "source": tel.get("source"),
        "telemetry": {
            "source": tel.get("source"),
            "quality": tel.get("quality"),
            "age_seconds": tel.get("ageSeconds"),
            "raw": tel.get("status"),
        },
        "supervisory": {"decision": "OPTIMIZE", "confidence": 0.99},
        "safety": {"status": snap.get("safety"), "passed": snap.get("safety") == "PASS"},
        "confidence": 0.99,
        "decision": "OPTIMIZE",
        "building_id": cmd.get("building_id"),
        "equipment_id": cmd.get("equipment_id"),
        "normalized": {"Indoor_Temp": None, "Occupancy": 0.5, "quality": tel.get("quality") or "GOOD"},
        "schedule_hour": 12,
    }
    ok, reason = apply_setpoint(command_id, point_id, float(new_value), context)
    if not ok:
        raise HTTPException(
            status_code=409,
            detail={"code": reason, "message": reason, "command_id": command_id, "command": get_command(command_id)},
        )
    return {"ok": True, "status": reason, "command_id": command_id, "command": get_command(command_id)}


@safety_router.post("/commands/{command_id}/verify")
async def command_verify(command_id: str):
    from backend.agents.runtime.verification import verify_command

    ok, reason = verify_command(command_id)
    if not ok:
        raise HTTPException(status_code=409, detail={"code": reason, "message": reason, "command_id": command_id})
    return {"ok": True, "status": reason, "command_id": command_id}


@safety_router.post("/commands/{command_id}/rollback")
async def command_rollback(command_id: str):
    from backend.agents.runtime.verification import rollback_command

    ok, reason = rollback_command(command_id)
    if not ok:
        raise HTTPException(status_code=409, detail={"code": reason, "message": reason, "command_id": command_id})
    return {"ok": True, "status": reason, "command_id": command_id}


@safety_router.get("/dashboard/home")
async def dashboard_home():
    from backend.services.dashboard_home_service import dashboard_home as _home

    return _home()


@safety_router.get("/safety/evaluate")
@safety_router.post("/safety/evaluate")
async def safety_evaluate(req: Optional[SafetyEvaluateRequest] = None):
    return bms.evaluate_safety(req.model_dump() if req else {})


@agents_router.get("/agents")
async def agent_center():
    return {"groups": bms.agent_groups(), "request_id": current_request_id()}


@agents_router.get("/agents/{opportunity}/context")
async def agent_context(opportunity: str, equipment_id: Optional[str] = None, building_id: Optional[str] = None):
    from backend.services.agent_telemetry_service import get_agent_context
    from backend.services.opportunity_feature_catalog import catalog_for

    try:
        catalog_for(opportunity)
    except KeyError:
        raise HTTPException(status_code=404, detail={"code": "UNKNOWN_OPPORTUNITY", "message": opportunity})
    return get_agent_context(opportunity, equipment_id, building_id)


@agents_router.get("/agents/{opportunity}/recommendation")
async def agent_recommendation(opportunity: str, equipment_id: Optional[str] = None, building_id: Optional[str] = None):
    from backend.services.agent_recommendation_service import build_recommendation
    from backend.services.opportunity_feature_catalog import catalog_for

    try:
        catalog_for(opportunity)
    except KeyError:
        raise HTTPException(status_code=404, detail={"code": "UNKNOWN_OPPORTUNITY", "message": opportunity})
    return build_recommendation(opportunity, equipment_id, building_id)
