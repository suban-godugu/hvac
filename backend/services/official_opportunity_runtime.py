"""Sample existing BMS telemetry, run official O11–O20 agents, persist, return API state."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.agents.official_opportunities._common import freshness, telemetry_age_seconds
from backend.agents.official_opportunities.o11_night_purge import evaluate_night_purge
from backend.agents.official_opportunities.o13_dcv_co import evaluate_dcv_co
from backend.agents.official_opportunities.o17_energy_planning import evaluate_energy_planning
from backend.agents.official_opportunities.o18_training import evaluate_training
from backend.agents.official_opportunities.o19_maintenance import evaluate_maintenance
from backend.agents.official_opportunities.o20_control_software import evaluate_control_software
from backend.services.opportunity_persist_service import (
    persist_co_measurement,
    persist_execution,
    persist_optimization,
    persist_safety_check,
    persist_ventilation_points,
    persist_vs_points,
)
from backend.services.om_persist_service import (
    get_o17_state,
    get_o18_state,
    get_o19_state,
    get_o20_state,
)
from backend.services.ventilation_telemetry_service import ventilation_telemetry_service
from backend.services.variable_speed_telemetry_service import vs_telemetry_service

_last_persist: Dict[str, float] = {}
PERSIST_EVERY_S = 20.0


def _v(points: Dict[str, Any], key: str) -> Optional[float]:
    row = points.get(key)
    if not row:
        return None
    if (row.get("quality") or "").upper() not in ("GOOD", "LIVE"):
        return None
    try:
        return float(row["value"])
    except (KeyError, TypeError, ValueError):
        return None


def _ts(points: Dict[str, Any]) -> Optional[str]:
    for row in points.values():
        if isinstance(row, dict) and row.get("timestamp"):
            return row["timestamp"]
    return datetime.now(timezone.utc).isoformat()


def _should_persist(oid: str) -> bool:
    now = time.time()
    last = _last_persist.get(oid, 0)
    if now - last < PERSIST_EVERY_S:
        return False
    _last_persist[oid] = now
    return True


def _attach_meta(result: Dict[str, Any], sampled: Dict[str, Any], started: float) -> Dict[str, Any]:
    from backend.services.hvac_safety_contract import is_demo_source

    raw = sampled.get("_raw") or {}
    sources = [row.get("source") for row in raw.values() if isinstance(row, dict)]
    demo = any(is_demo_source(s) for s in sources) or is_demo_source(sampled.get("source"))
    age = telemetry_age_seconds(sampled) or max(0.0, time.time() - started)
    result["telemetry_age_seconds"] = round(age, 2)
    if demo:
        result["live"] = False
        result["freshness"] = "SIMULATED"
        result["agent_status"] = "ONLINE"
        result["bms_status"] = "DISCONNECTED"
        if result.get("status") in (None, "AWAITING_TELEMETRY"):
            result["status"] = "SIMULATION"
        result["source"] = "SIMULATION"
    else:
        result["freshness"] = freshness(age) if result.get("live") else "OFFLINE"
        result["agent_status"] = result.get("agent_status") or ("ONLINE" if result.get("live") else "OFFLINE")
        result["bms_status"] = "CONNECTED" if result.get("live") else "UNKNOWN"
    result["execution_time_ms"] = int((time.time() - started) * 1000)
    result["last_execution"] = result.get("evaluated_at")
    return result


def sample_o11() -> Dict[str, Any]:
    pts = ventilation_telemetry_service.get_all_points()
    return {
        "OAT": _v(pts, "WEATHER.OutdoorDryBulb"),
        "RH": _v(pts, "WEATHER.OutdoorRH"),
        "ZONE_TEMP": _v(pts, "ZONE.AvgTemp"),
        "RAT": _v(pts, "AHU-01.ReturnAirTemp"),
        "SAT": _v(pts, "AHU-01.SupplyAirTemp"),
        "OA_DAMPER": _v(pts, "AHU-01.OutdoorAirDamper"),
        "FAN_STATE": _v(pts, "AHU-01.SupplyFanState"),
        "FAN_SPEED": _v(pts, "AHU-01.SupplyFanSpeed"),
        "OCCUPANCY": _v(pts, "ZONE.OccupantCount"),
        "ECONOMIZER": _v(pts, "AHU-01.EconomizerEnable"),
        "AHU_AVAILABLE": _v(pts, "AHU-01.SupplyFanState"),
        "AIRFLOW_CFM": _v(pts, "AHU-01.SupplyAirflow"),
        "PURGE_STATE": _v(pts, "AHU-01.PurgeState"),
        "timestamp": _ts(pts),
        "_raw": pts,
    }


def sample_o13() -> Dict[str, Any]:
    pts = ventilation_telemetry_service.get_all_points()
    return {
        "CO_PPM": _v(pts, "PARK.CO"),
        "FAN_STATE": _v(pts, "PARK.FanState"),
        "FAN_SPEED": _v(pts, "PARK.FanSpeed"),
        "DAMPER_PCT": _v(pts, "PARK.Damper"),
        "AIRFLOW_CFM": _v(pts, "PARK.Airflow"),
        "ZONE_ID": "PARK-L1",
        "CO_TREND": "STABLE",
        "timestamp": _ts(pts),
        "_raw": pts,
    }


def sample_o15() -> Dict[str, Any]:
    from backend.services.o15_service import sample_o15 as _sample

    return _sample()


def evaluate_o15(persist: bool = True) -> Dict[str, Any]:
    from backend.services.o15_service import evaluate_o15 as _eval

    return _eval(persist=persist)


def sample_o16() -> Dict[str, Any]:
    from backend.services.o16_service import sample_o16 as _sample

    return _sample()


def evaluate_o16(persist: bool = True) -> Dict[str, Any]:
    from backend.services.o16_service import evaluate_o16 as _eval

    return _eval(persist=persist)


def _persist_vent(oid: str, equipment_id: str, mapping: List[tuple], source: str = "SIMULATION") -> None:
    points = []
    for sensor_type, value, unit in mapping:
        if value is None:
            continue
        points.append({"sensor_type": sensor_type, "value": value, "unit": unit, "quality": "GOOD", "source": source})
    if points:
        persist_ventilation_points(oid, equipment_id, points)


def evaluate_o11(persist: bool = True) -> Dict[str, Any]:
    started = time.time()
    sampled = sample_o11()
    result = evaluate_night_purge(sampled)
    result["telemetry"] = {
        k: {"value": sampled[k], "unit": u}
        for k, u in [
            ("OAT", "°C"),
            ("ZONE_TEMP", "°C"),
            ("RAT", "°C"),
            ("SAT", "°C"),
            ("OA_DAMPER", "%"),
            ("FAN_STATE", ""),
            ("FAN_SPEED", "RPM"),
            ("OCCUPANCY", "Persons"),
            ("RH", "%"),
        ]
        if sampled.get(k) is not None
    }
    if persist and sampled.get("OAT") is not None and _should_persist("O11"):
        persist_execution("O11", "O11_NIGHT_PURGE", confidence=result.get("confidence"), execution_time_ms=int((time.time() - started) * 1000))
        _persist_vent(
            "O11",
            "AHU-01",
            [
                ("OAT", sampled.get("OAT"), "C"),
                ("ZONE_TEMP", sampled.get("ZONE_TEMP"), "C"),
                ("RAT", sampled.get("RAT"), "C"),
                ("SAT", sampled.get("SAT"), "C"),
                ("OA_DAMPER", sampled.get("OA_DAMPER"), "%"),
                ("FAN_STATE", sampled.get("FAN_STATE"), ""),
                ("FAN_SPEED", sampled.get("FAN_SPEED"), "RPM"),
                ("OCCUPANCY", sampled.get("OCCUPANCY"), "Persons"),
                ("ECONOMIZER", sampled.get("ECONOMIZER"), ""),
                ("PURGE_STATE", sampled.get("PURGE_STATE"), ""),
            ],
        )
        persist_optimization(
            "O11",
            {
                "current_value": result.get("current_value"),
                "optimized_value": result.get("optimized_value"),
                "energy_impact": result.get("energy_impact"),
                "confidence": result.get("confidence"),
                "reason": result.get("reason"),
                "status": result.get("status") or "PROPOSED",
            },
        )
        for chk in result.get("safety_checks") or []:
            persist_safety_check("O11", chk["check_name"], chk.get("actual_value"), chk.get("minimum"), chk.get("maximum"), chk["result"], chk["reason"])
    return _attach_meta(result, sampled, started)


def evaluate_o13(persist: bool = True) -> Dict[str, Any]:
    started = time.time()
    sampled = sample_o13()
    result = evaluate_dcv_co(sampled)
    result["co"] = {
        "zone_id": sampled.get("ZONE_ID"),
        "co_ppm": sampled.get("CO_PPM"),
        "co_trend": sampled.get("CO_TREND"),
        "fan_state": sampled.get("FAN_STATE"),
        "fan_speed": sampled.get("FAN_SPEED"),
        "damper_pct": sampled.get("DAMPER_PCT"),
        "airflow_cfm": sampled.get("AIRFLOW_CFM"),
    } if sampled.get("CO_PPM") is not None else None
    if persist and sampled.get("CO_PPM") is not None and _should_persist("O13"):
        persist_execution("O13", "O13_DCV_CO", confidence=result.get("confidence"), execution_time_ms=int((time.time() - started) * 1000))
        persist_co_measurement(
            {
                "zone_id": sampled.get("ZONE_ID") or "PARK-L1",
                "co_ppm": sampled["CO_PPM"],
                "co_trend": sampled.get("CO_TREND"),
                "fan_state": sampled.get("FAN_STATE"),
                "fan_speed": sampled.get("FAN_SPEED"),
                "damper_pct": sampled.get("DAMPER_PCT"),
                "airflow_cfm": sampled.get("AIRFLOW_CFM"),
                "quality": "GOOD",
                "source": "SIMULATION",
            }
        )
        persist_optimization(
            "O13",
            {
                "current_value": result.get("current_value"),
                "optimized_value": result.get("optimized_value"),
                "energy_impact": result.get("energy_impact"),
                "confidence": result.get("confidence"),
                "reason": result.get("reason"),
                "status": result.get("status") or "PROPOSED",
            },
        )
    return _attach_meta(result, sampled, started)


def sample_o14() -> Dict[str, Any]:
    from backend.services.o14_service import sample_o14 as _sample

    return _sample()


def evaluate_o14(persist: bool = True) -> Dict[str, Any]:
    from backend.services.o14_service import evaluate_o14 as _eval

    return _eval(persist=persist)


def evaluate_o17(persist: bool = True) -> Dict[str, Any]:
    started = time.time()
    stored = get_o17_state()
    snapshot = {
        "power_kw": stored.get("power_kw"),
        "baseline_kw": stored.get("baseline_kw"),
        "forecast_kw": stored.get("forecast"),
        "peak_demand_kw": None,
        "expected_cost_usd": None,
        "daily_target_kwh": None,
        "carbon_kg": stored.get("carbon"),
        "recommendations": [stored.get("recommendation")] if stored.get("recommendation") else [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    result = evaluate_energy_planning(snapshot)
    if persist and result.get("live") and snapshot.get("power_kw") is not None and _should_persist("O17"):
        persist_execution("O17", "O17_ENERGY_PLANNING", confidence=result.get("confidence"), execution_time_ms=int((time.time() - started) * 1000))
    return _attach_meta(result, snapshot, started)


def evaluate_o18() -> Dict[str, Any]:
    started = time.time()
    stored = get_o18_state()
    result = evaluate_training({"programs": stored.get("programs") or [], "completions": [stored["latest_completion"]] if stored.get("latest_completion") else []})
    result.update({k: stored[k] for k in stored if k not in result})
    result["live"] = result.get("live")
    return _attach_meta(result, {"timestamp": datetime.now(timezone.utc).isoformat()}, started)


def evaluate_o19() -> Dict[str, Any]:
    started = time.time()
    stored = get_o19_state()
    result = evaluate_maintenance({
        "findings": stored.get("findings") or stored.get("work_orders") or [],
        "performance": stored.get("performance"),
        "filter_dp_rise_pct": (stored.get("performance") or {}).get("filter_dp_rise_pct") if isinstance(stored.get("performance"), dict) else None,
        "equipment_health_pct": (stored.get("performance") or {}).get("health") if isinstance(stored.get("performance"), dict) else None,
    })
    return _attach_meta(result, {"timestamp": datetime.now(timezone.utc).isoformat()}, started)


def evaluate_o20() -> Dict[str, Any]:
    started = time.time()
    stored = get_o20_state()
    ctrl = stored.get("controller") or {}
    result = evaluate_control_software({"controller": ctrl})
    return _attach_meta(result, {"timestamp": datetime.now(timezone.utc).isoformat()}, started)


def agent_status(oid: str, fn) -> Dict[str, Any]:
    try:
        state = fn(persist=False)
    except TypeError:
        state = fn()
    return {
        "opportunity_id": oid,
        "agent_status": state.get("agent_status"),
        "health": state.get("agent_status"),
        "last_execution": state.get("last_execution"),
        "last_successful_execution": state.get("last_execution") if state.get("live") else None,
        "last_telemetry_timestamp": (state.get("telemetry") or {}).get("OAT", {}).get("timestamp") if oid == "O11" else state.get("evaluated_at"),
        "execution_duration_ms": state.get("execution_time_ms"),
        "error": None if state.get("live") else state.get("reason"),
        "freshness": state.get("freshness"),
    }


def optimization_history(opportunity_id: str) -> Dict[str, Any]:
    from database.session import SessionLocal
    from database.models_opportunities import OpportunityOptimizationResultDB

    db = SessionLocal()
    try:
        rows = (
            db.query(OpportunityOptimizationResultDB)
            .filter(OpportunityOptimizationResultDB.opportunity_id == opportunity_id)
            .order_by(OpportunityOptimizationResultDB.timestamp.desc())
            .limit(48)
            .all()
        )
        return {
            "opportunity_id": opportunity_id,
            "points": [
                {
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                    "current_value": r.current_value,
                    "optimized_value": r.optimized_value,
                    "energy_impact": r.energy_impact,
                    "confidence": r.confidence,
                    "status": r.status,
                    "reason": r.reason,
                }
                for r in reversed(rows)
            ],
        }
    finally:
        db.close()
