"""Official O11 Night Purge — evaluate only from provided telemetry (no sensor defaults)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict
from zoneinfo import ZoneInfo

from backend.agents.official_opportunities._common import agent_envelope, check, missing, num

REQUIRED = ["OAT", "ZONE_TEMP", "OA_DAMPER", "FAN_STATE", "OCCUPANCY"]
OAT_MIN_C = 12.0
OAT_MAX_C = 24.0
DELTA_MIN_C = 2.0
PURGE_WINDOW = (21, 6)  # local hour start inclusive, end exclusive
TZ = ZoneInfo("Asia/Kolkata")


def _local_hour(telemetry: Dict[str, Any]) -> int:
    raw = telemetry.get("local_hour")
    if raw is not None:
        return int(raw)
    ts = telemetry.get("timestamp")
    if ts:
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(TZ).hour
        except ValueError:
            pass
    return datetime.now(TZ).hour


def _in_window(hour: int) -> bool:
    start, end = PURGE_WINDOW
    if start > end:
        return hour >= start or hour < end
    return start <= hour < end


def evaluate_night_purge(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    absent = missing(telemetry, REQUIRED)
    if absent:
        return agent_envelope(
            "O11",
            False,
            recommendation="BLOCKED",
            reason=f"Missing required telemetry: {', '.join(absent)}",
            extra={"missing_points": absent},
        )

    oat = num(telemetry, "OAT")
    zone = num(telemetry, "ZONE_TEMP")
    rat = num(telemetry, "RAT")
    sat = num(telemetry, "SAT")
    damper = num(telemetry, "OA_DAMPER")
    fan_state = num(telemetry, "FAN_STATE")
    fan_speed = num(telemetry, "FAN_SPEED")
    occ = num(telemetry, "OCCUPANCY")
    economizer = num(telemetry, "ECONOMIZER")
    ahu = num(telemetry, "AHU_AVAILABLE")
    airflow = num(telemetry, "AIRFLOW_CFM")
    rh = num(telemetry, "RH")
    hour = _local_hour(telemetry)
    night = _in_window(hour)
    unoccupied = occ is not None and occ <= 4
    delta = (zone - oat) if oat is not None and zone is not None else None
    ahu_ok = ahu is None or ahu >= 1
    if ahu is None:
        ahu_ok = fan_state is not None and fan_state >= 1
    econ_ok = economizer is None or economizer >= 1
    fan_ok = fan_state is not None and fan_state >= 1
    oat_ok = oat is not None and OAT_MIN_C <= oat <= OAT_MAX_C
    cool_ok = delta is not None and delta >= DELTA_MIN_C

    safety = [
        check("Outdoor Air", bool(oat_ok), "OAT within purge band" if oat_ok else "OAT outside purge band", oat, OAT_MIN_C, OAT_MAX_C),
        check("AHU Availability", bool(ahu_ok), "AHU available" if ahu_ok else "AHU not available", ahu if ahu is not None else fan_state, 1, None),
        check("Economizer / OA Path", bool(econ_ok), "Outdoor-air path available" if econ_ok else "Economizer path unavailable", economizer, 1, None),
        check("Fan Operation", bool(fan_ok), "Fan available" if fan_ok else "Fan not available", fan_state, 1, None),
        check("Occupancy", bool(unoccupied), "Unoccupied" if unoccupied else "Occupied — purge not permitted", occ, None, 4),
        check("Operating Limits", bool(oat_ok and fan_ok and ahu_ok), "Operating limits satisfied" if oat_ok and fan_ok and ahu_ok else "Operating limit failed"),
    ]
    eligibility = [
        check("Zone Requires Cooling", bool(cool_ok), "Indoor-outdoor differential sufficient" if cool_ok else "Insufficient temperature differential", delta, DELTA_MIN_C, None),
        check("Schedule Window", night, "Within night purge window" if night else "Outside night purge hours", float(hour), 21, 6),
    ]
    safety_fail = any(c["result"] != "PASS" for c in safety)
    eligible = (not safety_fail) and all(c["result"] == "PASS" for c in eligibility)
    purge_active = (damper or 0) >= 60 and fan_ok and unoccupied
    rec = "HOLD"
    reason = "Night purge not eligible under current conditions."
    conf = 0.55
    rec_damper = damper
    start = "21:00"
    stop = "06:00"
    cooling = None
    energy = None

    if safety_fail and not unoccupied:
        rec = "BLOCKED"
        reason = "Occupancy does not permit outdoor-air purge."
        conf = 0.88
    elif safety_fail:
        rec = "BLOCKED"
        reason = "Safety validation failed; night purge is blocked."
        conf = 0.9
    elif eligible:
        rec = "ENABLE"
        rec_damper = 85.0
        hours_left = (24 - hour + 6) % 24 if hour >= 21 else max(1, 6 - hour)
        if delta is not None and airflow is not None:
            cooling = round(airflow * 1.08 * (delta * 1.8) * hours_left / 3412.0, 1)
            if fan_speed is not None:
                fan_kw = max(1.5, (fan_speed / 1450.0) * 8.4)
                energy = round(max(0.0, cooling * 0.28 - fan_kw * hours_left * 0.15), 2)
        reason = (
            f"Night purge eligible: OAT {oat:.1f}°C, zone {zone:.1f}°C, ΔT {delta:.1f}K, "
            f"unoccupied, OA path available."
        )
        conf = 0.92 if delta and delta >= 3 else 0.8
    elif not night:
        rec = "HOLD"
        reason = "Outside night purge window; mechanical cooling remains in control."
        conf = 0.7
    elif not oat_ok:
        rec = "BLOCKED"
        reason = "Outdoor air temperature is outside the purge safety band."
        conf = 0.9
    elif not cool_ok:
        rec = "HOLD"
        reason = "Outdoor air is not cooler than the zone enough to purge stored heat."
        conf = 0.75

    current = {
        "night_purge_status": "ACTIVE" if purge_active else "INACTIVE",
        "outdoor_temperature_c": oat,
        "outdoor_humidity_pct": rh,
        "zone_temperature_c": zone,
        "return_air_temperature_c": rat,
        "supply_air_temperature_c": sat,
        "temperature_differential_k": round(delta, 2) if delta is not None else None,
        "occupancy_state": "UNOCCUPIED" if unoccupied else "OCCUPIED",
        "ahu_availability": "AVAILABLE" if ahu_ok else "UNAVAILABLE",
        "economizer_availability": "AVAILABLE" if econ_ok else "UNAVAILABLE",
        "oa_damper_pct": damper,
        "fan_state": "ON" if fan_ok else "OFF",
        "fan_speed": fan_speed,
        "local_hour": hour,
    }
    optimized = {
        "recommended_purge": rec,
        "recommended_damper_pct": rec_damper,
        "recommended_start": start,
        "recommended_stop": stop,
        "estimated_cooling_benefit_kwh": cooling,
        "estimated_energy_impact_kwh": energy,
    }
    return agent_envelope(
        "O11",
        True,
        current_state=current,
        optimized_state=optimized,
        recommendation=rec,
        reason=reason,
        confidence=conf,
        energy_impact=energy,
        safety_checks=safety,
        extra={
            "current_value": zone,
            "optimized_value": rec_damper,
            "cooling_benefit_kwh": cooling,
            "eligibility": "ELIGIBLE" if eligible else "NOT_ELIGIBLE",
            "eligibility_checks": eligibility,
        },
    )
