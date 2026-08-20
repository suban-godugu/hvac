"""
PlantControlController: FastAPI Router exposing all REST endpoints for
Plant Control Parameter Optimizations:
- O5: Duct Static Pressure Reset
- O6–8: Unified Temperature Reset (HHW, CHW, CW modes)
- O9: Electronic Expansion Valve Retrofit Assessment
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from backend.services.plant_control_service import plant_control_service
from backend.services.plant_control_telemetry_service import plant_control_telemetry_service
from backend.services.plant_control_command_service import plant_control_command_service
from backend.services.plant_control_verification_service import plant_control_verification_service
from backend.services.plant_control_safety_service import plant_control_safety_service
from backend.agents.plant_control.o6_8_temperature_reset.engine import o6_8_agent
from backend.services.plant_control_provenance import stamp_plant_provenance


def _reset_opportunity(mode: str) -> str:
    r_type = (mode or "CHW").upper().replace("_RESET", "")
    if r_type == "HHW":
        return "O6"
    if r_type == "CW":
        return "O8"
    return "O7"

router = APIRouter(prefix="/api/agents/plant-control", tags=["Plant Control Parameter Optimizations"])

class CommandDispatchRequest(BaseModel):
    target_setpoint: float
    reset_type: Optional[str] = "CHW"
    context: Optional[Dict[str, Any]] = None

# -------------------------------------------------------------
# High-Level Plant Control Fleet Endpoints
# -------------------------------------------------------------
@router.get("/state")
async def get_plant_control_state():
    """Returns fleet-wide optimization state, total kW shed, and opportunity status."""
    return plant_control_service.get_dashboard_state()

@router.get("/telemetry")
async def get_all_plant_telemetry():
    """Returns standardized telemetry points across all plant control equipment."""
    return plant_control_telemetry_service.get_all_points()

@router.get("/activity")
async def get_plant_activity(limit: int = Query(20, ge=1, le=100)):
    """Returns audit log history of plant control actions, safety checks, and verifications."""
    return plant_control_service.get_activity_log(limit=limit)

@router.get("/safety/guardrails")
async def get_safety_guardrails():
    """Returns definitions of all 10 deterministic safety guardrails."""
    return plant_control_safety_service.get_guardrail_definitions()

# -------------------------------------------------------------
# Opportunity 5: Duct Static Pressure Reset
# -------------------------------------------------------------
@router.get("/o5/state")
async def get_o5_state():
    """Returns live O5 Duct Static Pressure Reset state and candidate evaluation."""
    return plant_control_service.get_o5_state()

@router.get("/o5/telemetry")
async def get_o5_telemetry():
    """Returns all standardized telemetry points for AHUs and downstream VAV boxes."""
    return plant_control_telemetry_service.get_opportunity_telemetry("O5")

@router.get("/o5/decision")
async def get_o5_decision():
    """Returns active candidate recommendation and fan power savings prediction."""
    state = plant_control_service.get_o5_state()
    return {
        "opportunity_code": "O5",
        "current_setpoint": state["current_setpoint"],
        "optimized_setpoint": state["optimized_setpoint"],
        "pressure_reduction": state["pressure_reduction"],
        "fan_power_shed_kw": state["power_shed_kw"],
        "confidence": state["confidence"],
        "safety_status": state["safety_status"],
        "decision": state["decision"]
    }

@router.get("/o5/history")
async def get_o5_history():
    """Returns 24-hour historical time-series for duct static pressure and fan power."""
    return plant_control_service.get_o5_history()

@router.post("/o5/command")
async def dispatch_o5_command(req: CommandDispatchRequest):
    """Dispatches an optimized duct static pressure setpoint via BMS Gateway."""
    try:
        return plant_control_command_service.execute_command("O5", req.target_setpoint, req.context)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "DISPATCH_BLOCKED", "message": str(exc)})

@router.post("/o5/verify")
async def verify_o5_response():
    """Runs 15-minute M&V verification for O5 static pressure reset."""
    return plant_control_verification_service.verify_opportunity("O5")

@router.post("/o5/rollback")
async def rollback_o5():
    """Rolls back O5 static pressure setpoint to design baseline."""
    return plant_control_verification_service.rollback_opportunity("O5", "Manual Operator Rollback")

# -------------------------------------------------------------
# Opportunity 6–8: Unified Temperature Reset (HHW, CHW, CW)
# -------------------------------------------------------------
@router.get("/o6-8/state")
@router.get("/temperature-reset/state")
async def get_o6_8_state(mode: str = Query("CHW", description="Reset Mode: HHW, CHW, or CW")):
    """Returns normalized Temperature Reset state for selected mode (HHW, CHW, or CW)."""
    return stamp_plant_provenance(o6_8_agent.optimize_mode(mode), _reset_opportunity(mode))

@router.get("/o6-8/modes")
@router.get("/temperature-reset/modes")
async def get_o6_8_all_modes():
    """Returns summary for all 3 temperature reset modes simultaneously."""
    return o6_8_agent.get_all_modes_summary()

@router.get("/o6-8/telemetry")
@router.get("/temperature-reset/telemetry")
async def get_o6_8_telemetry(mode: str = Query("CHW")):
    """Returns telemetry points for selected reset mode loop."""
    r_type = mode.upper().replace("_RESET", "")
    opp_code = "O6" if r_type == "HHW" else ("O8" if r_type == "CW" else "O7")
    return plant_control_telemetry_service.get_opportunity_telemetry(opp_code)

@router.get("/o6-8/decision")
@router.get("/temperature-reset/decision")
async def get_o6_8_decision(mode: str = Query("CHW")):
    """Returns normalized decision record for selected reset mode."""
    res = o6_8_agent.optimize_mode(mode)
    return {
        "opportunity_id": "O6_8",
        "reset_type": res["reset_type"],
        "current_setpoint": res["current_setpoint"],
        "optimized_setpoint": res["optimized_setpoint"],
        "baseline_setpoint": res["baseline_setpoint"],
        "power_impact": res["power_impact"],
        "efficiency_impact": res["efficiency_impact"],
        "confidence": res["confidence"],
        "safety_status": res["status"],
        "reason": res["reason"]
    }

@router.post("/o6-8/command")
@router.post("/temperature-reset/command")
async def dispatch_o6_8_command(req: CommandDispatchRequest):
    """Dispatches a temperature reset setpoint for HHW, CHW, or CW."""
    r_type = (req.reset_type or "CHW").upper().replace("_RESET", "")
    opp_code = "O6" if r_type == "HHW" else ("O8" if r_type == "CW" else "O7")
    try:
        return plant_control_command_service.execute_command(opp_code, req.target_setpoint, req.context)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "DISPATCH_BLOCKED", "message": str(exc)})

@router.post("/o6-8/verify")
@router.post("/temperature-reset/verify")
async def verify_o6_8_response(mode: str = Query("CHW")):
    """Runs 15-minute M&V verification for temperature reset mode."""
    r_type = mode.upper().replace("_RESET", "")
    opp_code = "O6" if r_type == "HHW" else ("O8" if r_type == "CW" else "O7")
    return plant_control_verification_service.verify_opportunity(opp_code)

@router.post("/o6-8/rollback")
@router.post("/temperature-reset/rollback")
async def rollback_o6_8(mode: str = Query("CHW")):
    """Rolls back temperature reset to baseline design setpoint."""
    r_type = mode.upper().replace("_RESET", "")
    opp_code = "O6" if r_type == "HHW" else ("O8" if r_type == "CW" else "O7")
    return plant_control_verification_service.rollback_opportunity(opp_code, f"Rollback for {mode} Temperature Reset")

# -------------------------------------------------------------
# Backward-Compatibility Routes for O6, O7, O8
# -------------------------------------------------------------
@router.get("/o6/state")
async def get_o6_state():
    return stamp_plant_provenance(o6_8_agent.optimize_mode("HHW"), "O6")

@router.get("/o6/telemetry")
async def get_o6_telemetry():
    return plant_control_telemetry_service.get_opportunity_telemetry("O6")

@router.get("/o6/decision")
async def get_o6_decision():
    return get_o6_8_decision("HHW")

@router.get("/o6/history")
async def get_o6_history():
    return plant_control_service.get_o6_history()

@router.get("/o7/state")
async def get_o7_state():
    return stamp_plant_provenance(o6_8_agent.optimize_mode("CHW"), "O7")

@router.get("/o7/telemetry")
async def get_o7_telemetry():
    return plant_control_telemetry_service.get_opportunity_telemetry("O7")

@router.get("/o7/decision")
async def get_o7_decision():
    return get_o6_8_decision("CHW")

@router.get("/o7/history")
async def get_o7_history():
    return plant_control_service.get_o7_history()

@router.get("/o8/state")
async def get_o8_state():
    return stamp_plant_provenance(o6_8_agent.optimize_mode("CW"), "O8")

@router.get("/o8/telemetry")
async def get_o8_telemetry():
    return plant_control_telemetry_service.get_opportunity_telemetry("O8")

@router.get("/o8/decision")
async def get_o8_decision():
    return get_o6_8_decision("CW")

@router.get("/o8/history")
async def get_o8_history():
    return plant_control_service.get_o8_history()

# -------------------------------------------------------------
# Opportunity 9: Electronic Expansion Valve Retrofit
# -------------------------------------------------------------
@router.get("/o9/assessment")
@router.get("/o9/state")
async def get_o9_assessment():
    """Returns comprehensive thermodynamic and economic retrofit feasibility assessment."""
    return plant_control_service.get_o9_assessment()

@router.get("/o9/telemetry")
async def get_o9_telemetry():
    """Returns live suction, superheat, and evaporating state telemetry."""
    return plant_control_telemetry_service.get_opportunity_telemetry("O9")

@router.get("/o9/history")
async def get_o9_history():
    """Returns superheat stability and hunting amplitude comparison curves."""
    return plant_control_service.get_o9_history()

@router.post("/o9/recalculate")
async def recalculate_o9_feasibility(utility_rate: float = Query(0.12)):
    """Recalculates capital payback and ROI based on updated utility rates."""
    from backend.agents.plant_control.o9_electronic_expansion_valve.engine import o9_agent
    return o9_agent.evaluate_retrofit_feasibility(utility_rate_per_kwh=utility_rate)
