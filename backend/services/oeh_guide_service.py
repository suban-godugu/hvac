"""Read-only OEH guide evaluate: official O1–O20 agents, never BMS write, never LIVE."""
from __future__ import annotations

from typing import Any, Dict, Optional

from backend.services.hvac_safety_contract import evaluate_dispatch, is_safe_mode
from backend.services.oeh_guide_catalog import catalog_item, normalize_oid
from backend.services.oeh_guide_physics import metrics_for, series_for

SIM = "SIMULATION"


def _sliders(item: Dict[str, Any], raw: Optional[Dict[str, Any]]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    incoming = raw or {}
    for sl in item["sliders"]:
        key = sl["key"]
        val = incoming.get(key, sl["default"])
        try:
            n = float(val)
        except (TypeError, ValueError):
            n = float(sl["default"])
        out[key] = max(float(sl["min"]), min(float(sl["max"]), n))
    return out


def _sim_tel(**extra: Any) -> Dict[str, Any]:
    body = {"source": SIM, "quality": "GOOD", "age_seconds": 5, "raw": "SIMULATION"}
    body.update(extra)
    return body


def _run_agent(oid: str, sliders: Dict[str, float], hour: int = 12) -> Dict[str, Any]:
    """Invoke the matching official engine with SIMULATION telemetry. persist=False. No dispatch."""
    tel = _sim_tel()
    try:
        if oid == "O10":
            from backend.agents.ventilation_airflow.o10_o13_engines import evaluate_o10
            from backend.services.oeh_guide_physics import oat

            tel.update(
                {
                    "outdoor_temp_c": oat(hour, sliders.get("oatMean", 18), 6),
                    "outdoor_rh_percent": 55,
                    "return_temp_c": 24,
                    "return_rh_percent": 50,
                    "damper_percent": 20,
                    "supply_airflow_cfm": 8000,
                    "fan_power_kw": 12,
                    "chiller_power_kw": 36,
                }
            )
            return evaluate_o10(tel)
        if oid == "O11":
            from backend.agents.official_opportunities.o11_night_purge import evaluate_night_purge

            tel.update(
                {
                    "OAT": sliders.get("overnightLow", 16),
                    "ZONE_TEMP": sliders.get("residual", 27),
                    "OA_DAMPER": 40,
                    "FAN_STATE": 1,
                    "OCCUPANCY": 0,
                    "ECONOMIZER": 1,
                    "AHU_AVAILABLE": 1,
                    "AIRFLOW_CFM": 7800,
                    "local_hour": 5 if hour < 8 else hour,
                }
            )
            return evaluate_night_purge(tel)
        if oid == "O12":
            from backend.agents.ventilation_airflow.o10_o13_engines import evaluate_o12

            tel.update(
                {
                    "co2_ppm": sliders.get("co2SP", 800),
                    "occupancy": int(sliders.get("peakOcc", 80)),
                    "damper_percent": 40,
                    "supply_airflow_cfm": 7000,
                    "outdoor_temp_c": 22,
                    "return_temp_c": 24,
                    "fan_power_kw": 8,
                }
            )
            return evaluate_o12(tel)
        if oid == "O13":
            from backend.agents.official_opportunities.o13_dcv_co import evaluate_dcv_co

            tel.update({"CO_PPM": 18, "FAN_SPEED": 80, "FAN_STATE": 1, "OCCUPANCY": 1})
            return evaluate_dcv_co(tel)
        if oid == "O14":
            from backend.agents.official_opportunities.o14_secondary_chw import evaluate_secondary_chw

            load = sliders.get("loadAmp", 75)
            tel.update(
                {
                    "INDEX_DP": 12.0,
                    "DP_SETPOINT": 15.0,
                    "MOST_OPEN_VALVE_PCT": max(40.0, 95.0 - (100 - load) * 0.4),
                    "SPEED_PCT": 80,
                    "COOLING_CALL": 1,
                    "LOAD_PCT": load,
                }
            )
            return evaluate_secondary_chw(tel, {"control_mode": "ADVISORY"})
        if oid == "O15":
            from backend.agents.official_opportunities.o15_air_cooled_hp import evaluate_air_cooled_hp
            from backend.services.oeh_guide_physics import oat

            amb = oat(hour, sliders.get("ambientMean", 20), 6)
            tel.update({"HEAD_PRESSURE": 180, "COND_TEMP": amb + 12, "OAT": amb, "FAN_SPEED": 70, "FAN_STATE": 1})
            return evaluate_air_cooled_hp(tel, {"control_mode": "ADVISORY"})
        if oid == "O16":
            from backend.agents.official_opportunities.o16_water_cooled_hp import evaluate_water_cooled_hp

            tel.update({"HEAD_PRESSURE": 170, "CW_FLOW": 80, "PUMP_SPEED_PCT": 90, "LOAD_PCT": sliders.get("loadAmp", 75)})
            return evaluate_water_cooled_hp(tel, {"control_mode": "ADVISORY"})
        if oid in ("O6", "O7", "O8"):
            from backend.agents.plant_control.o6_8_temperature_reset.engine import O6_8TemperatureResetAgent

            mode = {"O6": "HHW", "O7": "CHW", "O8": "CW"}[oid]
            raw = O6_8TemperatureResetAgent().optimize_mode(mode)
            raw = dict(raw or {})
            raw["opportunity_id"] = oid
            raw["opportunity_code"] = oid
            raw["live"] = False
            raw["source"] = SIM
            return raw
        if oid == "O17":
            from backend.agents.official_opportunities.o17_energy_planning import evaluate_energy_planning

            return evaluate_energy_planning(_sim_tel(plan_present=1, coordination=sliders.get("coordScore", 55)))
        if oid == "O18":
            from backend.agents.official_opportunities.o18_training import evaluate_training

            return evaluate_training(_sim_tel(training_coverage_pct=sliders.get("coverage", 50)))
        if oid == "O19":
            from backend.agents.official_opportunities.o19_maintenance import evaluate_maintenance

            return evaluate_maintenance(_sim_tel(checks_per_year=sliders.get("freq", 4)))
        if oid == "O20":
            from backend.agents.official_opportunities.o20_control_software import evaluate_control_software

            return evaluate_control_software(
                _sim_tel(access_control=sliders.get("accessCtrl", 1), backup_per_year=sliders.get("backupFreq", 4))
            )
        if oid in ("O1", "O2", "O3", "O4", "O5", "O9"):
            return {
                "opportunity_id": oid,
                "live": False,
                "source": SIM,
                "recommendation": "ADVISORY",
                "reason": "OEH guide evaluate uses official opportunity id; series from OEH teaching model plus this advisory stamp.",
                "agent_status": "ADVISORY",
            }
    except Exception as exc:
        return {
            "opportunity_id": oid,
            "live": False,
            "source": SIM,
            "recommendation": "HOLD",
            "reason": f"Guide agent snapshot unavailable ({type(exc).__name__}). Series remains OEH simulated.",
            "agent_status": "DEGRADED",
        }
    return {"opportunity_id": oid, "live": False, "source": SIM, "recommendation": "HOLD"}


def _public_agent(oid: str, raw: Dict[str, Any]) -> Dict[str, Any]:
    out = {
        "opportunity_id": oid,
        "live": False,
        "source": SIM,
        "recommendation": raw.get("recommendation") or raw.get("status"),
        "reason": raw.get("reason"),
        "confidence": raw.get("confidence"),
        "safety_status": raw.get("safety_status") or raw.get("safety"),
        "agent_status": raw.get("agent_status") or "ADVISORY",
        "current_value": raw.get("current_value") or (raw.get("current_state") or {}).get("current_value"),
        "optimized_value": raw.get("optimized_value") or (raw.get("optimized_state") or {}).get("optimized_value"),
    }
    return out


def evaluate_guide(oid_raw: str, sliders_raw: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    oid = normalize_oid(oid_raw)
    if not oid:
        raise ValueError("UNKNOWN_OPPORTUNITY")
    item = catalog_item(oid)
    if not item:
        raise ValueError("UNKNOWN_OPPORTUNITY")
    sliders = _sliders(item, sliders_raw)
    series = series_for(oid, sliders, item["x_type"])
    metrics = metrics_for(oid, series, sliders)
    agent_raw = _run_agent(oid, sliders)
    agent = _public_agent(oid, agent_raw if isinstance(agent_raw, dict) else {})

    ok, reason, classified = evaluate_dispatch(
        {
            "opportunity_id": oid,
            "id": oid,
            "source": SIM,
            "telemetry": {"source": SIM, "quality": "GOOD", "age_seconds": 5, "raw": "SIMULATION"},
            "supervisory": {"decision": "HOLD", "confidence": 0.5},
            "safety": {"status": "HOLD"},
            "current_value": 1,
            "target_value": 2,
        }
    )
    provenance = classified.get("status") or "SIMULATED"
    if provenance == "LIVE":
        provenance = "SIMULATED"

    return {
        "opportunity_id": oid,
        "id": item["id"],
        "live": False,
        "provenance": "SIMULATED",
        "source": SIM,
        "dispatch_allowed": False,
        "dispatch_blocked_reason": reason if not ok else "OEH guide evaluate is read-only.",
        "safe_mode": is_safe_mode(),
        "classified": {**classified, "status": "SIMULATED", "code": classified.get("code") or "SIMULATION_BLOCKED"},
        "agent": agent,
        "series": series,
        "metrics": metrics,
        "sliders": sliders,
        "x_type": item["x_type"],
        "sim_label": item["sim_label"],
        "pct": item["pct"],
        "scope": item["scope"],
        "title": item["title"],
        "route": item["route"],
    }
