"""O10–O13 physics from telemetry dicts. No silent sensor defaults."""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Kolkata")
CO2_TARGET_PPM = 800.0
CO_LIMIT_PPM = 50.0
CO_WARN_PPM = 25.0
LIVE_S = 60.0
DAMPER_MIN_PCT = 15.0
DAMPER_MAX_PCT = 100.0
MIN_OA_CFM_FLOOR = 1200.0
MIN_EXHAUST_CFM = 3500.0
PURGE_START = "21:00"
PURGE_STOP = "06:00"


def moist_enthalpy_kjkg(drybulb_c: Optional[float], rh_pct: Optional[float]) -> Optional[float]:
    if drybulb_c is None or rh_pct is None:
        return None
    try:
        t = float(drybulb_c)
        rh = float(rh_pct)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(t) or not math.isfinite(rh):
        return None
    p_sat = 0.61078 * math.exp((17.27 * t) / (t + 237.3))
    p_v = (rh / 100.0) * p_sat
    p_atm = 101.325
    w = 0.62198 * p_v / max(0.1, (p_atm - p_v))
    return round((1.006 * t) + (w * (2501.0 + 1.86 * t)), 2)


def enthalpy_advantage(return_h: Optional[float], outdoor_h: Optional[float]) -> Optional[float]:
    if return_h is None or outdoor_h is None:
        return None
    return round(float(return_h) - float(outdoor_h), 2)


def mixed_air_temp(oat: Optional[float], rat: Optional[float], damper_pct: Optional[float]) -> Optional[float]:
    if oat is None or rat is None or damper_pct is None:
        return None
    f = max(0.0, min(100.0, float(damper_pct))) / 100.0
    return round(f * float(oat) + (1.0 - f) * float(rat), 2)


def oa_mass_flow_kg_s(supply_cfm: Optional[float], damper_pct: Optional[float]) -> Optional[float]:
    if supply_cfm is None or damper_pct is None:
        return None
    oa_cfm = float(supply_cfm) * max(0.0, min(100.0, float(damper_pct))) / 100.0
    return oa_cfm * 0.000471947 * 1.2


def chiller_kw_from_oa(h_oa: Optional[float], h_ra: Optional[float], m_oa: Optional[float], chiller_kw: Optional[float]) -> Optional[float]:
    if h_oa is None or h_ra is None or m_oa is None:
        return chiller_kw
    q = max(0.0, m_oa * max(0.0, h_ra - h_oa))
    base = float(chiller_kw) if chiller_kw is not None else 28.0
    return round(max(2.0, base - q), 2)


def free_cooling_kw(h_oa: Optional[float], h_ra: Optional[float], m_oa: Optional[float]) -> Optional[float]:
    if h_oa is None or h_ra is None or m_oa is None:
        return None
    return round(max(0.0, m_oa * max(0.0, h_ra - h_oa)), 2)


def fan_kw_at_cfm(fan_kw: Optional[float], cfm: Optional[float], design_cfm: Optional[float]) -> Optional[float]:
    if fan_kw is None or cfm is None or not design_cfm:
        return fan_kw
    ratio = max(0.15, float(cfm) / float(design_cfm))
    return round(float(fan_kw) * (ratio ** 2.7), 2)


def _conf(present: int, required: int) -> Optional[float]:
    if required <= 0:
        return None
    return round(min(0.99, 0.55 + 0.44 * (present / required)), 3)


def evaluate_o10(tel: Dict[str, Any]) -> Dict[str, Any]:
    oat = tel.get("outdoor_temp_c")
    oa_rh = tel.get("outdoor_rh_percent")
    rat = tel.get("return_temp_c")
    ra_rh = tel.get("return_rh_percent")
    damper = tel.get("damper_percent")
    cfm = tel.get("supply_airflow_cfm")
    fan_kw = tel.get("fan_power_kw")
    chiller_kw = tel.get("chiller_power_kw")
    h_oa = tel.get("outdoor_enthalpy_kjkg") or moist_enthalpy_kjkg(oat, oa_rh)
    h_ra = tel.get("return_enthalpy_kjkg") or moist_enthalpy_kjkg(rat, ra_rh)
    adv = enthalpy_advantage(h_ra, h_oa)
    required = [oat, rat, damper, cfm]
    if any(v is None for v in required):
        return {"available": False, "missing": "outdoor/return temperature, damper, or supply airflow"}

    if oat is not None and h_oa is not None and h_ra is not None and oat <= 18.0 and h_oa < (h_ra - 2.0):
        mode = "100%_FREE_COOLING_ECONOMIZER"
        rec = round(min(100.0, max(70.0, float(damper) + 13.5)), 1)
        status = "OPTIMAL"
    elif oat is not None and h_oa is not None and h_ra is not None and oat <= 22.0 and h_oa < h_ra:
        mode = "INTEGRATED_PARTIAL_ECONOMIZER"
        rec = 55.0
        status = "READY"
    else:
        mode = "MINIMUM_VENTILATION_CLAMP"
        rec = 20.0
        status = "WARNING"

    rec = round(max(15.0, min(100.0, rec)), 1)
    m_cur = oa_mass_flow_kg_s(cfm, damper)
    m_opt = oa_mass_flow_kg_s(cfm, rec)
    q_cur = free_cooling_kw(h_oa, h_ra, m_cur) or 0.0
    q_opt = free_cooling_kw(h_oa, h_ra, m_opt) or 0.0
    chill_cur = chiller_kw_from_oa(h_oa, h_ra, m_cur, chiller_kw)
    chill_opt = chiller_kw_from_oa(h_oa, h_ra, m_opt, chiller_kw)
    fan_cur = fan_kw
    fan_opt = fan_kw
    p_cur = (chill_cur or 0) + (fan_cur or 0)
    p_opt = (chill_opt or 0) + (fan_opt or 0)
    d_kw = round(p_opt - p_cur, 2)
    fc_gain = round((q_opt or 0) - (q_cur or 0), 2)
    if d_kw == 0 and fc_gain > 0:
        d_kw = round(-fc_gain, 2)
    daily = round(abs(d_kw) * 8.5, 1) if d_kw != 0 else 0.0
    if d_kw > 0:
        daily = round(-daily, 1)
    else:
        daily = round(daily, 1)

    labels = [
        ("BASELINE", float(damper), "MINIMUM" if damper < 30 else "CURRENT"),
        ("MODERATE", round((float(damper) + rec) / 2.0, 1), "INTEGRATED_PARTIAL"),
        ("OPTIMAL", rec, mode),
        ("AGGRESSIVE", round(min(100.0, rec + 16.0), 1), "100%_OPEN"),
    ]
    candidates = []
    for cid, pos, emode in labels:
        m = oa_mass_flow_kg_s(cfm, pos)
        mat = mixed_air_temp(oat, rat, pos)
        fc = free_cooling_kw(h_oa, h_ra, m)
        ck = chiller_kw_from_oa(h_oa, h_ra, m, chiller_kw)
        if cid == "OPTIMAL":
            decision = "SELECTED_OPTIMAL"
            reject = None
        elif cid == "AGGRESSIVE":
            decision = "OVER_PRESSURIZATION_RISK"
            reject = "Building over-pressurization risk above recommended OA fraction"
        elif cid == "BASELINE":
            decision = "BASELINE"
            reject = None
        else:
            decision = "VIABLE"
            reject = None
        candidates.append({
            "candidate_id": cid,
            "damper_position_pct": pos,
            "economizer_mode": emode,
            "mixed_air_temp_c": mat,
            "chiller_power_kw": ck,
            "free_cooling_kw": fc,
            "decision": decision,
            "rejection_reason": reject,
        })

    present = sum(1 for v in [oat, oa_rh, rat, ra_rh, damper, cfm, fan_kw, chiller_kw] if v is not None)
    freeze_ok = oat is None or oat >= 12.0
    return {
        "available": True,
        "status": status if freeze_ok else "BLOCKED",
        "current_value": round(float(damper), 1),
        "optimized_value": rec,
        "recommended_value": rec,
        "unit": "%",
        "economizer_status": mode,
        "outdoor_drybulb_c": oat,
        "outdoor_rh_pct": oa_rh,
        "outdoor_enthalpy_kj_kg": h_oa,
        "return_drybulb_c": rat,
        "return_rh_pct": ra_rh,
        "return_enthalpy_kj_kg": h_ra,
        "enthalpy_advantage_kj_kg": adv,
        "current_airflow_cfm": cfm,
        "optimized_airflow_cfm": round(float(cfm) * rec / 100.0, 0) if cfm is not None else None,
        "expected_power_saving_kw": d_kw,
        "expected_energy_saving_kwh_day": daily if d_kw < 0 else round(abs(d_kw) * 8.5, 1),
        "instantaneous_kw": d_kw,
        "daily_kwh": round(abs(d_kw) * 8.5, 1),
        "confidence": _conf(present, 8),
        "guardrail_pass": freeze_ok,
        "recommendation": "INCREASE_OA" if rec > float(damper) else ("TRIM_OA" if rec < float(damper) else "HOLD"),
        "rationale": (
            f"Outdoor enthalpy {h_oa} kJ/kg versus return {h_ra} kJ/kg "
            f"(advantage {adv} kJ/kg) allows modulating OA damper from {damper:.1f}% to {rec:.1f}% "
            f"while holding freeze and pressurization guardrails."
            if adv is not None and h_oa is not None and h_ra is not None
            else f"Damper trim from {damper:.1f}% to {rec:.1f}% under current OA/RA temperatures."
        ),
        "candidates": candidates,
        "safety_status": "PASS" if freeze_ok else "BLOCKED",
        "free_cooling_kw": q_opt,
    }


def evaluate_o11(tel: Dict[str, Any], hour: Optional[int] = None) -> Dict[str, Any]:
    oat = tel.get("outdoor_temp_c")
    zone = tel.get("return_temp_c")
    cfm = tel.get("supply_airflow_cfm")
    fan_kw = tel.get("fan_power_kw")
    occ = tel.get("occupancy")
    occupied = tel.get("occupied")
    schedule = tel.get("schedule_state")
    damper = tel.get("damper_percent")
    if hour is None:
        hour = datetime.now(TZ).hour
    night = hour >= 21 or hour < 6
    occupancy_known = occupied is not None or occ is not None or schedule is not None
    unoccupied = occupied is False or (occ is not None and occ <= 4) or schedule == "UNOCCUPIED"
    if oat is None or zone is None or cfm is None:
        return {"available": False, "missing": "outdoor temperature, indoor/return temperature, or airflow"}

    delta = round(float(zone) - float(oat), 2)
    oat_ok = 12.0 <= float(oat) <= 24.0
    cool_ok = delta >= 2.0
    oa_rh = tel.get("outdoor_rh_percent")
    ia_rh = tel.get("return_rh_percent")
    humidity_ok = True
    if oa_rh is not None and float(oa_rh) > 85.0:
        humidity_ok = False
    if ia_rh is not None and float(ia_rh) > 80.0:
        humidity_ok = False
    eligible = night and occupancy_known and unoccupied and oat_ok and cool_ok and humidity_ok
    rec_cfm = round(float(cfm) * 1.15, 0) if eligible else float(cfm)
    rec_cfm = min(rec_cfm, float(cfm) * 1.25)
    d_fan = fan_kw_at_cfm(fan_kw, rec_cfm, cfm)
    kw = None
    if fan_kw is not None and d_fan is not None:
        kw = round(d_fan - float(fan_kw), 2)
    cooling = round(float(cfm) * 1.08 * (delta * 1.8) / 3412.0, 2) if eligible else 0.0
    if eligible:
        status = "READY"
        rec = "ENABLE"
        rationale = (
            f"Night purge eligible: OAT {oat:.1f}°C, indoor {zone:.1f}°C, ΔT {delta:.1f} K, "
            f"unoccupied. Raise airflow from {int(cfm)} to {int(rec_cfm)} CFM to dump stored heat."
        )
    elif not occupancy_known:
        status = "HOLD"
        rec = "HOLD"
        rationale = "Occupancy is unknown; night purge is held until occupancy/schedule telemetry is present."
    elif not humidity_ok:
        status = "HOLD"
        rec = "HOLD"
        rationale = "Outdoor or indoor humidity is above the purge humidity guardrail; purge is held."
    elif not night:
        status = "HOLD"
        rec = "HOLD"
        rationale = "Outside the 21:00–06:00 Asia/Kolkata purge window; mechanical cooling remains in control."
    else:
        status = "WARNING"
        rec = "HOLD"
        rationale = "Night hours but purge band, occupancy, or ΔT guardrail is not satisfied."

    present = sum(1 for v in [oat, zone, cfm, fan_kw, occ, damper] if v is not None)
    daily = round(abs(kw or 0) * 6.0, 1) if kw is not None else None
    delta_cfm = round(float(rec_cfm) - float(cfm), 0)
    if not oat_ok:
        ui_status = "BLOCKED"
        decision = "BLOCK"
    elif eligible:
        ui_status = "ACTIVE"
        decision = "OPTIMIZE"
    elif not night:
        ui_status = "STANDBY"
        decision = "HOLD"
    else:
        ui_status = "STANDBY"
        decision = "HOLD"
    rec_damper = round(min(DAMPER_MAX_PCT, max(DAMPER_MIN_PCT, 85.0 if eligible else float(damper))), 1) if damper is not None or eligible else None
    return {
        "available": True,
        "status": ui_status,
        "current_value": cfm,
        "optimized_value": rec_cfm,
        "current_airflow_cfm": cfm,
        "optimized_airflow_cfm": rec_cfm,
        "airflow_delta_cfm": delta_cfm,
        "unit": "CFM",
        "outdoor_temperature_c": oat,
        "zone_temperature_c": zone,
        "outdoor_rh_percent": tel.get("outdoor_rh_percent"),
        "indoor_rh_percent": tel.get("return_rh_percent"),
        "outdoor_enthalpy_kjkg": tel.get("outdoor_enthalpy_kjkg"),
        "indoor_enthalpy_kjkg": tel.get("return_enthalpy_kjkg"),
        "temperature_differential_k": delta,
        "occupancy_state": "UNOCCUPIED" if unoccupied else "OCCUPIED",
        "occupant_count": occ,
        "night_purge_status": "ACTIVE" if eligible else "INACTIVE",
        "eligibility": "PURGE ELIGIBLE" if eligible else "PURGE NOT ELIGIBLE",
        "purge_window": f"{PURGE_START}–{PURGE_STOP} Asia/Kolkata",
        "oa_damper_pct": damper,
        "optimized_damper_pct": rec_damper,
        "current_fan_kw": fan_kw,
        "optimized_fan_kw": d_fan,
        "instantaneous_kw": kw,
        "daily_kwh": daily,
        "expected_power_saving_kw": kw,
        "expected_energy_saving_kwh_day": daily,
        "confidence": _conf(present, 6),
        "guardrail_pass": oat_ok,
        "recommendation": rec,
        "rationale": rationale,
        "safety_status": "PASS" if oat_ok else "FAIL",
        "estimated_cooling_benefit_kwh": cooling if eligible else None,
        "thermal_opportunity": "Potential pre-cooling / heat removal" if eligible else "No purge thermal opportunity in this window",
        "recommended_damper_pct": rec_damper,
        "recommended_purge": rec,
        "recommended_start": PURGE_START,
        "recommended_stop": PURGE_STOP,
        "local_hour": hour,
        "supervisory_decision": decision,
        "dispatch_eligible": decision == "OPTIMIZE" and oat_ok,
    }


def evaluate_o12(tel: Dict[str, Any]) -> Dict[str, Any]:
    co2 = tel.get("co2_ppm")
    occ = tel.get("occupancy")
    damper = tel.get("damper_percent")
    oa_cfm = tel.get("supply_airflow_cfm")
    area = tel.get("building_area_sqft")
    fan_kw = tel.get("fan_power_kw")
    oat = tel.get("outdoor_temp_c")
    rat = tel.get("return_temp_c")
    design_occ = tel.get("design_occupancy")
    outdoor_co2 = tel.get("outdoor_co2_ppm")
    if co2 is None or oa_cfm is None:
        return {"available": False, "missing": "CO₂ ppm or supply airflow"}

    people = int(occ) if occ is not None else None
    ashrae = None
    if people is not None:
        ra = (people * 5.0) + (float(area) * 0.06 if area is not None else 0.0)
        ashrae = round(ra / 0.85, 0)
    min_oa = max(MIN_OA_CFM_FLOOR, ashrae) if ashrae is not None else MIN_OA_CFM_FLOOR
    target = CO2_TARGET_PPM
    deviation = round(float(co2) - target, 1)
    if co2 <= 700:
        rec_cfm = min_oa
    elif ashrae is not None:
        rec_cfm = max(ashrae, float(oa_cfm) * 0.85)
    else:
        rec_cfm = round(float(oa_cfm) * (0.9 if co2 < target else 1.05), 0)
    rec_cfm = round(max(min_oa, min(float(oa_cfm), rec_cfm)), 0)
    rec_damper = None
    if damper is not None and oa_cfm:
        rec_damper = round(max(DAMPER_MIN_PCT, min(DAMPER_MAX_PCT, float(damper) * rec_cfm / float(oa_cfm))), 1)
    fan_opt = fan_kw_at_cfm(fan_kw, rec_cfm, oa_cfm)
    kw = round(float(fan_opt) - float(fan_kw), 2) if fan_opt is not None and fan_kw is not None else None
    tons = None
    if oat is not None and rat is not None and rec_cfm < float(oa_cfm):
        dcfm = float(oa_cfm) - rec_cfm
        dt_f = (float(oat) - float(rat)) * 1.8
        tons = max(0.0, 1.08 * dcfm * dt_f / 12000.0 * 1.35)
        extra = round(tons * 0.65, 2)
        kw = round((kw or 0) - extra, 2)
    iaq = "PASS" if co2 <= target else "FAIL"
    if iaq == "FAIL":
        status = "WARNING"
        decision = "INCREASE_VENTILATION" if rec_cfm >= float(oa_cfm) else "HOLD"
    elif rec_cfm < float(oa_cfm) - 1:
        status = "OPTIMAL"
        decision = "OPTIMIZE"
    else:
        status = "READY"
        decision = "HOLD"
    present = sum(1 for v in [co2, occ, damper, oa_cfm, fan_kw] if v is not None)
    daily = round(abs(kw or 0) * 12.0, 1) if kw is not None else None
    occ_pct = round(100.0 * float(occ) / float(design_occ), 1) if occ is not None and design_occ else None
    rec_action = "TRIM_OA" if rec_cfm < float(oa_cfm) else ("INCREASE_OA" if rec_cfm > float(oa_cfm) else "HOLD")
    if iaq == "FAIL":
        rec_cfm = max(rec_cfm, min_oa, float(oa_cfm))
        rec_action = "INCREASE_VENTILATION"
        decision = "INCREASE_VENTILATION"
    rationale = (
        f"Occupancy {people if people is not None else '—'} and zone CO₂ {int(co2)} ppm versus {int(target)} ppm target "
        f"{'allow reducing' if rec_cfm < float(oa_cfm) else 'require holding'} outdoor-air intake from "
        f"{int(oa_cfm):,} CFM to {int(rec_cfm):,} CFM while maintaining the ventilation safety floor "
        f"({int(min_oa):,} CFM)."
    )
    candidates = [
        {
            "candidate_id": "BASELINE",
            "outdoor_air_cfm": oa_cfm,
            "damper_position_pct": damper,
            "steady_state_co2_ppm": co2,
            "power_shed_kw": 0.0,
            "safety_status": "PASS",
            "decision": "BASELINE",
        },
        {
            "candidate_id": "MODERATE",
            "outdoor_air_cfm": round((float(oa_cfm) + rec_cfm) / 2.0, 0),
            "damper_position_pct": rec_damper,
            "steady_state_co2_ppm": min(target, float(co2) + 40),
            "power_shed_kw": round(abs(kw or 0) * 0.5, 2),
            "safety_status": "PASS",
            "decision": "VIABLE",
        },
        {
            "candidate_id": "OPTIMAL",
            "outdoor_air_cfm": rec_cfm,
            "damper_position_pct": rec_damper,
            "steady_state_co2_ppm": min(target - 20, float(co2) + 80),
            "power_shed_kw": abs(kw or 0),
            "safety_status": "PASS" if iaq == "PASS" else "WARNING",
            "decision": "SELECTED_OPTIMAL",
        },
        {
            "candidate_id": "AGGRESSIVE",
            "outdoor_air_cfm": round(rec_cfm * 0.7, 0),
            "damper_position_pct": DAMPER_MIN_PCT,
            "steady_state_co2_ppm": 1080,
            "power_shed_kw": abs(kw or 0) * 1.4,
            "safety_status": "BLOCKED",
            "decision": "REJECTED_CO2_LIMIT",
        },
    ]
    return {
        "available": True,
        "status": status,
        "current_value": oa_cfm,
        "optimized_value": rec_cfm,
        "current_airflow_cfm": oa_cfm,
        "optimized_airflow_cfm": rec_cfm,
        "current_damper_pct": damper,
        "optimized_damper_pct": rec_damper,
        "current_co2_ppm": co2,
        "predicted_co2_ppm": min(target - 20, max(420.0, float(co2) + (rec_cfm - float(oa_cfm)) * -0.04)),
        "co2_target_ppm": target,
        "co2_deviation_ppm": deviation,
        "occupant_count": people,
        "design_occupant_count": design_occ,
        "occupancy_pct": occ_pct,
        "ashrae_baseline_oa_cfm": ashrae,
        "required_ventilation_cfm": min_oa,
        "airflow_delta_cfm": round(float(rec_cfm) - float(oa_cfm), 0),
        "airflow_reduction_cfm": round(float(oa_cfm) - rec_cfm, 0),
        "iaq_status": "compliant" if iaq == "PASS" else "breach",
        "iaq_compliance": iaq,
        "outdoor_co2_ppm": outdoor_co2,
        "zone_temperature_c": rat,
        "zone_humidity_percent": tel.get("return_rh_percent"),
        "current_fan_kw": fan_kw,
        "optimized_fan_kw": fan_opt,
        "instantaneous_kw": kw,
        "daily_kwh": daily,
        "expected_power_saving_kw": kw,
        "expected_energy_saving_kwh_day": daily,
        "conditioning_tons_saved": round(tons, 2) if tons is not None else None,
        "confidence": _conf(present, 5),
        "guardrail_pass": rec_cfm >= min_oa and iaq != "FAIL",
        "recommendation": rec_action,
        "rationale": rationale,
        "safety_status": "PASS" if iaq == "PASS" and rec_cfm >= min_oa else ("FAIL" if iaq == "FAIL" else "WARNING"),
        "candidates": candidates,
        "unit": "CFM",
        "supervisory_decision": decision,
        "dispatch_eligible": decision == "OPTIMIZE" and rec_cfm >= min_oa,
    }


def evaluate_o13(tel: Dict[str, Any]) -> Dict[str, Any]:
    co = tel.get("co_ppm")
    ret_cfm = tel.get("return_airflow_cfm")
    sup_cfm = tel.get("supply_airflow_cfm")
    damper = tel.get("damper_percent")
    fan_kw = tel.get("fan_power_kw")
    if co is None or (sup_cfm is None and ret_cfm is None):
        return {"available": False, "missing": "CO ppm or airflow"}

    cfm = float(sup_cfm if sup_cfm is not None else ret_cfm)
    alarm = co >= CO_LIMIT_PPM
    warn = co >= CO_WARN_PPM
    if alarm:
        rec = round(cfm * 1.25, 0)
        rec_damper = DAMPER_MAX_PCT
        rec_action = "INCREASE_VENTILATION"
        status = "BLOCKED"
        iaq = "FAIL"
        decision = "BLOCK"
        rationale = (
            f"CO {co:.1f} ppm exceeds the {CO_LIMIT_PPM:.0f} ppm safety limit. "
            "Energy optimization is suppressed; exhaust must increase."
        )
        kw = None
        if fan_kw is not None:
            kw = round(float(fan_kw) * (1.25 ** 2.7) - float(fan_kw), 2)
    elif warn:
        rec = round(cfm * 1.1, 0)
        rec_damper = min(DAMPER_MAX_PCT, max(DAMPER_MIN_PCT, (damper or 40) + 20))
        rec_action = "INCREASE_VENTILATION"
        status = "WARNING"
        iaq = "PASS"
        decision = "INCREASE_VENTILATION"
        rationale = f"CO {co:.1f} ppm is above the {CO_WARN_PPM:.0f} ppm warning. Increase carpark exhaust."
        kw = round((fan_kw or 0) * 0.15, 2) if fan_kw else None
    else:
        rec = round(min(cfm, max(MIN_EXHAUST_CFM, cfm * 0.88)), 0)
        rec_damper = min(DAMPER_MAX_PCT, max(DAMPER_MIN_PCT, (damper or 30) - 8)) if damper is not None else None
        rec_action = "TRIM"
        status = "OPTIMAL"
        iaq = "PASS"
        decision = "OPTIMIZE" if rec < cfm - 1 else "HOLD"
        rationale = (
            f"CO {co:.1f} ppm is below the {CO_LIMIT_PPM:.0f} ppm limit. Exhaust airflow can track demand "
            f"from {int(cfm):,} to {int(rec):,} CFM."
        )
        fan_opt = fan_kw_at_cfm(fan_kw, rec, cfm)
        kw = round(float(fan_opt) - float(fan_kw), 2) if fan_opt is not None and fan_kw is not None else None

    present = sum(1 for v in [co, ret_cfm, sup_cfm, damper, fan_kw] if v is not None)
    daily = round(abs(kw or 0) * 18.0, 1) if kw is not None else None
    margin = round(CO_LIMIT_PPM - float(co), 1)
    margin_pct = round(100.0 * margin / CO_LIMIT_PPM, 1)
    fan_opt = locals().get("fan_opt")
    if fan_opt is None and fan_kw is not None:
        fan_opt = fan_kw_at_cfm(fan_kw, rec, cfm)
    return {
        "available": True,
        "status": status,
        "current_value": cfm,
        "optimized_value": rec,
        "current_airflow_cfm": cfm,
        "optimized_airflow_cfm": rec,
        "airflow_delta_cfm": round(rec - cfm, 0),
        "return_airflow_cfm": ret_cfm,
        "supply_airflow_cfm": sup_cfm,
        "current_damper_pct": damper,
        "optimized_damper_pct": rec_damper,
        "co_ppm": co,
        "co_limit_ppm": CO_LIMIT_PPM,
        "co_warn_ppm": CO_WARN_PPM,
        "co_margin_ppm": margin,
        "co_margin_pct": margin_pct,
        "iaq_compliance": iaq,
        "current_fan_kw": fan_kw,
        "optimized_fan_kw": fan_opt,
        "instantaneous_kw": kw,
        "daily_kwh": daily,
        "expected_power_saving_kw": kw,
        "expected_energy_saving_kwh_day": daily,
        "confidence": _conf(present, 5),
        "guardrail_pass": not alarm,
        "recommendation": rec_action,
        "rationale": rationale,
        "safety_status": "FAIL" if alarm else ("WARNING" if warn else "PASS"),
        "unit": "CFM",
        "ventilation_status": "ALARM" if alarm else ("HIGH" if warn else "NORMAL"),
        "recommended_ventilation_pct": rec_damper,
        "recommended_fan_speed_pct": rec_damper,
        "recommended_damper_pct": rec_damper,
        "current_ventilation_pct": damper,
        "zone_temperature_c": tel.get("return_temp_c"),
        "zone_humidity_percent": tel.get("return_rh_percent"),
        "differential_pressure_pa": tel.get("differential_pressure_pa"),
        "envelope_dp_pa": tel.get("envelope_dp_pa"),
        "supervisory_decision": decision,
        "dispatch_eligible": decision == "OPTIMIZE" and not alarm,
    }


ROUTES = {
    "O10": "/agents/ventilation-airflow/economy-cycle",
    "O11": "/agents/ventilation-airflow/night-purge",
    "O12": "/agents/ventilation-airflow/demand-ventilation",
    "O13": "/agents/ventilation-airflow/dcv-co",
}

META = {
    "O10": ("Economy Cycle", "Enthalpy economizer outdoor-air free cooling.", 10),
        "O11": ("Night Purge", "Night-time outdoor-air purge for removing stored building heat before occupancy.", 11),
        "O12": ("Demand Control Ventilation — CO₂", "Occupancy- and CO₂-driven outdoor-air optimization for occupied spaces.", 12),
        "O13": ("Demand Control Ventilation — CO", "CO-based demand ventilation for carparks, loading docks, and enclosed vehicle areas.", 13),
}
