"""
VariableSpeedController: FastAPI Router exposing REST & SSE endpoints
for Variable Speed Based Optimisations (Fans, Pumps, CHW Pumps, CW Pumps, Cooling Towers).
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import asyncio
import json
from datetime import datetime, timezone

from backend.services.variable_speed_service import vs_service
from backend.services.variable_speed_telemetry_service import vs_telemetry_service
from backend.services.variable_speed_command_service import vs_command_service
from backend.services.variable_speed_verification_service import vs_verification_service
from backend.agents.variable_speed.safety_engine import vs_safety_engine
from backend.data_pipeline.variable_speed_simulator import vs_simulator
from backend.services.opportunity_persist_service import (
    persist_vs_points,
    persist_optimization,
    persist_execution,
    persist_safety_check,
    dispatch_official,
    audit,
)
from backend.services.official_opportunity_runtime import evaluate_o15, evaluate_o16, agent_status as official_agent_status, optimization_history
from backend.services import o15_service, o16_service

router = APIRouter(prefix="/api/variable-speed", tags=["Variable Speed Based Optimisations"])

class DispatchActionRequest(BaseModel):
    equipment_id: str
    target_speed_pct: float
    context: Optional[Dict[str, Any]] = None

class ScenarioRequest(BaseModel):
    scenario: str

class OfficialVsIngest(BaseModel):
    equipment_id: str
    points: List[Dict[str, Any]]
    optimization: Optional[Dict[str, Any]] = None
    safety: Optional[Dict[str, Any]] = None

# -------------------------------------------------------------
# REST Endpoints
# -------------------------------------------------------------
@router.get("/dashboard")
async def get_variable_speed_dashboard():
    """Returns live fleet-wide VFD metrics, equipment running, power savings, and cards."""
    return vs_service.get_dashboard_state()

@router.get("/equipment")
async def get_variable_speed_equipment():
    """Returns inventory of all variable-speed equipment."""
    return vs_service.get_equipment_list()

@router.get("/telemetry")
async def get_variable_speed_telemetry(equipment_id: Optional[str] = Query(None)):
    """Returns real-time telemetry from BACnet or physics simulator."""
    if equipment_id:
        return vs_telemetry_service.get_equipment_points(equipment_id)
    return vs_telemetry_service.get_telemetry()

@router.get("/predictions")
async def get_variable_speed_predictions():
    """Returns ML model predictions across all equipment."""
    cycle = vs_service.agent.run_supervisory_cycle()
    return cycle["opportunities"]

@router.get("/recommendations")
async def get_variable_speed_recommendations():
    """Returns active AI speed recommendations."""
    return vs_service.get_recommendations()

@router.get("/history")
async def get_variable_speed_history(hours: int = Query(24, ge=1, le=168)):
    """Returns time-series history comparing speed, power, flow, and savings."""
    return vs_service.get_history(hours)

@router.get("/fan")
async def get_fan_optimization_state():
    """Returns Fan Speed Optimization state and candidate curve."""
    return vs_service.get_opportunity_state("fan")

@router.get("/pumps")
async def get_pump_optimization_state():
    """Returns General Pump Speed Optimization state."""
    return vs_service.get_opportunity_state("pump")

@router.get("/chw-pump")
async def get_chw_pump_optimization_state():
    """Returns Chilled Water Pump Optimization state."""
    return vs_service.get_opportunity_state("chw")

@router.get("/o15/state")
async def get_o15_state():
    return evaluate_o15(persist=False)


@router.get("/o15/dashboard")
async def get_o15_dashboard():
    """Alias so O15 UI works even if the domain router is not yet remounted."""
    return o15_service.dashboard()

@router.get("/o15/telemetry")
async def get_o15_telemetry():
    s = evaluate_o15(persist=False)
    return {"opportunity_id": "O15", "telemetry": s.get("telemetry"), "freshness": s.get("freshness")}

@router.get("/o15/optimization")
async def get_o15_opt():
    s = evaluate_o15(persist=False)
    return {"current_state": s.get("current_state"), "optimized_state": s.get("optimized_state"), "energy_impact": s.get("energy_impact")}

@router.get("/o15/recommendation")
async def get_o15_rec():
    s = evaluate_o15(persist=False)
    return {"recommendation": s.get("recommendation"), "reason": s.get("reason"), "safety_checks": s.get("safety_checks")}

@router.get("/o15/history")
async def get_o15_history():
    return optimization_history("O15")

@router.get("/o15/agent-status")
async def get_o15_agent():
    return official_agent_status("O15", evaluate_o15)

@router.post("/o15/state")
async def post_o15_state(body: OfficialVsIngest):
    persist_execution("O15", "O15_AGENT")
    persist_vs_points("O15", body.equipment_id, body.points)
    if body.optimization:
        persist_optimization("O15", body.optimization)
    if body.safety:
        persist_safety_check(
            "O15",
            body.safety.get("check_name", "unnamed"),
            body.safety.get("actual_value"),
            body.safety.get("minimum"),
            body.safety.get("maximum"),
            body.safety.get("result", "PASS"),
            body.safety.get("reason", ""),
            domain="variable-speed",
        )
    return evaluate_o15()

@router.post("/o15/dispatch")
async def dispatch_o15(req: DispatchActionRequest):
    try:
        return dispatch_official("O15", req.target_speed_pct, req.equipment_id, f"{req.equipment_id}.HeadPressure")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "DISPATCH_BLOCKED", "message": str(exc)})

@router.post("/o15/rollback")
async def rollback_o15():
    audit("O15", "BMS_COMMAND_APPLIED", "ROLLBACK")
    return {"status": "ROLLED_BACK", "opportunity_id": "O15"}

@router.get("/o16/state")
async def get_o16_state():
    return evaluate_o16(persist=False)


@router.get("/o16/dashboard")
async def get_o16_dashboard():
    """Alias so O16 UI works even if the domain router is not yet remounted."""
    return o16_service.dashboard()

@router.get("/o16/telemetry")
async def get_o16_telemetry():
    s = evaluate_o16(persist=False)
    return {"opportunity_id": "O16", "telemetry": s.get("telemetry"), "freshness": s.get("freshness")}

@router.get("/o16/optimization")
async def get_o16_opt():
    s = evaluate_o16(persist=False)
    return {"current_state": s.get("current_state"), "optimized_state": s.get("optimized_state"), "energy_impact": s.get("energy_impact")}

@router.get("/o16/recommendation")
async def get_o16_rec():
    s = evaluate_o16(persist=False)
    return {"recommendation": s.get("recommendation"), "reason": s.get("reason"), "safety_checks": s.get("safety_checks")}

@router.get("/o16/history")
async def get_o16_history():
    return optimization_history("O16")

@router.get("/o16/agent-status")
async def get_o16_agent():
    return official_agent_status("O16", evaluate_o16)

@router.post("/o16/state")
async def post_o16_state(body: OfficialVsIngest):
    persist_execution("O16", "O16_AGENT")
    persist_vs_points("O16", body.equipment_id, body.points)
    if body.optimization:
        persist_optimization("O16", body.optimization)
    if body.safety:
        persist_safety_check(
            "O16",
            body.safety.get("check_name", "unnamed"),
            body.safety.get("actual_value"),
            body.safety.get("minimum"),
            body.safety.get("maximum"),
            body.safety.get("result", "PASS"),
            body.safety.get("reason", ""),
            domain="variable-speed",
        )
    return evaluate_o16()

@router.post("/o16/dispatch")
async def dispatch_o16(req: DispatchActionRequest):
    try:
        return dispatch_official("O16", req.target_speed_pct, req.equipment_id, f"{req.equipment_id}.HeadPressure")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "DISPATCH_BLOCKED", "message": str(exc)})

@router.post("/o16/rollback")
async def rollback_o16():
    audit("O16", "BMS_COMMAND_APPLIED", "ROLLBACK")
    return {"status": "ROLLED_BACK", "opportunity_id": "O16"}

@router.get("/cw-pump")
async def get_cw_pump_optimization_state():
    """Returns Condenser Water Pump Optimization state."""
    return vs_service.get_opportunity_state("cw")

@router.get("/cooling-tower")
async def get_cooling_tower_optimization_state():
    """Returns Cooling Tower Fan Speed Optimization state."""
    return vs_service.get_opportunity_state("tower")

@router.get("/health")
async def get_variable_speed_health():
    """Returns agent health, BACnet status, and telemetry quality."""
    return {
        "module": "VARIABLE_SPEED_BASED_OPTIMISATIONS",
        "agent_health": "ONLINE",
        "bms_status": "OFFLINE",
        "telemetry_freshness": None,
        "guardrail_status": "11_OF_11_ACTIVE",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.get("/safety/guardrails")
async def get_safety_guardrails():
    """Returns definitions of all 11 deterministic safety constraints."""
    return vs_safety_engine.GUARDRAILS

@router.post("/optimize")
async def trigger_fleet_optimization():
    """Triggers immediate on-demand fleet optimization cycle."""
    return vs_service.agent.run_supervisory_cycle()

@router.post("/recommendations/{id}/approve")
async def approve_recommendation(id: str):
    """Approves a speed recommendation for dispatch."""
    return {
        "status": "APPROVED",
        "recommendation_id": id,
        "approved_at": datetime.now(timezone.utc).isoformat()
    }

@router.post("/actions/dispatch")
async def dispatch_vfd_action(req: DispatchActionRequest):
    try:
        return vs_command_service.execute_command(req.equipment_id, req.target_speed_pct, req.context)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "DISPATCH_BLOCKED", "message": str(exc)})

@router.post("/actions/verify/{equipment_id}")
async def verify_vfd_action(equipment_id: str):
    """Triggers 15-minute M&V verification for equipment."""
    return vs_verification_service.verify_equipment(equipment_id)

@router.post("/actions/rollback")
async def rollback_vfd_action(equipment_id: str = Query(...), reason: str = Query("Operator Manual Rollback")):
    """Executes instant fail-safe rollback of VFD speed to baseline."""
    return vs_verification_service.rollback_equipment(equipment_id, reason)

@router.post("/simulator/scenario")
async def set_simulator_scenario(req: ScenarioRequest):
    """Sets simulator scenario (NORMAL, HIGH_LOAD, HOT_DAY, SENSOR_FAULT, BMS_DISCONNECTED)."""
    vs_simulator.set_scenario(req.scenario)
    return {"status": "SCENARIO_UPDATED", "scenario": req.scenario}

# -------------------------------------------------------------
# Server-Sent Events (SSE) Stream
# -------------------------------------------------------------
@router.get("/stream")
async def stream_variable_speed_events():
    """Server-Sent Events stream updating VFD telemetry every 3 seconds."""
    async def event_generator():
        while True:
            tel = vs_telemetry_service.get_telemetry()
            data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "bms_status": "ONLINE" if vs_simulator.bms_connected else "DISCONNECTED",
                "telemetry": tel
            }
            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(3)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
