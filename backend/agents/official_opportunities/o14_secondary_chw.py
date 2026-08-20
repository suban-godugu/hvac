"""Official O14: Optimised Secondary Chilled Water Pumping (differential pressure reset).

SOURCE: NSW OEH / AIRAH HVAC Optimisation Guide (OEH 2015/0317), Opportunity 14.

Guide strategy (not invented):
- Applies to secondary CHW (SCHW) systems with 2-port modulating valves (variable flow).
- Typical waste: constant DP setpoint selected for peak design flow.
- Reset: when all CHW valves are less than 95% open, reduce SCHW pump speed
  incrementally (CHW pressure setpoint reset) so the most-open valve is held at 95%.
- Deliver CHW at the lowest possible pressure while still satisfying all users.
- SCHW does not pump through chillers (primary pumps do).
- Guide states up to 30% energy reduction on SCHW pumps as typical potential,
  not a verified measurement.

Numeric trim step, min/max DP, min/max speed, and staging thresholds are
CONFIGURABLE — the guide does not specify those magnitudes.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.agents.official_opportunities._common import agent_envelope, check, missing, num, text
from backend.services.hvac_safety_contract import classify_telemetry, is_demo_source, is_safe_mode, production_bms_connected

ENGINE_VERSION = "o14-dp-reset-1.0"
GUIDE_VALVE_TARGET_PCT = 95.0
GUIDE_SAVINGS_POTENTIAL_NOTE = "Guide states up to 30% energy reduction on SCHW pumps (typical potential, not verified)."

REQUIRED = ["INDEX_DP", "MOST_OPEN_VALVE_PCT"]


def _cfg(config: Dict[str, Any], key: str, default=None):
    if config.get(key) is not None:
        return config[key]
    return default


def _gate(name: str, ok: bool, reason: str, actual=None, minimum=None, maximum=None) -> Dict[str, Any]:
    return check(name, ok, reason, actual, minimum, maximum)


def evaluate_secondary_chw(telemetry: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = config or {}
    absent = missing(telemetry, REQUIRED)
    if absent:
        return agent_envelope(
            "O14",
            False,
            recommendation="HOLD",
            reason=f"Missing required SCHW telemetry: {', '.join(absent)}. "
            "Guide minimum information: index-run CHW differential pressure and CHW valve positions.",
            extra={"missing_points": absent, "engine_version": ENGINE_VERSION},
        )

    dp = num(telemetry, "INDEX_DP", "DP", "DIFFERENTIAL_PRESSURE")
    dp_sp = num(telemetry, "DP_SETPOINT", "DP_SP")
    most_open = num(telemetry, "MOST_OPEN_VALVE_PCT", "VALVE_MAX_PCT")
    avg_valve = num(telemetry, "VALVE_AVG_PCT")
    flow = num(telemetry, "FLOW", "CHW_FLOW")
    speed = num(telemetry, "SPEED_PCT", "PUMP_SPEED_PCT")
    power = num(telemetry, "POWER_KW", "PUMP_POWER_KW")
    chwst = num(telemetry, "CHWST", "SUPPLY_TEMP")
    chwrt = num(telemetry, "CHWRT", "RETURN_TEMP")
    load = num(telemetry, "LOAD_PCT", "SYSTEM_LOAD")
    cooling_call = num(telemetry, "COOLING_CALL")
    pumps_running = num(telemetry, "PUMPS_RUNNING")
    quality = (text(telemetry, "quality", "QUALITY") or telemetry.get("quality") or "UNKNOWN").upper()
    source = text(telemetry, "source", "SOURCE") or telemetry.get("source")
    classified = classify_telemetry(
        {"quality": quality, "age_seconds": telemetry.get("age_seconds") or telemetry.get("ageSeconds"), "source": source},
        source,
    )

    target_valve = float(_cfg(cfg, "most_open_valve_target_pct", GUIDE_VALVE_TARGET_PCT))
    trim = _cfg(cfg, "dp_setpoint_trim", 0.5)
    trim_unit = _cfg(cfg, "dp_setpoint_trim_unit", telemetry.get("dp_unit") or "psi")
    speed_trim = _cfg(cfg, "speed_trim_pct", 2.0)
    min_speed = _cfg(cfg, "min_pump_speed_pct", None)
    max_speed = _cfg(cfg, "max_pump_speed_pct", None)
    min_dp = _cfg(cfg, "min_dp", None)
    max_dp = _cfg(cfg, "max_dp", None)
    min_flow = _cfg(cfg, "min_flow", None)
    max_flow = _cfg(cfg, "max_flow", None)
    max_step = _cfg(cfg, "max_speed_step_pct", 25.0)
    mode = str(_cfg(cfg, "control_mode", "ADVISORY") or "ADVISORY").upper()

    rec = "HOLD"
    rec_state = "ADVISORY"
    recommended_dp_sp = dp_sp
    recommended_speed = speed
    reason_parts: List[str] = []

    if cooling_call is not None and cooling_call <= 0:
        rec = "HOLD"
        reason_parts.append("No cooling call — SCHW pumps should remain disabled (guide: cooling call enables SCHW pumps).")
    elif most_open is not None and most_open < target_valve:
        rec = "RESET_DP"
        if dp_sp is not None and trim is not None:
            recommended_dp_sp = round(float(dp_sp) - float(trim), 3)
        if speed is not None and speed_trim is not None:
            recommended_speed = round(float(speed) - float(speed_trim), 2)
        reason_parts.append(
            f"Most-open CHW valve is {most_open:.1f}% (< {target_valve:.0f}%). "
            "Guide strategy: reduce SCHW pump speed incrementally (CHW pressure setpoint reset) "
            f"to hold the most-open valve at {target_valve:.0f}% so CHW is delivered at the lowest "
            "pressure that still satisfies all users."
        )
    elif most_open is not None and most_open >= 100.0:
        rec = "HOLD"
        reason_parts.append(
            "At least one CHW valve is 100% open. Guide tip: check CHW balancing for valves that "
            "are 100% open more often than others. No invented increase formula is applied."
        )
    elif most_open is not None:
        rec = "HOLD"
        reason_parts.append(
            f"Most-open CHW valve is {most_open:.1f}%, at or above the guide target of {target_valve:.0f}%. "
            "No further DP reset this cycle."
        )

    if recommended_dp_sp is not None and min_dp is not None and recommended_dp_sp < float(min_dp):
        rec = "REJECT"
        reason_parts.append(f"Recommended DP setpoint {recommended_dp_sp} is below configured minimum DP {min_dp}.")
    if recommended_dp_sp is not None and max_dp is not None and recommended_dp_sp > float(max_dp):
        rec = "REJECT"
        reason_parts.append(f"Recommended DP setpoint {recommended_dp_sp} exceeds configured maximum DP {max_dp}.")
    if recommended_speed is not None and min_speed is not None and recommended_speed < float(min_speed):
        rec = "REJECT"
        reason_parts.append("Recommended speed is below configured minimum pump speed.")
    if recommended_speed is not None and max_speed is not None and recommended_speed > float(max_speed):
        rec = "REJECT"
        reason_parts.append("Recommended speed exceeds configured maximum pump speed.")
    if speed is not None and recommended_speed is not None and max_step is not None:
        if abs(float(recommended_speed) - float(speed)) > float(max_step):
            rec = "REJECT"
            reason_parts.append("Recommended speed step exceeds configured rate-of-change limit.")

    predicted_power = None
    predicted_class = None
    if power is not None and speed and recommended_speed and speed > 0:
        # Appendix D affinity: power varies approximately with speed cubed (guide).
        predicted_power = round(float(power) * ((float(recommended_speed) / float(speed)) ** 3), 3)
        predicted_class = "PREDICTED"
    predicted_delta = None
    if predicted_power is not None and power is not None:
        predicted_delta = round(float(power) - predicted_power, 3)

    demo = classified.get("demo") or is_demo_source(source)
    bms_ok = production_bms_connected()
    safe_mode = is_safe_mode()
    tel_ok = classified.get("status") in ("LIVE",) and classified.get("usable")
    if classified.get("status") == "STALE":
        rec = "HOLD"
        reason_parts.append("Telemetry is STALE — HOLD (no write).")
    if classified.get("status") == "BAD":
        rec = "HOLD"
        reason_parts.append("Telemetry quality is BAD — HOLD (no write).")
    if demo:
        rec_state = "REJECTED" if rec == "RESET_DP" else rec_state
        reason_parts.append("Source is SIMULATION/DEMO — production writes are rejected.")
    if safe_mode:
        rec = "HOLD" if rec == "RESET_DP" else rec
        reason_parts.append("SAFE_MODE is active — equipment writes are blocked.")

    engineering = [
        _gate("Telemetry Fresh", classified.get("status") not in ("STALE", "MISSING", "BAD"), f"Classified {classified.get('status')}", classified.get("age_seconds")),
        _gate("Data Quality GOOD", quality in ("GOOD", "LIVE") and classified.get("status") not in ("BAD",), f"quality={quality}"),
        _gate("Pump Available", cooling_call is None or cooling_call > 0, "Cooling call / enable", cooling_call),
        _gate("DP Within Limits", (min_dp is None or (dp is not None and dp >= float(min_dp))) and (max_dp is None or (dp is not None and dp <= float(max_dp))), "Configured DP envelope (optional)", dp, min_dp, max_dp),
        _gate("Flow Within Limits", (min_flow is None or (flow is not None and flow >= float(min_flow))) and (max_flow is None or (flow is not None and flow <= float(max_flow))), "Configured flow envelope (optional)", flow, min_flow, max_flow),
        _gate("Rate-of-change Valid", not (speed is not None and recommended_speed is not None and max_step is not None and abs(float(recommended_speed) - float(speed)) > float(max_step)), "Configured speed step", abs(float(recommended_speed) - float(speed)) if speed is not None and recommended_speed is not None else None, None, max_step),
        _gate("Engineering Limits Valid", rec != "REJECT", "Config min/max DP and speed"),
    ]
    write_gates = [
        _gate("BMS Connected", bms_ok, "Production BMS connected" if bms_ok else "BMS offline"),
        _gate("No SAFE_MODE", not safe_mode, "SAFE_MODE off" if not safe_mode else "SAFE_MODE on"),
        _gate("Source not SIMULATION", not demo, f"source={source or 'UNKNOWN'}"),
        _gate("No conflicting command", True, "Checked at apply"),
    ]
    gates = engineering + write_gates
    eng_pass = all(g["result"] == "PASS" for g in engineering)
    write_pass = all(g["result"] == "PASS" for g in write_gates)
    overall = "SAFE TO APPLY" if rec == "RESET_DP" and eng_pass and write_pass and tel_ok and not demo and not safe_mode else "HOLD — SAFETY CONDITION NOT MET"

    if rec == "REJECT":
        rec_state = "REJECTED"
        safety_status = "REJECT"
    elif not eng_pass or rec != "RESET_DP":
        rec_state = "ADVISORY" if mode == "ADVISORY" else "HOLD"
        if safe_mode:
            rec_state = "REJECTED"
        safety_status = "HOLD"
    elif not write_pass:
        rec_state = "ADVISORY"
        safety_status = "HOLD"
    elif mode == "APPROVAL_REQUIRED":
        rec_state = "APPROVAL_REQUIRED"
        safety_status = "PASS"
    elif mode == "AUTO" and write_pass and tel_ok and not demo:
        rec_state = "READY TO APPLY"
        safety_status = "PASS"
    else:
        rec_state = "ADVISORY"
        safety_status = "PASS" if eng_pass else "HOLD"

    current = {
        "index_dp": dp,
        "dp_setpoint": dp_sp,
        "most_open_valve_pct": most_open,
        "avg_valve_pct": avg_valve,
        "flow": flow,
        "pump_speed_pct": speed,
        "pump_power_kw": power,
        "supply_temperature": chwst,
        "return_temperature": chwrt,
        "load_pct": load,
        "cooling_call": cooling_call,
        "pumps_running": pumps_running,
        "dp_unit": trim_unit,
    }
    optimized = {
        "recommended_dp_setpoint": recommended_dp_sp,
        "recommended_speed_pct": recommended_speed,
        "most_open_valve_target_pct": target_valve,
        "target_source": "SOURCE-GUIDE",
        "dp_trim": trim,
        "dp_trim_source": "CONFIGURABLE_DEFAULT",
        "speed_trim_pct": speed_trim,
        "speed_trim_source": "CONFIGURABLE_DEFAULT",
    }

    extra = {
        "current_value": dp_sp if dp_sp is not None else dp,
        "optimized_value": recommended_dp_sp,
        "unit": trim_unit,
        "engine_version": ENGINE_VERSION,
        "recommendation_state": rec_state,
        "control_mode": mode,
        "overall_safety": overall,
        "classified_telemetry": classified,
        "energy_impact_class": predicted_class,
        "predicted_power_kw": predicted_power,
        "predicted_power_delta_kw": predicted_delta,
        "verified_savings_kw": None,
        "applied_savings_kw": None,
        "guide_potential_note": GUIDE_SAVINGS_POTENTIAL_NOTE,
        "why": {
            "current_operating_condition": f"Index DP={dp}, DP setpoint={dp_sp}, most-open valve={most_open}%, speed={speed}%",
            "detected_demand": f"Most-open CHW valve {most_open}% vs guide target {target_valve}%",
            "control_relationship": "SCHW VSD maintains index-run differential pressure; reset DP setpoint to keep most-open 2-port valve at 95%.",
            "active_engineering_limits": {"min_dp": min_dp, "max_dp": max_dp, "min_speed": min_speed, "max_speed": max_speed, "max_speed_step_pct": max_step},
            "safety_gates": [g["check_name"] + "=" + g["result"] for g in gates],
            "reason_for_change": " ".join(reason_parts),
        },
    }

    envelope = agent_envelope(
        "O14",
        True,
        current_state=current,
        optimized_state=optimized,
        recommendation=rec,
        reason=" ".join(reason_parts) or "No recommendation.",
        confidence=0.8 if rec == "RESET_DP" and eng_pass else (0.55 if rec == "HOLD" else 0.3),
        energy_impact=predicted_delta,
        safety_checks=engineering,
        extra=extra,
    )
    envelope["safety_checks"] = gates
    envelope["write_gates"] = write_gates
    envelope["safety_status"] = safety_status
    envelope["live"] = (not demo) and classified.get("status") == "LIVE"
    if rec == "REJECT":
        envelope["recommendation"] = "REJECT"
        envelope["status"] = "REJECTED"
    if not envelope["live"]:
        envelope["status"] = "AWAITING_TELEMETRY" if classified.get("status") in ("MISSING", None) else classified.get("status")
        envelope["agent_status"] = "DEGRADED"
        if demo:
            envelope["status"] = "SIMULATION"
    return envelope
