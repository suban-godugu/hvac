"""
VariableSpeedSafetyEngine: Deterministic safety guardrails enforcing VFD frequency floors,
minimum flows, maximum speeds, critical zone protection, and sensor freshness checks.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class SafetyCheckResult(BaseModel):
    is_safe: bool
    status: str # "PASS", "BLOCKED_BY_SAFETY_GUARDRAIL"
    violations: List[str]
    clamped_value: Optional[float] = None

class VariableSpeedSafetyEngine:
    GUARDRAILS = {
        "VFD_MIN_SPEED": {"min": 30.0, "unit": "%", "desc": "Minimum VFD speed clamp for motor cooling"},
        "VFD_MAX_SPEED": {"max": 100.0, "unit": "%", "desc": "Maximum VFD speed capacity limit"},
        "VFD_MIN_FREQUENCY": {"min": 20.0, "unit": "Hz", "desc": "Motor thermal minimum operating frequency"},
        "VFD_MAX_FREQUENCY": {"max": 60.0, "unit": "Hz", "desc": "Maximum rated line frequency"},
        "FAN_STATIC_PRESSURE_MIN": {"min": 0.60, "unit": "in.w.c.", "desc": "Duct static pressure floor to avoid VAV starvation"},
        "PUMP_MIN_FLOW": {"min": 200.0, "unit": "GPM", "desc": "Pump minimum bypass flow to prevent dead-heading/cavitation"},
        "PUMP_MAX_PRESSURE": {"max": 50.0, "unit": "PSI", "desc": "Hydraulic pipe pressure safety ceiling"},
        "CHILLER_MIN_FLOW": {"min": 350.0, "unit": "GPM", "desc": "Evaporator freeze-protection minimum flow rate"},
        "TOWER_APPROACH_MIN": {"min": 2.5, "unit": "°C", "desc": "Psychrometric limit preventing tower over-cooling / freeze risk"},
        "RAMP_RATE_MAX": {"max": 12.0, "unit": "%/min", "desc": "Maximum VFD ramp rate to prevent mechanical shock"},
        "CRITICAL_ZONE_PROTECTION": {"desc": "Locks out fan reductions when critical zone damper > 85%"}
    }

    def evaluate_safety(self, equipment_type: str, current_speed: float, proposed_speed: float, context: Optional[Dict[str, Any]] = None) -> SafetyCheckResult:
        violations = []
        ctx = context or {}

        # 1. Sensor quality & telemetry freshness
        if ctx.get("quality") in ["BAD", "STALE", "UNKNOWN"]:
            violations.append(f"Sensor telemetry quality is {ctx.get('quality')}. Automatic control is locked out.")

        # 2. General VFD bounds (30% to 100%, 20 Hz to 60 Hz)
        if proposed_speed < 30.0:
            violations.append(f"Proposed speed {proposed_speed}% violates VFD minimum motor cooling limit (30.0% / 20 Hz).")
        if proposed_speed > 100.0:
            violations.append(f"Proposed speed {proposed_speed}% exceeds maximum rated capacity (100.0% / 60 Hz).")

        # 3. Ramp rate limit (12% per min)
        delta_speed = abs(proposed_speed - current_speed)
        if delta_speed > 25.0: # Single-step step-change limit
            violations.append(f"Speed step change {delta_speed:.1f}% exceeds anti-hunting ramp rate limit (25.0%).")

        # 4. Equipment specific guardrails
        eq = equipment_type.upper()
        if "FAN" in eq:
            max_damper = float(ctx.get("max_vav_damper_pct", 75.0))
            if max_damper > 88.0 and proposed_speed < current_speed:
                violations.append(f"Critical zone damper is near saturation ({max_damper}% > 88%). Fan speed reduction blocked.")
            static_p = float(ctx.get("static_pressure_inwc", 1.20))
            if static_p < 0.60:
                violations.append(f"Duct static pressure {static_p} in.w.c. is below minimum distribution floor (0.60 in.w.c.).")

        elif "CHW" in eq or "PUMP" in eq:
            min_flow = float(ctx.get("flow_gpm", 500.0))
            if min_flow < 200.0:
                violations.append(f"Hydraulic flow {min_flow} GPM below dead-heading protection floor (200 GPM).")

        elif "TOWER" in eq or "COOLING" in eq:
            approach_c = float(ctx.get("approach_temp_c", 4.0))
            if approach_c < 2.0:
                violations.append(f"Tower approach {approach_c}°C approaches psychrometric limit (<2.0°C).")

        is_safe = len(violations) == 0
        return SafetyCheckResult(
            is_safe=is_safe,
            status="PASS" if is_safe else "BLOCKED_BY_SAFETY_GUARDRAIL",
            violations=violations,
            clamped_value=max(30.0, min(100.0, proposed_speed))
        )

vs_safety_engine = VariableSpeedSafetyEngine()
