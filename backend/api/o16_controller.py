"""O16 Variable Head Pressure Control — Water-Cooled Condensers — domain controller."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from backend.agents.runtime.command import get_command
from backend.services import o16_service
from backend.services.canonical_telemetry_service import latest_points

router = APIRouter(prefix="/api/agents/variable-speed/o16", tags=["O16 Water-Cooled Head Pressure"])


class TelemetryIngest(BaseModel):
    building_id: Optional[str] = None
    points: List[Dict[str, Any]]


class CommandBody(BaseModel):
    command_id: Optional[str] = None
    confirm: bool = False


class ConfigBody(BaseModel):
    enabled: Optional[bool] = None
    control_mode: Optional[str] = None
    control_strategy: Optional[str] = None
    shared_pump: Optional[bool] = None
    target_head_pressure: Optional[float] = None
    target_condensing_temp_c: Optional[float] = None
    min_head_pressure: Optional[float] = None
    max_head_pressure: Optional[float] = None
    min_condensing_temp_c: Optional[float] = None
    max_condensing_temp_c: Optional[float] = None
    min_pump_speed_pct: Optional[float] = None
    max_pump_speed_pct: Optional[float] = None
    min_cw_flow: Optional[float] = None
    max_cw_flow: Optional[float] = None
    min_valve_pct: Optional[float] = None
    max_valve_pct: Optional[float] = None
    pump_trim_pct: Optional[float] = None
    valve_trim_pct: Optional[float] = None
    hp_deadband: Optional[float] = None
    max_pump_step_pct: Optional[float] = None
    high_load_pct: Optional[float] = None
    isolate_valve_pct: Optional[float] = None
    verify_tolerance: Optional[float] = None
    refrigerant: Optional[str] = None
    building_id: Optional[str] = None


class SafeModeBody(BaseModel):
    reason: Optional[str] = None


def _http(exc: Exception, status: int = 409) -> HTTPException:
    if isinstance(exc, KeyError):
        return HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Command not found."})
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=409, detail={"code": str(exc), "message": str(exc)})
    return HTTPException(status_code=status, detail={"code": "DISPATCH_BLOCKED", "message": str(exc)})


@router.get("/dashboard")
async def dashboard():
    return o16_service.dashboard()


@router.get("/state")
async def state():
    return o16_service.evaluate_o16(persist=False)


@router.get("/telemetry")
async def telemetry(building_id: Optional[str] = None):
    sampled = o16_service.sample_o16(building_id)
    return {
        "opportunity": "O16",
        "points": sampled.get("_points") or latest_points(building_id, limit=200),
        "sampled": {k: sampled[k] for k in sampled if not str(k).startswith("_") and "__" not in str(k)},
        "source": sampled.get("source"),
        "quality": sampled.get("quality"),
    }


@router.post("/telemetry")
async def post_telemetry(body: TelemetryIngest):
    n = o16_service.ingest_points(body.points, body.building_id)
    return {"ingested": n, "state": o16_service.evaluate_o16(persist=True, building_id=body.building_id)}


@router.get("/recommendation")
async def recommendation():
    s = o16_service.evaluate_o16(persist=False)
    return {
        "recommendation": s.get("recommendation"),
        "recommendation_state": s.get("recommendation_state"),
        "current": s.get("current_value"),
        "recommended": s.get("optimized_value"),
        "unit": s.get("unit"),
        "reason": s.get("reason"),
        "confidence": s.get("confidence"),
        "safety": s.get("safety_status"),
        "why": s.get("why"),
        "current_state": s.get("current_state"),
        "optimized_state": s.get("optimized_state"),
    }


@router.post("/optimize")
async def optimize():
    return o16_service.optimize()


@router.post("/commands")
async def post_command(body: CommandBody):
    return o16_service.create_command(body.model_dump())


@router.get("/commands")
async def commands():
    return {"commands": o16_service.command_list()}


@router.get("/commands/{command_id}")
async def command_one(command_id: str):
    row = get_command(command_id)
    if not row or row.get("opportunity") != "O16":
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Command not found."})
    return row


@router.post("/commands/{command_id}/approve")
async def approve(command_id: str):
    try:
        return o16_service.approve_command(command_id)
    except Exception as exc:
        raise _http(exc)


@router.post("/commands/{command_id}/apply")
async def apply(command_id: str, body: Optional[CommandBody] = None):
    try:
        return o16_service.apply_command(command_id, confirm=bool(body and body.confirm))
    except Exception as exc:
        raise _http(exc)


@router.post("/commands/{command_id}/verify")
async def verify(command_id: str):
    try:
        return o16_service.verify(command_id)
    except Exception as exc:
        raise _http(exc)


@router.post("/commands/{command_id}/rollback")
async def rollback(command_id: str):
    try:
        return o16_service.rollback(command_id)
    except Exception as exc:
        raise _http(exc)


@router.get("/history")
async def history(hours: int = Query(24, ge=1, le=720), format: Optional[str] = None):
    data = o16_service.history(hours)
    if (format or "").lower() == "csv":
        cols = ["timestamp", "head_pressure", "condensing_temperature", "cw_supply", "cw_return", "cw_flow", "pump_speed", "pump_power", "load", "quality", "source"]
        lines = [",".join(cols)]
        for p in data.get("points") or []:
            lines.append(",".join("" if p.get(c) is None else str(p.get(c)) for c in cols))
        return PlainTextResponse("\n".join(lines) + "\n", media_type="text/csv")
    return data


@router.get("/health")
async def health():
    return o16_service.health()


@router.get("/equipment")
async def equipment():
    return {"equipment": o16_service.list_equipment()}


@router.get("/safety")
async def safety():
    return o16_service.safety_view()


@router.get("/runs")
async def runs():
    return {"runs": o16_service.runs()}


@router.get("/audit")
async def audit():
    return {"events": o16_service.audit_events()}


@router.get("/config")
async def config():
    return o16_service.get_config()


@router.post("/config")
async def post_config(body: ConfigBody):
    return o16_service.save_config(body.model_dump(exclude_none=True))


@router.post("/safe-mode")
async def safe_mode(body: Optional[SafeModeBody] = None):
    return o16_service.enter_safe_mode(body.reason if body else None)
