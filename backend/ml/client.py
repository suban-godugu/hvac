"""Attach shared ML output onto existing agent payloads. Never sets live=True from Kaggle/ML."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.ml.features.maps import AGENT_FOR


def _num(payload: Dict[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        if "." in key:
            cur: Any = payload
            ok = True
            for part in key.split("."):
                if not isinstance(cur, dict) or part not in cur:
                    ok = False
                    break
                cur = cur[part]
            if ok:
                try:
                    return float(cur)
                except (TypeError, ValueError):
                    continue
            continue
        raw = payload.get(key)
        if isinstance(raw, dict) and "value" in raw:
            raw = raw["value"]
        try:
            if raw is None or raw == "":
                continue
            return float(raw)
        except (TypeError, ValueError):
            continue
    return None


def extract_features(oid: str, payload: Dict[str, Any]) -> Dict[str, float]:
    """Best-effort feature pull from existing agent JSON. Missing keys stay omitted."""
    cs = payload.get("current_state") if isinstance(payload.get("current_state"), dict) else {}
    cur = payload.get("current") if isinstance(payload.get("current"), dict) else {}
    merged = {**payload, **cs, **cur}
    catalog = {
        "O4": {
            "chw_flow": ("chw_flow", "flow", "current_state.flow"),
            "cw_temperature": ("cw_temp", "condenser_water", "cws"),
            "cooling_load": ("cooling_load", "load", "plant_load", "current_load"),
            "outdoor_temperature": ("oat", "outdoor_temperature", "oa_temp"),
            "humidity": ("humidity", "rh", "oa_rh"),
            "dew_point": ("dew_point", "oa_dewpoint"),
        },
        "O3": {
            "oat": ("oat", "outdoor_temperature"),
            "rat": ("rat", "return_air_temp"),
            "mat": ("mat", "mixed_air_temp"),
            "occupancy": ("occupancy", "occupied"),
            "cooling_valve": ("cooling_valve", "chw_valve"),
            "heating_valve": ("heating_valve", "hw_valve"),
            "fan_speed": ("fan_speed", "fan_speed_pct"),
        },
        "O5": {
            "fan_speed": ("fan_speed", "fan_speed_pct"),
            "occupancy": ("occupancy",),
            "oat": ("oat", "outdoor_temperature"),
            "static_pressure_setpoint": ("static_pressure_setpoint", "dsp_setpoint", "current_value"),
        },
        "O12": {
            "co2": ("co2", "co2_ppm", "current.co2Ppm"),
            "zone_temperature": ("zone_temperature", "temperature"),
            "humidity": ("humidity", "rh"),
            "hour": ("hour",),
            "day_of_week": ("day_of_week",),
        },
        "O17": {
            "cooling_load": ("cooling_load", "load", "current_kw"),
            "outdoor_temperature": ("oat", "outdoor_temperature"),
            "humidity": ("humidity",),
        },
        "O19": {
            "sat": ("sat", "supply_air_temp"),
            "sat_sp": ("sat_sp", "sat_setpoint"),
            "oat": ("oat",),
            "fan_speed": ("fan_speed",),
            "static_pressure": ("static_pressure", "dsp"),
            "occupancy": ("occupancy",),
        },
    }
    keys = catalog.get(oid, {})
    out: Dict[str, float] = {}
    for feat, aliases in keys.items():
        val = _num(merged, *aliases)
        if val is not None:
            out[feat] = val
    return out


def attach_ml_prediction(oid: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(payload or {})
    out["opportunity_id"] = oid
    out.setdefault("agent_id", AGENT_FOR.get(oid))
    out.setdefault("live", False)
    out.setdefault("energy_impact", out.get("energy_impact"))
    out.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    try:
        from backend.ml.prediction.service import predict
    except Exception as exc:
        out["ml"] = {
            "status": "DATA SOURCE ERROR",
            "provenance": "NO DATA",
            "prediction": None,
            "model_id": None,
            "confidence": None,
            "message": str(type(exc).__name__),
        }
        return out
    features = extract_features(oid, out)
    ml = predict(oid, features=features, agent_id=out.get("agent_id"), persist=False)
    # Never promote ML to LIVE
    if ml.get("provenance") == "LIVE" or ml.get("source") == "LIVE_BMS":
        ml["provenance"] = "MODEL PREDICTION"
        ml["source"] = "ML_MODEL"
    out["ml"] = ml
    out["model_id"] = ml.get("model_id")
    out["ml_provenance"] = ml.get("provenance")
    out["ml_confidence"] = ml.get("confidence")
    out.setdefault("provenance", out.get("ui_state") or out.get("classified_status"))
    return out
