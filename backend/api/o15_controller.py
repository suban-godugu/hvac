"""O15 Variable Head Pressure Control — Air-Cooled Condensers — domain controller."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from backend.services import o15_service
from backend.services.canonical_telemetry_service import latest_points

router = APIRouter(prefix="/api/agents/variable-speed/o15", tags=["O15 Air-Cooled Head Pressure"])


class TelemetryIngest(BaseModel):
    building_id: Optional[str] = None
    points: List[Dict[str, Any]]


class CommandBody(BaseModel):
    command_id: Optional[str] = None
    confirm: bool = False


class ConfigBody(BaseModel):
    approach_c: Optional[float] = None
    approach_min_c: Optional[float] = None
    approach_max_c: Optional[float] = None
    min_head_pressure: Optional[float] = None
    max_head_pressure: Optional[float] = None
    min_condensing_temp_c: Optional[float] = None
    max_condensing_temp_c: Optional[float] = None
    min_fan_speed_pct: Optional[float] = None
    max_fan_speed_pct: Optional[float] = None
    fan_trim_pct: Optional[float] = None
    tcond_deadband_c: Optional[float] = None
    max_fan_step_pct: Optional[float] = None
    verify_tolerance: Optional[float] = None
    refrigerant: Optional[str] = None
    saturation_curve_json: Optional[list] = None
    control_mode: Optional[str] = None
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
    return o15_service.dashboard()


@router.get("/state")
async def state():
    return o15_service.evaluate_o15(persist=False)


@router.get("/telemetry")
async def telemetry(building_id: Optional[str] = None):
    sampled = o15_service.sample_o15(building_id)
    return {
        "opportunity": "O15",
        "points": sampled.get("_points") or latest_points(building_id, limit=200),
        "sampled": {k: sampled[k] for k in sampled if not str(k).startswith("_") and "__" not in str(k)},
        "source": sampled.get("source"),
        "quality": sampled.get("quality"),
    }


@router.post("/telemetry")
async def post_telemetry(body: TelemetryIngest):
    n = o15_service.ingest_points(body.points, body.building_id)
    return {"ingested": n, "state": o15_service.evaluate_o15(persist=True, building_id=body.building_id)}


@router.get("/kpis")
async def kpis():
    return o15_service.kpis()


@router.get("/condensers")
async def condensers():
    return {"condensers": o15_service.list_condensers()}


@router.get("/fans")
async def fans():
    return {"fans": o15_service.list_fans()}


@router.get("/recommendation")
async def recommendation():
    s = o15_service.evaluate_o15(persist=False)
    return {
        "recommendation": s.get("recommendation"),
        "recommendation_state": s.get("recommendation_state"),
        "current": s.get("current_value"),
        "recommended": s.get("optimized_value"),
        "unit": s.get("unit"),
        "reason": s.get("reason"),
        "confidence": s.get("confidence"),
        "safety": s.get("safety_status"),
        "data_quality": (s.get("classified_telemetry") or {}).get("status"),
        "why": s.get("why"),
        "current_state": s.get("current_state"),
        "optimized_state": s.get("optimized_state"),
    }


@router.get("/safety")
async def safety():
    return o15_service.safety_view()


@router.get("/history")
async def history(hours: int = Query(24, ge=1, le=720), format: Optional[str] = None):
    data = o15_service.history(hours)
    if (format or "").lower() == "csv":
        cols = [
            "timestamp",
            "outdoor_air_temperature",
            "head_pressure",
            "head_pressure_setpoint",
            "condensing_temperature",
            "fan_speed",
            "fan_power",
            "compressor_power",
            "load",
            "quality",
            "source",
        ]
        lines = [",".join(cols)]
        for p in data.get("points") or []:
            lines.append(",".join("" if p.get(c) is None else str(p.get(c)) for c in cols))
        return PlainTextResponse("\n".join(lines) + "\n", media_type="text/csv")
    return data


@router.get("/commands")
async def commands():
    return {"commands": o15_service.command_list()}


@router.post("/optimize")
async def optimize():
    return o15_service.optimize()


@router.post("/commands")
async def post_command(body: CommandBody):
    return o15_service.create_command(body.model_dump())


@router.post("/commands/{command_id}/apply")
async def apply(command_id: str, body: Optional[CommandBody] = None):
    try:
        return o15_service.apply_command(command_id, confirm=bool(body and body.confirm))
    except Exception as exc:
        raise _http(exc)


@router.post("/commands/{command_id}/verify")
async def verify(command_id: str):
    try:
        return o15_service.verify(command_id)
    except Exception as exc:
        raise _http(exc)


@router.post("/commands/{command_id}/rollback")
async def rollback(command_id: str):
    try:
        return o15_service.rollback(command_id)
    except Exception as exc:
        raise _http(exc)


@router.get("/runs")
async def runs():
    return {"runs": o15_service.runs()}


@router.get("/audit")
async def audit():
    return {"events": o15_service.audit_events()}


@router.get("/config")
async def config():
    return o15_service.get_config()


@router.post("/config")
async def post_config(body: ConfigBody):
    return o15_service.save_config(body.model_dump(exclude_none=True))


@router.post("/safe-mode")
async def safe_mode(body: Optional[SafeModeBody] = None):
    return o15_service.enter_safe_mode(body.reason if body else None)
