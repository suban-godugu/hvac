"""Official O13 DCV-CO. Safety ventilation always outranks energy savings."""
from __future__ import annotations

from typing import Any, Dict

from backend.agents.official_opportunities._common import agent_envelope, check, missing, num, text

REQUIRED = ["CO_PPM"]
CO_ALARM_PPM = 50.0
CO_WARN_PPM = 25.0
CO_TARGET_PPM = 15.0


def evaluate_dcv_co(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    absent = missing(telemetry, REQUIRED)
    if absent:
        return agent_envelope(
            "O13",
            False,
            recommendation="BLOCKED",
            reason="Missing CO concentration telemetry.",
            extra={"missing_points": absent},
        )

    co = num(telemetry, "CO_PPM")
    trend = text(telemetry, "CO_TREND")
    zone = text(telemetry, "ZONE_ID") or "PARK"
    fan_state = num(telemetry, "FAN_STATE")
    fan_speed = num(telemetry, "FAN_SPEED")
    damper = num(telemetry, "DAMPER_PCT")
    airflow = num(telemetry, "AIRFLOW_CFM")
    occ = num(telemetry, "OCCUPANCY")

    alarm = co is not None and co >= CO_ALARM_PPM
    warn = co is not None and co >= CO_WARN_PPM
    rec_speed = 25.0
    rec_damper = 20.0
    rec = "REDUCE"
    reason = "CO is below warning; ventilation can track demand."
    conf = 0.7
    energy = 1.2

    if alarm:
        rec_speed = 100.0
        rec_damper = 100.0
        rec = "MAX_VENTILATION"
        reason = f"CO {co:.1f} ppm exceeds safety limit {CO_ALARM_PPM:.0f} ppm. Energy optimization suppressed."
        conf = 0.99
        energy = 0.0
    elif warn:
        rec_speed = 80.0
        rec_damper = 70.0
        rec = "INCREASE"
        reason = f"CO {co:.1f} ppm above warning {CO_WARN_PPM:.0f} ppm. Increase exhaust."
        conf = 0.93
        energy = 0.2
    elif co is not None and co > CO_TARGET_PPM:
        rec_speed = 45.0
        rec_damper = 40.0
        rec = "TRIM"
        reason = f"CO {co:.1f} ppm above target {CO_TARGET_PPM:.0f} ppm."
        conf = 0.82
        energy = 0.6

    checks = [
        check("CO Sensor Present", True, "CO concentration available", co, None, None),
        check(
            "CO Safety Limit",
            True,
            "CO alarm — maximum ventilation commanded" if alarm else "CO below alarm threshold",
            co,
            None,
            CO_ALARM_PPM,
        ),
        check("Fan Available", fan_state is None or fan_state >= 0, "Fan command path present", fan_state, 0, None),
    ]
    current = {
        "co_ppm": co,
        "co_trend": trend,
        "zone": zone,
        "ventilation_status": "ALARM" if alarm else ("HIGH" if warn else "NORMAL"),
        "fan_state": fan_state,
        "fan_speed": fan_speed,
        "damper_pct": damper,
        "airflow_cfm": airflow,
        "occupancy_proxy": occ,
        "current_ventilation_pct": fan_speed if fan_speed is not None else damper,
    }
    optimized = {
        "recommended_ventilation_pct": rec_speed,
        "recommended_fan_speed_pct": rec_speed,
        "recommended_damper_pct": rec_damper,
    }
    return agent_envelope(
        "O13",
        True,
        current_state=current,
        optimized_state=optimized,
        recommendation=rec,
        reason=reason,
        confidence=conf,
        energy_impact=energy if not alarm else 0.0,
        safety_checks=checks,
        extra={"current_value": co, "optimized_value": rec_speed},
    )
