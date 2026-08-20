"""Official O16: Variable Head Pressure Control — Water-Cooled Condensers.

SOURCE: NSW OEH / AIRAH HVAC Optimisation Guide (OEH 2015/0317), Opportunity 16.

Guide strategy:
- Part-load: condenser capacity up, load typically down — condensing pressure can be reduced.
- Maintain head/condensing pressure (constant or, better, floating setpoint) by modulating heat rejection:
  1. Single water-cooled DX unit: VSD on the condenser-water pump.
  2. Multiple DX units on one CW pump: CW modulating head-pressure valves.
- Isolate CW to a unit that is not operating (2-port) so a shared pump does not circulate unused flow.
- Over-condensing (excess CW) drops condensing temperature/pressure and harms the vapour-compression cycle
  (capacity, oil return, protection trips). Under-condensing also risks trips.
- Typical potential: 10–30% CW-pump energy (guide typical potential, not verified site savings).
- Manufacturer advice required (especially CW isolation retrofits).

Numeric HP/flow/speed envelopes, pump trim, and a CEWT formula are NOT in the guide — CONFIGURABLE.
Affinity-law predicted pump power (Appendix D) is PREDICTED only.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.agents.official_opportunities._common import agent_envelope, check, num, text
from backend.services.hvac_safety_contract import classify_telemetry, is_demo_source, is_safe_mode, production_bms_connected

ENGINE_VERSION = "o16-wc-hp-1.0"
GUIDE_SAVINGS_NOTE = (
    "Guide states CW-pump energy reduction of approximately 10–30% (typical potential, not verified for this site)."
)

STRATEGIES = (
    "FIXED_HEAD_PRESSURE",
    "FLOATING_HEAD_PRESSURE",
    "VSD_PUMP",
    "VALVE",
    "COORDINATED",
)


def _cfg(config: Dict[str, Any], key: str, default=None):
    if config.get(key) is not None:
        return config[key]
    return default


class O16WaterCooledHeadPressureOptimizer:
    """Deterministic water-cooled head-pressure optimizer (shared runtime engine)."""

    version = ENGINE_VERSION

    def evaluate(self, telemetry: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return evaluate_water_cooled_hp(telemetry, config)


def evaluate_water_cooled_hp(telemetry: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = config or {}
    cewt = num(telemetry, "CEWT", "CW_SUPPLY_TEMP")
    clwt = num(telemetry, "CLWT", "CW_RETURN_TEMP")
    hp = num(telemetry, "HEAD_PRESSURE", "HP")
    tcond = num(telemetry, "COND_TEMP", "CONDENSING_TEMP")
    if cewt is None and clwt is None and hp is None and tcond is None:
        return agent_envelope(
            "O16",
            False,
            recommendation="HOLD",
            reason="Missing required telemetry: condenser-water temperatures and/or condensing pressure/temperature "
            "(guide: field sensors for temperature and pressure).",
            extra={"missing_points": ["CEWT", "CLWT", "HEAD_PRESSURE", "COND_TEMP"], "engine_version": ENGINE_VERSION},
        )

    hp_sp = num(telemetry, "HP_SETPOINT", "HEAD_PRESSURE_SETPOINT")
    flow = num(telemetry, "CW_FLOW")
    pump_spd = num(telemetry, "PUMP_SPEED", "PUMP_SPEED_PCT")
    pump_st = num(telemetry, "PUMP_STATE")
    pump_kw = num(telemetry, "PUMP_POWER_KW")
    valve = num(telemetry, "VALVE_POSITION", "VALVE_PCT")
    load = num(telemetry, "LOAD", "LOAD_PCT")
    comp = num(telemetry, "COMPRESSOR_STATE", "COMPRESSOR_LOAD")
    cooling_call = num(telemetry, "COOLING_CALL", "UNIT_ENABLE")
    oat = num(telemetry, "OAT")
    oawb = num(telemetry, "OAWB", "WET_BULB")
    alarm = num(telemetry, "ALARM")
    active_n = num(telemetry, "ACTIVE_CONDENSERS")
    quality = (text(telemetry, "quality", "QUALITY") or telemetry.get("quality") or "UNKNOWN").upper()
    source = text(telemetry, "source", "SOURCE") or telemetry.get("source")
    classified = classify_telemetry(
        {"quality": quality, "age_seconds": telemetry.get("age_seconds") or telemetry.get("ageSeconds"), "source": source},
        source,
    )

    strategy = str(_cfg(cfg, "control_strategy", "VSD_PUMP") or "VSD_PUMP").upper()
    if strategy not in STRATEGIES:
        strategy = "VSD_PUMP"
    mode = str(_cfg(cfg, "control_mode", "ADVISORY") or "ADVISORY").upper()
    enabled = bool(_cfg(cfg, "enabled", True))
    shared_pump = bool(_cfg(cfg, "shared_pump", strategy in ("VALVE", "COORDINATED")))
    target_hp = _cfg(cfg, "target_head_pressure", None)
    target_tcond = _cfg(cfg, "target_condensing_temp_c", None)
    hp_deadband = float(_cfg(cfg, "hp_deadband", 2.0) or 2.0)
    pump_trim = _cfg(cfg, "pump_trim_pct", 2.0)
    valve_trim = _cfg(cfg, "valve_trim_pct", 2.0)
    min_pump = _cfg(cfg, "min_pump_speed_pct", None)
    max_pump = _cfg(cfg, "max_pump_speed_pct", None)
    min_flow = _cfg(cfg, "min_cw_flow", None)
    max_flow = _cfg(cfg, "max_cw_flow", None)
    min_hp = _cfg(cfg, "min_head_pressure", None)
    max_hp = _cfg(cfg, "max_head_pressure", None)
    min_tc = _cfg(cfg, "min_condensing_temp_c", None)
    max_tc = _cfg(cfg, "max_condensing_temp_c", None)
    min_valve = _cfg(cfg, "min_valve_pct", None)
    max_valve = _cfg(cfg, "max_valve_pct", None)
    max_step = _cfg(cfg, "max_pump_step_pct", 25.0)
    high_load = float(_cfg(cfg, "high_load_pct", 90.0) or 90.0)
    isolate_valve = float(_cfg(cfg, "isolate_valve_pct", 0.0) or 0.0)

    rec = "HOLD"
    rec_state = "ADVISORY"
    recommended_pump = pump_spd
    recommended_valve = valve
    recommended_hp = target_hp if target_hp is not None else hp_sp
    recommended_tcond = target_tcond
    recommended_flow = None
    reasons: List[str] = []
    cmd_point = "CW.PumpSpeed"
    cmd_value = recommended_pump
    cmd_unit = "%"

    unit_off = (cooling_call is not None and cooling_call <= 0) or (comp is not None and comp <= 0 and cooling_call is None)
    delta_t = None
    if cewt is not None and clwt is not None:
        delta_t = round(float(clwt) - float(cewt), 2)
    approach = None
    if tcond is not None and cewt is not None:
        approach = round(float(tcond) - float(cewt), 2)
    hp_margin = None
    if hp is not None and min_hp is not None:
        hp_margin = round(float(hp) - float(min_hp), 2)
    elif hp is not None and recommended_hp is not None:
        hp_margin = round(float(hp) - float(recommended_hp), 2)
    load_ratio = None
    if load is not None:
        load_ratio = round(float(load) / 100.0, 3)

    if not enabled:
        rec = "HOLD"
        reasons.append("O16 optimization is DISABLED in configuration.")
    elif unit_off and strategy in ("VALVE", "COORDINATED") and valve is not None:
        rec = "ISOLATE_UNIT"
        recommended_valve = isolate_valve
        cmd_point = "CW.ValvePosition"
        cmd_value = recommended_valve
        reasons.append(
            "Guide: when AC units are not in operation, isolate CW through a 2-port valve so a shared pump "
            "does not circulate unused condenser water."
        )
        if shared_pump:
            recommended_pump = pump_spd
            reasons.append("Shared CW pump is not stopped independently (coordinate demand across units).")
    elif unit_off and strategy == "VSD_PUMP":
        rec = "HOLD"
        reasons.append(
            "Unit appears off. Guide: isolate unused condensers; a single-unit VSD pump should not be sped up. "
            "No pump-speed reduction is issued without a configured isolation valve."
        )
    elif load is not None and float(load) >= high_load:
        rec = "HOLD"
        reasons.append(
            f"High cooling load ({load}%) — heat rejection is not reduced (guide: do not compromise refrigeration performance)."
        )
    elif min_hp is not None and hp is not None and float(hp) < float(min_hp):
        rec = "REJECT"
        reasons.append("Measured head pressure is below configured minimum — over-condensing / lubrication / trip risk.")
        if pump_spd is not None and pump_trim is not None:
            recommended_pump = round(float(pump_spd) + float(pump_trim), 2)
        if valve is not None and valve_trim is not None:
            recommended_valve = round(float(valve) + float(valve_trim), 2)
    elif recommended_hp is None and recommended_tcond is None:
        rec = "HOLD"
        reasons.append(
            "Guide: determine optimal or floating head pressure for the refrigerant and equipment. "
            "No site target_head_pressure or target_condensing_temp_c is configured — no invented CEWT/psig formula is applied."
        )
    else:
        err_hp = None
        err_tc = None
        if hp is not None and recommended_hp is not None:
            err_hp = float(hp) - float(recommended_hp)
        if tcond is not None and recommended_tcond is not None:
            err_tc = float(tcond) - float(recommended_tcond)
        over = (err_hp is not None and err_hp > hp_deadband) or (err_tc is not None and err_tc > 0.5)
        under = (err_hp is not None and err_hp < -hp_deadband) or (err_tc is not None and err_tc < -0.5)
        if over:
            rec = "OPTIMIZE_HP"
            reasons.append(
                "Part-load / excess heat-rejection capacity: condensing pressure is above the configured target. "
                "Guide: reduce CW pumping energy by VSD pump speed (single unit) or modulating head-pressure valves (shared pump), "
                "without over-condensing."
            )
            if strategy in ("VSD_PUMP", "COORDINATED", "FLOATING_HEAD_PRESSURE", "FIXED_HEAD_PRESSURE") and pump_spd is not None and pump_trim is not None:
                if not (shared_pump and strategy == "VALVE"):
                    recommended_pump = round(float(pump_spd) - float(pump_trim), 2)
                    cmd_point = "CW.PumpSpeed"
                    cmd_value = recommended_pump
            if strategy in ("VALVE", "COORDINATED") and valve is not None and valve_trim is not None:
                recommended_valve = round(float(valve) - float(valve_trim), 2)
                if strategy == "VALVE" or shared_pump:
                    cmd_point = "CW.ValvePosition"
                    cmd_value = recommended_valve
                    cmd_unit = "%"
        elif under:
            rec = "OPTIMIZE_HP"
            reasons.append(
                "Head/condensing pressure is below the configured target — increase heat-rejection flow "
                "(guide: avoid under-condensing and protection trips)."
            )
            if pump_spd is not None and pump_trim is not None and not (shared_pump and strategy == "VALVE"):
                recommended_pump = round(float(pump_spd) + float(pump_trim), 2)
                cmd_point = "CW.PumpSpeed"
                cmd_value = recommended_pump
            if strategy in ("VALVE", "COORDINATED") and valve is not None and valve_trim is not None:
                recommended_valve = round(float(valve) + float(valve_trim), 2)
                if strategy == "VALVE" or shared_pump:
                    cmd_point = "CW.ValvePosition"
                    cmd_value = recommended_valve
        else:
            rec = "HOLD"
            reasons.append("Head/condensing pressure is within the configurable deadband of the target.")

    def _limit(val, lo, hi, name):
        nonlocal rec, reasons
        if val is None:
            return val
        out = val
        if lo is not None and out < float(lo):
            rec = "REJECT"
            reasons.append(f"{name} below configured minimum.")
            out = float(lo)
        if hi is not None and out > float(hi):
            rec = "REJECT"
            reasons.append(f"{name} exceeds configured maximum.")
            out = float(hi)
        return out

    recommended_pump = _limit(recommended_pump, min_pump, max_pump, "Recommended pump speed")
    recommended_valve = _limit(recommended_valve, min_valve, max_valve, "Recommended valve position")
    if flow is not None and min_flow is not None and float(flow) < float(min_flow) and rec == "OPTIMIZE_HP" and cmd_point == "CW.PumpSpeed":
        rec = "REJECT"
        reasons.append("Measured CW flow is below configured minimum — pump speed will not be reduced.")
    if pump_spd is not None and recommended_pump is not None and max_step is not None:
        if abs(float(recommended_pump) - float(pump_spd)) > float(max_step):
            rec = "REJECT"
            reasons.append("Recommended pump speed step exceeds configured rate-of-change limit.")
    if hp is not None and max_hp is not None and float(hp) > float(max_hp):
        rec = "REJECT"
        reasons.append("Measured head pressure exceeds configured maximum.")
    if tcond is not None and min_tc is not None and float(tcond) < float(min_tc):
        rec = "REJECT"
        reasons.append("Condensing temperature is below configured minimum.")
    if tcond is not None and max_tc is not None and float(tcond) > float(max_tc):
        rec = "REJECT"
        reasons.append("Condensing temperature exceeds configured maximum.")

    if cmd_point == "CW.ValvePosition":
        cmd_value = recommended_valve
    else:
        cmd_value = recommended_pump

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
        if rec in ("OPTIMIZE_HP", "ISOLATE_UNIT"):
            rec = "HOLD"
        reasons.append("SAFE_MODE is active — equipment writes are blocked.")
    if alarm is not None and alarm > 0:
        rec = "HOLD"
        reasons.append("Equipment alarm is active — HOLD.")

    predicted_pump_kw = None
    predicted_class = None
    predicted_delta = None
    if pump_kw is not None and pump_spd and recommended_pump and float(pump_spd) > 0:
        predicted_pump_kw = round(float(pump_kw) * ((float(recommended_pump) / float(pump_spd)) ** 3), 3)
        predicted_class = "PREDICTED"
        predicted_delta = round(float(pump_kw) - predicted_pump_kw, 3)

    engineering = [
        check("Telemetry present", hp is not None or tcond is not None or cewt is not None, "Water-cooled condenser telemetry"),
        check("Telemetry Fresh", classified.get("status") not in ("STALE", "MISSING", "BAD"), f"Classified {classified.get('status')}", classified.get("age_seconds")),
        check("Data Quality GOOD", quality in ("GOOD", "LIVE") and classified.get("status") not in ("BAD",), f"quality={quality}"),
        check("Equipment enabled", enabled, "O16 enabled" if enabled else "Disabled"),
        check("Condenser Available", alarm is None or alarm <= 0, "No critical alarm", alarm),
        check(
            "Head Pressure Within Limits",
            (min_hp is None or hp is None or hp >= float(min_hp)) and (max_hp is None or hp is None or hp <= float(max_hp)),
            "Configured HP envelope",
            hp,
            min_hp,
            max_hp,
        ),
        check("Minimum head pressure maintained", min_hp is None or hp is None or hp >= float(min_hp), "Configured min HP", hp, min_hp, None),
        check("Minimum CW flow maintained", min_flow is None or flow is None or flow >= float(min_flow), "Configured min flow", flow, min_flow, None),
        check(
            "Pump speed envelope",
            (min_pump is None or recommended_pump is None or recommended_pump >= float(min_pump))
            and (max_pump is None or recommended_pump is None or recommended_pump <= float(max_pump)),
            "Configured pump min/max",
            recommended_pump,
            min_pump,
            max_pump,
        ),
        check(
            "Valve operating range",
            (min_valve is None or recommended_valve is None or recommended_valve >= float(min_valve))
            and (max_valve is None or recommended_valve is None or recommended_valve <= float(max_valve)),
            "Configured valve min/max",
            recommended_valve,
            min_valve,
            max_valve,
        ),
        check(
            "Rate-of-change Valid",
            not (
                pump_spd is not None
                and recommended_pump is not None
                and max_step is not None
                and abs(float(recommended_pump) - float(pump_spd)) > float(max_step)
            ),
            "Configured pump step",
            abs(float(recommended_pump) - float(pump_spd)) if pump_spd is not None and recommended_pump is not None else None,
            None,
            max_step,
        ),
        check("Compressor operating envelope", rec != "REJECT", "Config HP/Tcond/flow/speed"),
        check("Engineering Limits Valid", rec != "REJECT", "Manufacturer/site envelope"),
    ]
    write_gates = [
        check("BMS Connected", bms_ok, "Production BMS connected" if bms_ok else "BMS offline"),
        check("Source is LIVE", classified.get("status") == "LIVE" and not demo, f"classified={classified.get('status')}"),
        check("No SAFE_MODE", not safe_mode, "SAFE_MODE off" if not safe_mode else "SAFE_MODE on"),
        check("No conflicting command", True, "Checked at apply"),
        check("Command idempotency", True, "Checked at apply via command_id"),
    ]
    gates = engineering + write_gates
    eng_pass = all(g["result"] == "PASS" for g in engineering)
    write_pass = all(g["result"] == "PASS" for g in write_gates)
    actionable = rec in ("OPTIMIZE_HP", "ISOLATE_UNIT")
    overall = (
        "SAFE TO APPLY"
        if actionable and eng_pass and write_pass and tel_ok
        else ("REJECTED — ENGINEERING LIMIT" if rec == "REJECT" else "HOLD — SAFETY CONDITION NOT MET")
    )

    if rec == "REJECT":
        rec_state = "REJECTED"
        safety_status = "REJECT"
        rec_out = "BLOCKED"
    elif not eng_pass or not actionable:
        rec_state = "ADVISORY" if mode == "ADVISORY" else "HOLD"
        if safe_mode:
            rec_state = "REJECTED"
        safety_status = "HOLD"
        rec_out = rec
    elif not write_pass:
        rec_state = "ADVISORY"
        safety_status = "HOLD"
        rec_out = rec
    elif mode == "APPROVAL_REQUIRED":
        rec_state = "APPROVAL_REQUIRED"
        safety_status = "PASS"
        rec_out = rec
    elif mode == "AUTO" and write_pass and tel_ok:
        rec_state = "READY TO APPLY"
        safety_status = "PASS"
        rec_out = rec
    else:
        rec_state = "ADVISORY"
        safety_status = "PASS" if eng_pass else "HOLD"
        rec_out = rec

    current = {
        "cewt_c": cewt,
        "clwt_c": clwt,
        "cw_delta_t_c": delta_t,
        "cw_flow": flow,
        "condensing_temperature_c": tcond,
        "head_pressure": hp,
        "head_pressure_setpoint": hp_sp,
        "pump_speed_pct": pump_spd,
        "pump_status": "ON" if (pump_st or 0) >= 1 or (pump_spd or 0) > 5 else ("OFF" if pump_st is not None or pump_spd is not None else None),
        "pump_power_kw": pump_kw,
        "valve_position_pct": valve,
        "load_pct": load,
        "load_ratio": load_ratio,
        "compressor_status": "ON" if (comp or 0) >= 1 else ("OFF" if comp is not None else None),
        "cooling_call": cooling_call,
        "approach_c": approach,
        "head_pressure_margin": hp_margin,
        "outdoor_temperature_c": oat,
        "outdoor_wet_bulb_c": oawb,
        "active_condensers": active_n,
        "alarm": alarm,
        "current_setpoint_c": cewt,
    }
    optimized = {
        "recommended_head_pressure": recommended_hp,
        "recommended_condensing_temp_c": recommended_tcond,
        "recommended_pump_speed_pct": recommended_pump,
        "recommended_valve_position_pct": recommended_valve,
        "recommended_cw_flow": recommended_flow,
        "control_strategy": strategy,
        "shared_pump": shared_pump,
        "command_point": cmd_point,
        "strategy_source": "SOURCE-GUIDE (VSD pump vs modulating valve vs isolate-off)",
    }
    extra = {
        "current_value": pump_spd if cmd_point == "CW.PumpSpeed" else valve,
        "optimized_value": cmd_value,
        "unit": cmd_unit,
        "command_point": cmd_point,
        "engine_version": ENGINE_VERSION,
        "recommendation_state": rec_state,
        "control_mode": mode,
        "overall_safety": overall,
        "classified_telemetry": classified,
        "energy_impact_class": predicted_class,
        "predicted_pump_power_kw": predicted_pump_kw,
        "predicted_power_delta_kw": predicted_delta,
        "verified_savings_kw": None,
        "applied_savings_kw": None,
        "guide_potential_note": GUIDE_SAVINGS_NOTE,
        "why": {
            "outdoor_condition": f"OAT={oat} WB={oawb}",
            "current_load": f"load={load}",
            "current_head_pressure": f"HP={hp} target={recommended_hp} Tcond={tcond}",
            "cw_temps": f"CEWT={cewt} CLWT={clwt} dT={delta_t}",
            "current_pump": f"speed={pump_spd}% power={pump_kw} kW",
            "current_valve": f"position={valve}",
            "estimated_pump_power": pump_kw,
            "estimated_optimized_pump_power": predicted_pump_kw,
            "control_relationship": (
                "VSD CW pump (single unit) or modulating head-pressure valves (shared pump) "
                "modulate heat rejection to hold configured head pressure without over-condensing (guide)."
            ),
            "active_engineering_limits": {
                "min_head_pressure": min_hp,
                "max_head_pressure": max_hp,
                "min_cw_flow": min_flow,
                "min_pump_speed_pct": min_pump,
                "max_pump_speed_pct": max_pump,
                "control_strategy": strategy,
            },
            "recommended_target": f"HP={recommended_hp} pump={recommended_pump}% valve={recommended_valve}%",
            "reason_for_change": " ".join(reasons),
            "safety_gates": [g["check_name"] + "=" + g["result"] for g in gates],
        },
    }
    envelope = agent_envelope(
        "O16",
        True,
        current_state=current,
        optimized_state=optimized,
        recommendation=rec_out if rec == "REJECT" else rec,
        reason=" ".join(reasons) or "No recommendation.",
        confidence=0.8 if actionable and eng_pass else (0.55 if rec == "HOLD" else 0.3),
        energy_impact=predicted_delta,
        safety_checks=engineering,
        extra=extra,
    )
    envelope["safety_checks"] = gates
    envelope["write_gates"] = write_gates
    envelope["safety_status"] = safety_status
    envelope["live"] = (not demo) and classified.get("status") == "LIVE"
    if rec == "REJECT":
        envelope["recommendation"] = "BLOCKED"
        envelope["status"] = "REJECTED"
    if not envelope["live"]:
        envelope["status"] = "AWAITING_TELEMETRY" if classified.get("status") in ("MISSING", None) else classified.get("status")
        envelope["agent_status"] = "DEGRADED"
        if demo:
            envelope["status"] = "SIMULATION"
    return envelope
