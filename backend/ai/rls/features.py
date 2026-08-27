"""Feature builders for Stage C RLS models from NB2 normalized AI rows."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

MODEL_ZONE_THERMAL = "zone_thermal"
MODEL_HVAC_POWER = "hvac_power"
MODEL_KEYS = (MODEL_ZONE_THERMAL, MODEL_HVAC_POWER)

ZONE_THERMAL_DIM = 7  # 1, Tin, Toa, Tsp, Fan, Occ, Equip
HVAC_POWER_DIM = 7  # 1, Toa, Tin, Tin-Tsp, Fan, Occ, Equip


def _f(row: Dict[str, Any], key: str) -> Optional[float]:
    v = row.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _equip(row: Dict[str, Any]) -> Optional[float]:
    return _f(row, "Equipment_Status")


def row_ok(row: Dict[str, Any], *, require_keys: Tuple[str, ...]) -> bool:
    q = str(row.get("quality") or "").upper()
    if q not in ("GOOD", "STALE"):
        return False
    for k in require_keys:
        if _f(row, k) is None and k != "Equipment_Status":
            return False
    return True


def zone_thermal_xy(row_k: Dict[str, Any], row_k1: Dict[str, Any]) -> Optional[Tuple[List[float], float]]:
    """Predict Indoor_Temp at k+1 from state at k."""
    need = ("Indoor_Temp", "Outdoor_Temp", "Setpoint", "Fan_Speed", "Occupancy")
    if not row_ok(row_k, require_keys=need):
        return None
    y = _f(row_k1, "Indoor_Temp")
    if y is None:
        return None
    q1 = str(row_k1.get("quality") or "").upper()
    if q1 not in ("GOOD", "STALE"):
        return None
    tin = _f(row_k, "Indoor_Temp")
    toa = _f(row_k, "Outdoor_Temp")
    tsp = _f(row_k, "Setpoint")
    fan = _f(row_k, "Fan_Speed")
    occ = _f(row_k, "Occupancy")
    eq = _equip(row_k)
    if None in (tin, toa, tsp, fan, occ):
        return None
    equip = 0.0 if eq is None else eq
    x = [1.0, tin, toa, tsp, fan, occ, equip]
    return x, y


def hvac_power_xy(row: Dict[str, Any]) -> Optional[Tuple[List[float], float]]:
    """Predict HVAC_Power at k from contemporaneous state."""
    need = ("Indoor_Temp", "Outdoor_Temp", "Setpoint", "Fan_Speed", "Occupancy", "HVAC_Power")
    if not row_ok(row, require_keys=need):
        return None
    y = _f(row, "HVAC_Power")
    tin = _f(row, "Indoor_Temp")
    toa = _f(row, "Outdoor_Temp")
    tsp = _f(row, "Setpoint")
    fan = _f(row, "Fan_Speed")
    occ = _f(row, "Occupancy")
    eq = _equip(row)
    if None in (y, tin, toa, tsp, fan, occ):
        return None
    equip = 0.0 if eq is None else eq
    x = [1.0, toa, tin, float(tin) - float(tsp), fan, occ, equip]
    return x, float(y)


def feature_dim(model_key: str) -> int:
    if model_key == MODEL_ZONE_THERMAL:
        return ZONE_THERMAL_DIM
    if model_key == MODEL_HVAC_POWER:
        return HVAC_POWER_DIM
    raise ValueError(f"Unknown model_key: {model_key}")
