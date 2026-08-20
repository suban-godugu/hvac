from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from backend.services.hvac_safety_contract import evaluate_dispatch, is_safe_mode
from database.models import EngineeringLimitDB
from database.session import SessionLocal


def load_limits(building_id: Optional[str]) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        row = None
        if building_id:
            row = db.query(EngineeringLimitDB).filter_by(id=building_id).first()
        if row is None:
            row = db.query(EngineeringLimitDB).first()
        return dict(row.config_json or {}) if row else {}
    finally:
        db.close()


def envelope_ok(point_id: Optional[str], new_value: Optional[float], limits: Dict[str, Any]) -> Tuple[bool, str]:
    if new_value is None:
        return False, "INVALID_LIMIT"
    cfg = limits or {}
    # Nested or flat min/max
    amin = cfg.get("absolute_min")
    amax = cfg.get("absolute_max")
    by_point = (cfg.get("points") or {}).get(point_id or "") if point_id else None
    if isinstance(by_point, dict):
        amin = by_point.get("min", amin)
        amax = by_point.get("max", amax)
    try:
        if amin is not None and float(new_value) < float(amin):
            return False, "BELOW_ABSOLUTE_MIN"
        if amax is not None and float(new_value) > float(amax):
            return False, "ABOVE_ABSOLUTE_MAX"
    except (TypeError, ValueError):
        return False, "INVALID_LIMIT"
    return True, "OK"


def evaluate_safety(context: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    if is_safe_mode():
        return False, "SAFE_MODE", {"code": "SAFE_MODE"}
    ok, reason, classified = evaluate_dispatch(context)
    if not ok:
        return False, reason, classified
    limits = load_limits(context.get("building_id") or (context.get("user") or {}).get("building_id"))
    env_ok, env_code = envelope_ok(context.get("point_id") or context.get("point"), context.get("target_value"), limits)
    if not env_ok:
        return False, "Requested value is outside engineering_limits.", {**classified, "code": env_code}
    return True, "OK", {**classified, "code": "DISPATCH_OK", "limits": limits}
