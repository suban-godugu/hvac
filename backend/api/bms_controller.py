"""Read-only BMS platform APIs. Writes are rejected with WRITE_DISABLED."""
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.bms.command_writer import write_disabled_body, write_point
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


@router.post("/write-enable")
async def write_enable():
    body = write_disabled_body("Write enable is blocked during Phase 1 read-only commissioning.")
    raise HTTPException(status_code=409, detail=body)


@router.post("/write")
async def write(payload: Dict[str, Any]):
    outcome = write_point(str(payload.get("point_id") or ""), float(payload.get("value") or 0))
    raise HTTPException(status_code=409, detail={**write_disabled_body(), **outcome.as_dict()})


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
