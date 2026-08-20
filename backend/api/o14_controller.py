"""O14 Optimised Secondary Chilled Water Pumping — one domain controller."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.services import o14_service
from backend.services.canonical_telemetry_service import latest_points

router = APIRouter(prefix="/api/agents/variable-speed/o14", tags=["O14 Secondary CHW Pumping"])


class TelemetryIngest(BaseModel):
    building_id: Optional[str] = None
    points: List[Dict[str, Any]]


class OptimizeBody(BaseModel):
    building_id: Optional[str] = None


class CommandBody(BaseModel):
    command_id: Optional[str] = None
    confirm: bool = False


class ConfigBody(BaseModel):
    most_open_valve_target_pct: Optional[float] = None
    dp_setpoint_trim: Optional[float] = None
    dp_setpoint_trim_unit: Optional[str] = None
    speed_trim_pct: Optional[float] = None
    min_pump_speed_pct: Optional[float] = None
    max_pump_speed_pct: Optional[float] = None
    min_dp: Optional[float] = None
    max_dp: Optional[float] = None
    min_flow: Optional[float] = None
    max_flow: Optional[float] = None
    max_speed_step_pct: Optional[float] = None
    verify_tolerance: Optional[float] = None
    control_mode: Optional[str] = None
    building_id: Optional[str] = None


class SafeModeBody(BaseModel):
    reason: Optional[str] = None


def _http(exc: Exception, status: int = 409) -> HTTPException:
    code = getattr(exc, "args", ["ERROR"])[0] if exc.args else type(exc).__name__
    if isinstance(exc, KeyError):
        return HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Command not found."})
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=409, detail={"code": str(exc), "message": str(exc)})
    return HTTPException(status_code=status, detail={"code": "DISPATCH_BLOCKED", "message": str(exc)})


@router.get("/dashboard")
async def dashboard():
    return o14_service.dashboard()


@router.get("/telemetry")
async def telemetry(building_id: Optional[str] = None):
    sampled = o14_service.sample_o14(building_id)
    return {
        "opportunity": "O14",
        "points": sampled.get("_points") or latest_points(building_id, limit=200),
        "sampled": {k: sampled[k] for k in sampled if not str(k).startswith("_") and "__" not in str(k)},
        "source": sampled.get("source"),
        "quality": sampled.get("quality"),
    }


@router.post("/telemetry")
async def post_telemetry(body: TelemetryIngest):
    n = o14_service.ingest_points(body.points, body.building_id)
    return {"ingested": n, "state": o14_service.evaluate_o14(persist=True, building_id=body.building_id)}


@router.get("/state")
async def state():
    return o14_service.evaluate_o14(persist=False)


@router.get("/recommendation")
async def recommendation():
    s = o14_service.evaluate_o14(persist=False)
    return {
        "recommendation": s.get("recommendation"),
        "recommendation_state": s.get("recommendation_state"),
        "current": s.get("current_value"),
        "recommended": s.get("optimized_value"),
        "unit": s.get("unit"),
        "expected_effect": s.get("why"),
        "reason": s.get("reason"),
        "confidence": s.get("confidence"),
        "safety": s.get("safety_status"),
        "data_quality": (s.get("classified_telemetry") or {}).get("status"),
        "why": s.get("why"),
    }


@router.get("/kpis")
async def kpis():
    return o14_service.kpis()


@router.get("/pumps")
async def pumps():
    return {"pumps": o14_service.list_pumps()}


@router.get("/history")
async def history(hours: int = Query(24, ge=1, le=720)):
    return o14_service.history(hours)


@router.get("/safety")
async def safety():
    return o14_service.safety_view()


@router.get("/commands")
async def commands():
    return {"commands": o14_service.command_list()}


@router.post("/optimize")
async def optimize(body: Optional[OptimizeBody] = None):
    del body
    return o14_service.optimize()


@router.post("/commands")
async def post_command(body: CommandBody):
    return o14_service.create_command(body.model_dump())


@router.post("/commands/{command_id}/apply")
async def apply(command_id: str, body: Optional[CommandBody] = None):
    confirm = bool(body and body.confirm)
    try:
        return o14_service.apply_command(command_id, confirm=confirm)
    except Exception as exc:
        raise _http(exc)


@router.post("/commands/{command_id}/verify")
async def verify(command_id: str):
    try:
        return o14_service.verify(command_id)
    except Exception as exc:
        raise _http(exc)


@router.post("/commands/{command_id}/rollback")
async def rollback(command_id: str):
    try:
        return o14_service.rollback(command_id)
    except Exception as exc:
        raise _http(exc)


@router.get("/runs")
async def runs():
    return {"runs": o14_service.runs()}


@router.get("/audit")
async def audit():
    return {"events": o14_service.audit_events()}


@router.get("/config")
async def config():
    return o14_service.get_config()


@router.post("/config")
async def post_config(body: ConfigBody):
    return o14_service.save_config(body.model_dump(exclude_none=True))


@router.post("/safe-mode")
async def safe_mode(body: Optional[SafeModeBody] = None):
    return o14_service.enter_safe_mode(body.reason if body else None)
