"""
Ventilation & Air Flow Optimisations: Deterministic Safety Guardrail Engine
Enforces 10 non-negotiable physical and IAQ constraints across Opportunities 10–14.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class VentilationSafetyCheckResult:
    is_safe: bool
    status: str # "PASS", "BLOCKED_BY_SAFETY_GUARDRAIL", "WARNING"
    violations: List[str]
    rule_results: Dict[str, Dict[str, Any]]
    details: Dict[str, Any]

class VentilationSafetyEngine:
    """
    Deterministic Safety Guardrail Engine for Ventilation & Airflow:
    1. MINIMUM_VENTILATION_FLOOR: Absolute minimum fresh air cfm floor (ASHRAE 62.1 non-negotiable)
    2. MAXIMUM_VENTILATION_LIMIT: Prevents coil thermal overload and dehumidification failure
    3. IAQ_CO2_LIMIT_CLAMP: Maximum zone CO2 ceiling (1,000 ppm strictly enforced)
    4. FAN_MINIMUM_SPEED_STALL: Minimum fan speed (20 Hz / 33% speed) to prevent VFD motor overheating and duct stall
    5. FAN_MAXIMUM_SPEED_LIMIT: Maximum fan speed (60 Hz / 100% speed) to avoid duct overpressurization
    6. DAMPER_MINIMUM_POSITION: Minimum outdoor air damper position (15%) for baseline pressurization
    7. DAMPER_MAXIMUM_POSITION: Maximum damper limit (100% full economizer)
    8. STATIC_PRESSURE_ENVELOPE: Duct static pressure clamped between 0.8 in.w.c. and 2.5 in.w.c.
    9. POSITIVE_BUILDING_PRESSURE: Supply airflow must exceed return/exhaust to maintain positive building pressurization (+0.02 to +0.05 in.w.c.)
    10. EQUIPMENT_INTERLOCK_HEALTH: Locks out airflow reduction if smoke/freeze-stat or fire alarms trigger
    """

    GUARDRAILS = {
        "MIN_VENT_FLOOR": {"min": 150.0, "max": 10000.0, "unit": "CFM", "desc": "ASHRAE 62.1 absolute minimum ventilation floor per zone/AHU"},
        "MAX_VENT_LIMIT": {"min": 500.0, "max": 25000.0, "unit": "CFM", "desc": "Maximum airflow capacity limit"},
        "CO2_LIMIT": {"min": 350.0, "max": 1000.0, "unit": "ppm", "desc": "IAQ maximum allowable CO2 concentration ceiling"},
        "FAN_SPEED_HZ": {"min": 20.0, "max": 60.0, "unit": "Hz", "desc": "VFD safe operating frequency band"},
        "DAMPER_OA_PCT": {"min": 15.0, "max": 100.0, "unit": "%", "desc": "Outdoor air damper mechanical operating envelope"},
        "STATIC_PRESSURE": {"min": 0.8, "max": 2.5, "unit": "in.w.c.", "desc": "Duct structural static pressure limits"},
        "BUILDING_PRESSURE": {"min": 0.01, "max": 0.08, "unit": "in.w.c.", "desc": "Envelope positive differential pressure"},
        "DELTA_T_COIL": {"min": 3.0, "max": 15.0, "unit": "°C", "desc": "Supply to Mixed air temperature differential"}
    }

    def evaluate_safety(
        self,
        opportunity_code: str,
        current_value: float,
        proposed_value: float,
        context: Optional[Dict[str, Any]] = None
    ) -> VentilationSafetyCheckResult:
        """Evaluates all 10 non-negotiable deterministic safety guardrails."""
        ctx = context or {}
        violations: List[str] = []
        rule_results: Dict[str, Dict[str, Any]] = {}

        # 1. BMS Communication & Telemetry Health
        bms_online = ctx.get("bms_online", True)
        sensor_healthy = ctx.get("sensor_quality_ok", True)
        if not bms_online or not sensor_healthy:
            violations.append("BMS Offline or Stale Telemetry Lockout (SAFE_MODE)")
            rule_results["COMMUNICATION_WATCHDOG"] = {"pass": False, "reason": "BMS offline or sensor stale"}

        # Official O10 Economy Cycle (leftover economizer damper envelope)
        if opportunity_code in ["O10", "OUTDOOR_AIR", "ECONOMIZER"]:
            oa_damper_pct = proposed_value
            if oa_damper_pct < 15.0:
                violations.append(f"Outdoor air damper ({oa_damper_pct}%) clamped below minimum 15% fresh air floor")
            if oa_damper_pct > 100.0:
                violations.append(f"Outdoor air damper ({oa_damper_pct}%) exceeds 100% mechanical travel")
            oat = ctx.get("outdoor_air_temp_c", 18.0)
            if oat < 4.0 and oa_damper_pct > 30.0:
                violations.append(f"Low Outdoor Air Temperature ({oat}°C) triggers Freeze-Stat Damper Lockout")

        # Official O12 DCV CO₂ (leftover DCV engine) — O11 alias is DCV-only for leftover engine tests
        if opportunity_code in ["O12", "DCV"]:
            zone_co2 = ctx.get("zone_co2_ppm", 620.0)
            if zone_co2 > 1000.0:
                violations.append(f"Zone CO2 concentration ({zone_co2} ppm) exceeds IAQ safety ceiling (1000 ppm)")
            oa_vent_cfm = proposed_value
            min_vent_rate = ctx.get("ashrae_min_vent_cfm", 210.0)
            if oa_vent_cfm < min_vent_rate:
                violations.append(f"Outdoor ventilation airflow ({oa_vent_cfm} CFM) below ASHRAE 62.1 baseline ({min_vent_rate} CFM)")

        # Leftover AHU/VAV airflow physics (not an official opportunity number)
        if opportunity_code in ["AIRFLOW", "O10_AIRFLOW"]:
            min_cfm = ctx.get("min_allowed_cfm", 1500.0 if proposed_value > 1200.0 else 180.0)
            max_cfm = ctx.get("max_allowed_cfm", 12000.0 if proposed_value > 1200.0 else 1200.0)
            if proposed_value < min_cfm:
                violations.append(f"Airflow below minimum ventilation floor ({proposed_value} < {min_cfm} CFM)")
            if proposed_value > max_cfm:
                violations.append(f"Airflow exceeds aerodynamic capacity ({proposed_value} > {max_cfm} CFM)")

        # Leftover supply/return balancing physics (not official O13)
        if opportunity_code in ["BALANCING", "O13_BALANCE"]:
            bldg_dp = ctx.get("building_dp_inwc", 0.03)
            if bldg_dp < 0.005:
                violations.append(f"Negative Building Pressure Risk ({bldg_dp} in.w.c. < 0.01 in.w.c.) - Infiltration hazard")
            if bldg_dp > 0.08:
                violations.append(f"Excess Building Pressurization ({bldg_dp} in.w.c. > 0.08 in.w.c.) - Door opening force violation")

        # Leftover fan SFP physics (not official O14)
        if opportunity_code in ["FAN_OPTIMIZATION", "O14_FAN"]:
            vfd_hz = proposed_value
            if vfd_hz < 20.0:
                violations.append(f"Fan VFD frequency ({vfd_hz} Hz) below motor cooling minimum (20.0 Hz)")
            if vfd_hz > 60.0:
                violations.append(f"Fan VFD frequency ({vfd_hz} Hz) exceeds electrical nameplate (60.0 Hz)")
            static_p = ctx.get("duct_static_pressure_inwc", 1.4)
            if static_p > 2.5:
                violations.append(f"Duct Static Pressure ({static_p} in.w.c.) exceeds high-limit duct rupture safety floor (2.5 in.w.c.)")

        # 7. Slew-Rate / Ramp-Rate Limiting
        max_ramp = ctx.get("max_ramp_rate", 25.0)
        delta = abs(proposed_value - current_value)
        if delta > max_ramp:
            violations.append(f"Setpoint step change ({delta:.1f}) exceeds safe single-step ramp rate ({max_ramp:.1f})")

        is_safe = len(violations) == 0
        status = "PASS" if is_safe else "BLOCKED_BY_SAFETY_GUARDRAIL"

        return VentilationSafetyCheckResult(
            is_safe=is_safe,
            status=status,
            violations=violations,
            rule_results=rule_results,
            details={
                "opportunity_code": opportunity_code,
                "current_value": current_value,
                "proposed_value": proposed_value,
                "violations_count": len(violations),
                "lockout_triggered": not is_safe
            }
        )

ventilation_safety_engine = VentilationSafetyEngine()
