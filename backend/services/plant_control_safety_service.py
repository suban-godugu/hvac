"""
PlantControlSafetyService: Validates all candidate setpoints against
10 deterministic safety guardrails before allowing BMS dispatch.
"""
from typing import Dict, Any, List
from backend.agents.plant_control.safety_engine import plant_control_safety

class PlantControlSafetyService:
    def __init__(self):
        self.safety_engine = plant_control_safety

    def validate_candidate(self, opportunity: str, proposed_value: float, context: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the 10 deterministic safety guardrails against a proposed setpoint."""
        opp = opportunity.upper()
        current_val = float(context.get("current_value", proposed_value))
        telemetry = context.get("telemetry", {})
        
        res = self.safety_engine.evaluate_safety(
            opportunity_code=opp,
            current_value=current_val,
            proposed_value=float(proposed_value),
            telemetry=telemetry,
            telemetry_age_sec=float(context.get("telemetry_age_sec", 4.0)),
            is_bms_connected=True
        )
        
        is_passed = res.get("status") == "PASS"
        return {
            "opportunity": opp,
            "proposed_value": proposed_value,
            "passed": is_passed,
            "overall_status": res.get("status", "PASS"),
            "violations": [res.get("reason")] if not is_passed else [],
            "guardrail_checks": res.get("checks", []),
            "clamped_value": res.get("clamped_value", proposed_value)
        }

    def get_guardrail_definitions(self) -> List[Dict[str, str]]:
        return [
            {"id": "G01", "name": "Freeze Protection", "description": "Guarantees water temperatures remain above freeze floor (>4.0°C)."},
            {"id": "G02", "name": "Overheat Protection", "description": "Guarantees HHW delivery does not exceed boiler design maximum (<85.0°C)."},
            {"id": "G03", "name": "Minimum Static Pressure Floor", "description": "Maintains minimum duct static pressure (>=0.8 in.w.c.) to avoid VAV starvation."},
            {"id": "G04", "name": "Maximum Duct Static Pressure", "description": "Prevents duct over-pressurization (<=2.2 in.w.c.) to protect seals and dampers."},
            {"id": "G05", "name": "Maximum Rate of Change", "description": "Clamps setpoint changes to prevent pneumatic shock and hunt."},
            {"id": "G06", "name": "Anti-Hunting Dwell Time", "description": "Enforces 15-minute dwell interval between consecutive resets."},
            {"id": "G07", "name": "Sensor Quality Check", "description": "Verifies freshness, range, and telemetry validity before evaluating resets."},
            {"id": "G08", "name": "Critical Zone Airflow Authority", "description": "Ensures no critical zone drops below 85% required design CFM."},
            {"id": "G09", "name": "Chiller Minimum Lift Floor", "description": "Guarantees chiller refrigerant lift exceeds 12.0°C to prevent surge."},
            {"id": "G10", "name": "Cooling Coil Valve Saturation", "description": "Ensures terminal and AHU valve demand does not saturate (>92%)."}
        ]

plant_control_safety_service = PlantControlSafetyService()
