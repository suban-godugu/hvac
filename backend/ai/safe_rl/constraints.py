"""Feasibility filters for Safe-RL candidates."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from backend.agents.runtime.safety import envelope_ok, load_limits
from backend.agents.scheduling_supervisory.safety.guardrails import SafetyGuardrails
from backend.services.hvac_safety_contract import is_safe_mode

_GUARDRAILS = SafetyGuardrails()
_LIMITS = _GUARDRAILS.HARD_LIMITS


def _comfort_violation_risk(state: Dict[str, Any], candidate: Dict[str, Any]) -> Tuple[float, List[str]]:
    """Estimate comfort risk from LSTM zone_temp forecast after action."""
    tags: List[str] = []
    band = state.get("comfort_band") or {}
    lo = float(band.get("min_c", 21))
    hi = float(band.get("max_c", 24))
    lstm = state.get("lstm") or {}
    series = (lstm.get("series") or {}).get("zone_temp")
    if not series:
        tags.append("zone_temp_forecast_missing")
        return 0.15, tags
    points = series.get("points") or []
    risk = 0.0
    for pt in points:
        y = pt.get("yhat")
        if y is None:
            continue
        yf = float(y)
        if yf < lo:
            risk = max(risk, (lo - yf) / max(0.5, hi - lo))
            tags.append("below_comfort_min")
        elif yf > hi:
            risk = max(risk, (yf - hi) / max(0.5, hi - lo))
            tags.append("above_comfort_max")
    action_id = candidate.get("action_id") or ""
    if action_id.startswith("zone_sp_up") and risk > 0:
        risk += 0.2
    if action_id.startswith("sat_warmer") and risk > 0:
        risk += 0.15
    return risk, tags


def _guardrail_check(candidate: Dict[str, Any]) -> Tuple[bool, str, Optional[float]]:
    if candidate.get("action_id") == "hold":
        return True, "OK", None
    new_value = candidate.get("new_value")
    old_value = candidate.get("old_value")
    if new_value is None:
        return False, "MISSING_CURRENT_VALUE", None
    opp = candidate.get("mapped_opportunity") or ""
    clamped = float(new_value)
    if opp == "O2":
        lo, hi = _LIMITS["ZONE_COOL_SP_MIN"], _LIMITS["ZONE_COOL_SP_MAX"]
        if clamped < lo:
            return False, "ZONE_COOL_SP_MIN", lo
        if clamped > hi:
            return False, "ZONE_COOL_SP_MAX", hi
    elif opp == "O3":
        lo, hi = _LIMITS["AHU_SAT_MIN"], _LIMITS["AHU_SAT_MAX"]
        if clamped < lo:
            return False, "AHU_SAT_MIN", lo
        if clamped > hi:
            return False, "AHU_SAT_MAX", hi
    elif opp == "O7":
        lo, hi = _LIMITS["CHWS_MIN"], _LIMITS["CHWS_MAX"]
        if clamped < lo:
            return False, "CHWS_MIN", lo
        if clamped > hi:
            return False, "CHWS_MAX", hi
    elif opp in ("O14", "O16", "O5"):
        if old_value is not None and clamped < 0:
            return False, "NEGATIVE_SETPOINT", None
    return True, "OK", clamped if clamped != new_value else None


def check_candidate(
    state: Dict[str, Any],
    candidate: Dict[str, Any],
) -> Dict[str, Any]:
    """Return feasibility result with reason tags."""
    action_id = candidate.get("action_id") or ""
    if action_id == "hold":
        return {"feasible": True, "reason": "HOLD", "constraints": [], "comfort_risk": 0.0}

    if is_safe_mode() or state.get("safe_mode"):
        return {"feasible": False, "reason": "SAFE_MODE", "constraints": ["SAFE_MODE"], "comfort_risk": 1.0}

    if not state.get("telemetry_ok"):
        return {"feasible": False, "reason": "TELEMETRY_MISSING", "constraints": ["telemetry_ok"], "comfort_risk": 1.0}

    ok, code, _clamped = _guardrail_check(candidate)
    constraints: List[str] = []
    if not ok:
        constraints.append(code)
        return {"feasible": False, "reason": code, "constraints": constraints, "comfort_risk": 1.0}

    limits = state.get("engineering_limits") or load_limits(state.get("building_id"))
    env_ok, env_code = envelope_ok(candidate.get("point_id"), candidate.get("new_value"), limits)
    if not env_ok:
        constraints.append(env_code)
        return {"feasible": False, "reason": env_code, "constraints": constraints, "comfort_risk": 0.8}

    comfort_risk, comfort_tags = _comfort_violation_risk(state, candidate)
    constraints.extend(comfort_tags)
    max_comfort = float(__import__("os").getenv("HVAC_SAFE_RL_MAX_COMFORT_RISK", "0.85") or "0.85")
    if comfort_risk > max_comfort:
        constraints.append("COMFORT_LIMIT")
        return {
            "feasible": False,
            "reason": "COMFORT_LIMIT",
            "constraints": constraints,
            "comfort_risk": comfort_risk,
        }

    return {"feasible": True, "reason": "OK", "constraints": constraints, "comfort_risk": comfort_risk}
