"""Assemble Safe-RL decision state from Stage B/C/D inputs."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from backend.agents.runtime.safety import load_limits
from backend.agents.runtime.state_builder import build_state
from backend.ai.safe_rl.actions import action_catalog, materialize_candidate, point_map
from backend.services.ai_normalized_telemetry import build_ai_records, point_map_for_zone
from backend.services.canonical_telemetry_service import latest_points
from backend.services.hvac_safety_contract import is_safe_mode


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def comfort_band() -> Dict[str, float]:
    return {
        "min_c": float(os.getenv("HVAC_COMFORT_MIN_C", "21") or "21"),
        "max_c": float(os.getenv("HVAC_COMFORT_MAX_C", "24") or "24"),
    }


def tariff_usd_kwh() -> float:
    return float(os.getenv("HVAC_TOU_TARIFF_USD_KWH", "0.14") or "0.14")


def _latest_normalized_row(zone_id: str, building_id: Optional[str]) -> Optional[Dict[str, Any]]:
    end = _now()
    start = end - timedelta(minutes=90)
    payload = build_ai_records(
        zone_id=zone_id,
        t0=start.isoformat(),
        t1=end.isoformat(),
        step_seconds=60,
        building_id=building_id,
    )
    records = payload.get("records") or []
    for row in reversed(records):
        q = str(row.get("quality") or "").upper()
        if q in ("GOOD", "STALE"):
            return row
    return None


def _current_values(zone_id: str, building_id: Optional[str]) -> Dict[str, Optional[float]]:
    out: Dict[str, Optional[float]] = {}
    zmap = point_map_for_zone(zone_id)
    norm = _latest_normalized_row(zone_id, building_id)
    if norm:
        for field, pid in zmap.items():
            val = norm.get(field)
            if val is not None:
                out[pid] = float(val)
                out[field] = float(val)
    for p in latest_points(building_id, limit=400):
        pid = str(p.get("point_id") or "")
        if pid and p.get("value") is not None:
            out[pid] = float(p["value"])
    pmap = point_map()
    for key, pid in pmap.items():
        if key == "zone_cooling_setpoint":
            pid = f"{zone_id}.cooling_setpoint"
        if pid in out:
            out[key] = out[pid]
    return out


def build_decision_state(
    zone_id: str = "ZONE-01",
    *,
    building_id: Optional[str] = None,
) -> Dict[str, Any]:
    building_id = building_id or os.getenv("HVAC_DEFAULT_BUILDING_ID") or "bldg-corp-hq-01"
    norm = _latest_normalized_row(zone_id, building_id)
    current_values = _current_values(zone_id, building_id)
    candidates = [
        materialize_candidate(a, zone_id=zone_id, building_id=building_id, current_values=current_values)
        for a in action_catalog()
    ]

    rls: Dict[str, Any] = {"models": [], "ready": False}
    try:
        from backend.ai.rls.service import params_for, snapshot_all

        snap = snapshot_all(zone_id)
        rls["models"] = snap.get("models") or []
        rls["ready"] = any(m.get("status") == "READY" for m in rls["models"])
        rls["zone_thermal"] = params_for("zone_thermal", zone_id=zone_id)
        rls["hvac_power"] = params_for("hvac_power", zone_id=zone_id)
    except Exception as exc:
        rls["error"] = str(exc)

    lstm: Dict[str, Any] = {"status": {}, "series": {}}
    try:
        from backend.ai.lstm.infer import forecast

        fc = forecast(zone_id=zone_id, lookback_min=60, targets=["zone_temp", "hvac_power"])
        lstm = {
            "now": fc.get("now"),
            "status": fc.get("status") or {},
            "series": fc.get("series") or {},
            "horizons_min": fc.get("horizons_min") or [15, 30, 45, 60],
        }
    except Exception as exc:
        lstm["error"] = str(exc)

    telemetry_ok = norm is not None and str(norm.get("quality") or "").upper() in ("GOOD", "STALE")
    return {
        "zone_id": zone_id,
        "building_id": building_id,
        "timestamp": _now().isoformat(),
        "safe_mode": is_safe_mode(),
        "telemetry_ok": telemetry_ok,
        "normalized": norm,
        "platform_state": build_state(building_id, "SAFE_RL"),
        "current_values": current_values,
        "candidates": candidates,
        "rls": rls,
        "lstm": lstm,
        "comfort_band": comfort_band(),
        "tariff_usd_kwh": tariff_usd_kwh(),
        "engineering_limits": load_limits(building_id),
        "point_map": point_map(),
    }
