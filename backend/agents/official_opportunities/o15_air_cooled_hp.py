"""Official O15: Variable Head Pressure Control — Air-Cooled Condensers.

SOURCE: NSW OEH / AIRAH HVAC Optimisation Guide (OEH 2015/0317), Opportunity 15.

Guide strategy:
- Condenser fans use substantial energy; VSDs (or EC motors) on condenser fans control
  head/condensing pressure more efficiently than on/off or staged fans.
- During lower ambient, condenser capacity rises and load typically falls — condensing
  pressure can be reduced (floating or constant setpoint).
- Over-condensing harms TXV systems (flashing, expansion-device flow, oil return).
- Typical air-cooled condensing temperature is 8–12°C above ambient dry-bulb.
- Maintain that optimal head pressure by modulating condenser-fan speed (heat rejection).
- Guide-stated typical potential: up to 30% energy reduction on condenser fans (not verified).
- Manufacturer advice is required before changing head-pressure control.

Numeric HP envelopes, fan trim, deadband, and refrigerant P-T conversion are NOT in the
guide — they are CONFIGURABLE. This engine does not invent a psig vs OAT formula.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.agents.official_opportunities._common import agent_envelope, check, missing, num, text
from backend.services.hvac_safety_contract import classify_telemetry, is_demo_source, is_safe_mode, production_bms_connected

ENGINE_VERSION = "o15-float-hp-1.0"
GUIDE_APPROACH_MIN_C = 8.0
GUIDE_APPROACH_MAX_C = 12.0
GUIDE_SAVINGS_NOTE = "Guide states up to 30% energy reduction on condenser fans (typical potential, not verified)."


def _cfg(config: Dict[str, Any], key: str, default=None):
    if config.get(key) is not None:
        return config[key]
    return default


def _hp_from_curve(tcond: float, curve: Optional[List[Dict[str, Any]]]) -> Optional[float]:
    """Interpolate configurable saturation curve [{t_c, hp}, ...] — not a guide formula."""
    if not curve:
        return None
    pts = sorted(
        [(float(p["t_c"]), float(p["hp"])) for p in curve if p.get("t_c") is not None and p.get("hp") is not None],
        key=lambda x: x[0],
    )
    if len(pts) < 2:
        return None
    if tcond <= pts[0][0]:
        return pts[0][1]
    if tcond >= pts[-1][0]:
        return pts[-1][1]
    for (t0, p0), (t1, p1) in zip(pts, pts[1:]):
        if t0 <= tcond <= t1:
            frac = (tcond - t0) / (t1 - t0) if t1 != t0 else 0.0
            return round(p0 + frac * (p1 - p0), 2)
    return None


def evaluate_air_cooled_hp(telemetry: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = config or {}
    hp = num(telemetry, "HEAD_PRESSURE", "HP")
    tcond = num(telemetry, "COND_TEMP", "CONDENSING_TEMP")
    oat = num(telemetry, "OAT")
    if hp is None and tcond is None:
        return agent_envelope(
            "O15",
            False,
            recommendation="HOLD",
            reason="Missing required telemetry: head pressure or condensing temperature "
            "(guide: field sensors for temperature and pressure).",
            extra={"missing_points": ["HEAD_PRESSURE", "COND_TEMP"], "engine_version": ENGINE_VERSION},
        )

    hp_sp = num(telemetry, "HP_SETPOINT", "HEAD_PRESSURE_SETPOINT")
    fan_spd = num(telemetry, "FAN_SPEED", "FAN_SPEED_PCT")
    fan_st = num(telemetry, "FAN_STATE")
    fan_kw = num(telemetry, "FAN_POWER_KW")
    fans_n = num(telemetry, "FANS_RUNNING")
    comp = num(telemetry, "COMPRESSOR_STATE")
    comp_kw = num(telemetry, "COMPRESSOR_POWER_KW")
    load = num(telemetry, "LOAD", "LOAD_PCT")
    power = num(telemetry, "POWER", "POWER_KW")
    rh = num(telemetry, "RH")
    alarm = num(telemetry, "ALARM")
    quality = (text(telemetry, "quality", "QUALITY") or telemetry.get("quality") or "UNKNOWN").upper()
    source = text(telemetry, "source", "SOURCE") or telemetry.get("source")
    classified = classify_telemetry(
        {"quality": quality, "age_seconds": telemetry.get("age_seconds") or telemetry.get("ageSeconds"), "source": source},
        source,
    )

    approach = float(_cfg(cfg, "approach_c", 10.0))
    ap_min = float(_cfg(cfg, "approach_min_c", GUIDE_APPROACH_MIN_C))
    ap_max = float(_cfg(cfg, "approach_max_c", GUIDE_APPROACH_MAX_C))
    approach = min(max(approach, ap_min), ap_max)
    deadband = float(_cfg(cfg, "tcond_deadband_c", 0.5) or 0.5)
    fan_trim = _cfg(cfg, "fan_trim_pct", 2.0)
    min_fan = _cfg(cfg, "min_fan_speed_pct", None)
    max_fan = _cfg(cfg, "max_fan_speed_pct", None)
    max_step = _cfg(cfg, "max_fan_step_pct", 25.0)
    min_hp = _cfg(cfg, "min_head_pressure", None)
    max_hp = _cfg(cfg, "max_head_pressure", None)
    min_tc = _cfg(cfg, "min_condensing_temp_c", None)
    max_tc = _cfg(cfg, "max_condensing_temp_c", None)
    curve = _cfg(cfg, "saturation_curve_json", None)
    mode = str(_cfg(cfg, "control_mode", "ADVISORY") or "ADVISORY").upper()

    rec = "HOLD"
    rec_state = "ADVISORY"
    recommended_tcond = None
    recommended_hp = None
    recommended_fan = fan_spd
    reasons: List[str] = []

    if oat is None:
        rec = "HOLD"
        reasons.append(
            "Outdoor temperature is desirable for floating head pressure (guide). "
            "Without OAT, a floating condensing-temperature target is not computed."
        )
    else:
        recommended_tcond = round(float(oat) + approach, 2)
        recommended_hp = _hp_from_curve(recommended_tcond, curve)
        rec = "FLOAT_HEAD_PRESSURE"
        reasons.append(
            f"Guide: typical air-cooled condensing temperature is {ap_min:.0f}–{ap_max:.0f}°C above ambient dry-bulb. "
            f"Active approach {approach:.1f}°C (SOURCE-GUIDE range; value CONFIGURABLE within range) "
            f"gives recommended condensing temperature {recommended_tcond:.1f}°C at OAT {oat:.1f}°C. "
            "Maintain that head pressure by modulating condenser-fan speed (VSD/EC), not on/off cycling."
        )
        if tcond is not None and fan_spd is not None and fan_trim is not None:
            err = float(tcond) - recommended_tcond
            if err > deadband:
                recommended_fan = round(float(fan_spd) + float(fan_trim), 2)
                reasons.append(
                    f"Condensing temperature {tcond:.1f}°C is above the floating target — increase fan speed "
                    "to raise heat rejection (guide: VSD modulates heat rejection)."
                )
            elif err < -deadband:
                recommended_fan = round(float(fan_spd) - float(fan_trim), 2)
                reasons.append(
                    f"Condensing temperature {tcond:.1f}°C is below the floating target — reduce fan speed "
                    "to avoid over-condensing (guide: over-condensing harms TXV operation, liquid-line flashing, and oil return)."
                )
            else:
                rec = "HOLD"
                reasons.append("Condensing temperature is within the configurable deadband of the floating target.")
        elif tcond is None:
            reasons.append(
                "Condensing temperature is unavailable. A refrigerant P-T conversion is not specified by the guide; "
                "configure saturation_curve_json or provide COND_TEMP before a numeric head-pressure target is issued."
            )
            if recommended_hp is None:
                rec = "HOLD"

    if recommended_hp is not None and min_hp is not None and recommended_hp < float(min_hp):
        rec = "REJECT"
        reasons.append("Recommended head pressure is below configured minimum (manufacturer/site envelope).")
    if recommended_hp is not None and max_hp is not None and recommended_hp > float(max_hp):
        rec = "REJECT"
        reasons.append("Recommended head pressure exceeds configured maximum.")
    if hp is not None and max_hp is not None and hp > float(max_hp):
        rec = "REJECT"
        reasons.append("Measured head pressure exceeds configured maximum.")
    if hp is not None and min_hp is not None and hp < float(min_hp):
        rec = "REJECT"
        reasons.append("Measured head pressure is below configured minimum — over-condensing / TXV risk.")
    if recommended_tcond is not None and min_tc is not None and recommended_tcond < float(min_tc):
        rec = "REJECT"
        reasons.append("Recommended condensing temperature is below configured minimum.")
    if recommended_tcond is not None and max_tc is not None and recommended_tcond > float(max_tc):
        rec = "REJECT"
        reasons.append("Recommended condensing temperature exceeds configured maximum.")
    if recommended_fan is not None and min_fan is not None and recommended_fan < float(min_fan):
        rec = "REJECT"
        reasons.append("Recommended fan speed is below configured minimum.")
    if recommended_fan is not None and max_fan is not None and recommended_fan > float(max_fan):
        rec = "REJECT"
        reasons.append("Recommended fan speed exceeds configured maximum.")
    if fan_spd is not None and recommended_fan is not None and max_step is not None:
        if abs(float(recommended_fan) - float(fan_spd)) > float(max_step):
            rec = "REJECT"
            reasons.append("Recommended fan speed step exceeds configured rate-of-change limit.")

    demo = classified.get("demo") or is_demo_source(source)
    bms_ok = production_bms_connected()
    safe_mode = is_safe_mode()
    tel_ok = classified.get("status") == "LIVE" and classified.get("usable")
    if classified.get("status") == "STALE":
        rec = "HOLD"
        reasons.append("Telemetry is STALE — HOLD (no write).")
    if classified.get("status") == "BAD":
        rec = "HOLD"
        reasons.append("Telemetry quality is BAD — HOLD (no write).")
    if demo:
        reasons.append("Source is SIMULATION/DEMO — production writes are rejected.")
    if safe_mode:
        if rec == "FLOAT_HEAD_PRESSURE":
            rec = "HOLD"
        reasons.append("SAFE_MODE is active — equipment writes are blocked.")
    if alarm is not None and alarm > 0:
        rec = "HOLD"
        reasons.append("Equipment alarm is active — HOLD.")

    predicted_fan_kw = None
    predicted_class = None
    if fan_kw is not None and fan_spd and recommended_fan and fan_spd > 0:
        predicted_fan_kw = round(float(fan_kw) * ((float(recommended_fan) / float(fan_spd)) ** 3), 3)
        predicted_class = "PREDICTED"
    predicted_delta = None
    if predicted_fan_kw is not None and fan_kw is not None:
        predicted_delta = round(float(fan_kw) - predicted_fan_kw, 3)

    engineering = [
        check("Telemetry Fresh", classified.get("status") not in ("STALE", "MISSING", "BAD"), f"Classified {classified.get('status')}", classified.get("age_seconds")),
        check("Data Quality GOOD", quality in ("GOOD", "LIVE") and classified.get("status") not in ("BAD",), f"quality={quality}"),
        check("Condenser Available", alarm is None or alarm <= 0, "No active condenser alarm", alarm),
        check("Fan Available", fan_st is None or fan_st >= 0, "Fan state present or unknown", fan_st),
        check("Compressor Available", True, "Compressor state not required for fan HP loop" if comp is None else "Observed", comp),
        check(
            "Head Pressure Within Limits",
            (min_hp is None or hp is None or hp >= float(min_hp)) and (max_hp is None or hp is None or hp <= float(max_hp)),
            "Configured HP envelope (optional)",
            hp,
            min_hp,
            max_hp,
        ),
        check(
            "Condensing Temperature Within Limits",
            (min_tc is None or tcond is None or tcond >= float(min_tc)) and (max_tc is None or tcond is None or tcond <= float(max_tc)),
            "Configured Tcond envelope (optional)",
            tcond,
            min_tc,
            max_tc,
        ),
        check(
            "Rate-of-change Valid",
            not (fan_spd is not None and recommended_fan is not None and max_step is not None and abs(float(recommended_fan) - float(fan_spd)) > float(max_step)),
            "Configured fan step",
            abs(float(recommended_fan) - float(fan_spd)) if fan_spd is not None and recommended_fan is not None else None,
            None,
            max_step,
        ),
        check("Engineering Limits Valid", rec != "REJECT", "Config min/max HP, Tcond, fan"),
    ]
    write_gates = [
        check("BMS Connected", bms_ok, "Production BMS connected" if bms_ok else "BMS offline"),
        check("Source is LIVE", classified.get("status") == "LIVE" and not demo, f"classified={classified.get('status')}"),
        check("No SAFE_MODE", not safe_mode, "SAFE_MODE off" if not safe_mode else "SAFE_MODE on"),
        check("No conflicting command", True, "Checked at apply"),
    ]
    gates = engineering + write_gates
    eng_pass = all(g["result"] == "PASS" for g in engineering)
    write_pass = all(g["result"] == "PASS" for g in write_gates)
    overall = (
        "SAFE TO APPLY"
        if rec == "FLOAT_HEAD_PRESSURE" and eng_pass and write_pass and tel_ok
        else ("REJECTED — ENGINEERING LIMIT" if rec == "REJECT" else "HOLD — SAFETY CONDITION NOT MET")
    )

    if rec == "REJECT":
        rec_state = "REJECTED"
        safety_status = "REJECT"
    elif not eng_pass or rec != "FLOAT_HEAD_PRESSURE":
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
    elif mode == "AUTO" and write_pass and tel_ok:
        rec_state = "READY TO APPLY"
        safety_status = "PASS"
    else:
        rec_state = "ADVISORY"
        safety_status = "PASS" if eng_pass else "HOLD"

    observed_approach = None
    if tcond is not None and oat is not None:
        observed_approach = round(float(tcond) - float(oat), 2)

    current = {
        "outdoor_temperature_c": oat,
        "outdoor_humidity_pct": rh,
        "condenser_temperature_c": tcond,
        "head_pressure": hp,
        "head_pressure_setpoint": hp_sp,
        "fan_speed_pct": fan_spd,
        "fan_status": "ON" if (fan_st or 0) >= 1 or (fan_spd or 0) > 5 else ("OFF" if fan_st is not None or fan_spd is not None else None),
        "fan_power_kw": fan_kw,
        "fans_running": fans_n,
        "compressor_status": "ON" if (comp or 0) >= 1 else ("OFF" if comp is not None else None),
        "compressor_power_kw": comp_kw,
        "load": load,
        "power_kw": power,
        "observed_approach_c": observed_approach,
        "alarm": alarm,
        "current_setpoint_psig": hp_sp if hp_sp is not None else hp,
    }
    optimized = {
        "recommended_condensing_temp_c": recommended_tcond,
        "recommended_head_pressure": recommended_hp,
        "recommended_fan_speed_pct": recommended_fan,
        "approach_c": approach,
        "approach_source": "SOURCE-GUIDE range 8–12°C; value CONFIGURABLE within range",
        "fan_trim_pct": fan_trim,
        "fan_trim_source": "CONFIGURABLE_DEFAULT",
        "saturation_curve_source": "CONFIGURABLE" if curve else "NOT_CONFIGURED",
    }
    cmd_value = recommended_fan if recommended_fan is not None else recommended_hp
    extra = {
        "current_value": fan_spd if recommended_fan is not None else (hp_sp if hp_sp is not None else hp),
        "optimized_value": cmd_value,
        "unit": "%" if recommended_fan is not None else None,
        "engine_version": ENGINE_VERSION,
        "recommendation_state": rec_state,
        "control_mode": mode,
        "overall_safety": overall,
        "classified_telemetry": classified,
        "energy_impact_class": predicted_class,
        "predicted_fan_power_kw": predicted_fan_kw,
        "predicted_power_delta_kw": predicted_delta,
        "verified_savings_kw": None,
        "applied_savings_kw": None,
        "guide_potential_note": GUIDE_SAVINGS_NOTE,
        "why": {
            "outdoor_condition": f"OAT={oat}",
            "current_head_pressure": f"HP={hp}, Tcond={tcond}, setpoint={hp_sp}",
            "current_fan_operation": f"speed={fan_spd}% state={fan_st}",
            "system_demand": f"load={load} compressor={comp}",
            "active_engineering_limits": {
                "approach_c": approach,
                "approach_range_c": [ap_min, ap_max],
                "min_head_pressure": min_hp,
                "max_head_pressure": max_hp,
                "min_condensing_temp_c": min_tc,
                "max_condensing_temp_c": max_tc,
            },
            "control_relationship": "VSD/EC condenser fans modulate heat rejection to hold floating condensing temperature ≈ OAT + 8–12°C (guide).",
            "recommended_target": f"Tcond={recommended_tcond} HP={recommended_hp} fan={recommended_fan}%",
            "reason_for_change": " ".join(reasons),
            "safety_gates": [g["check_name"] + "=" + g["result"] for g in gates],
        },
    }
    envelope = agent_envelope(
        "O15",
        True,
        current_state=current,
        optimized_state=optimized,
        recommendation=rec,
        reason=" ".join(reasons) or "No recommendation.",
        confidence=0.8 if rec == "FLOAT_HEAD_PRESSURE" and eng_pass else (0.55 if rec == "HOLD" else 0.3),
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
    if rec in ("FLOAT_HEAD_PRESSURE", "HOLD", "REJECT"):
        envelope["recommendation"] = rec
    return envelope
