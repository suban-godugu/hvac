"""Shared helpers for official O11–O20 agents. No invented sensor defaults."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def num(payload: Dict[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        raw = payload.get(key)
        if raw is None:
            continue
        if isinstance(raw, dict) and "value" in raw:
            raw = raw["value"]
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue
    return None


def text(payload: Dict[str, Any], *keys: str) -> Optional[str]:
    for key in keys:
        raw = payload.get(key)
        if raw is None:
            continue
        if isinstance(raw, dict) and "value" in raw:
            raw = raw["value"]
        if raw is None:
            continue
        return str(raw)
    return None


def missing(payload: Dict[str, Any], required: List[str]) -> List[str]:
    out = []
    for key in required:
        if num(payload, key) is None and text(payload, key) is None:
            out.append(key)
    return out


def check(
    name: str,
    ok: bool,
    reason: str,
    actual: Optional[float] = None,
    minimum: Optional[float] = None,
    maximum: Optional[float] = None,
) -> Dict[str, Any]:
    return {
        "check_name": name,
        "result": "PASS" if ok else "FAIL",
        "reason": reason,
        "actual_value": actual,
        "minimum": minimum,
        "maximum": maximum,
    }


def safety_status(checks: List[Dict[str, Any]]) -> str:
    if any(c["result"] != "PASS" for c in checks):
        return "BLOCKED"
    return "PASS"


def agent_envelope(
    opportunity_id: str,
    live: bool,
    *,
    current_state: Optional[Dict[str, Any]] = None,
    optimized_state: Optional[Dict[str, Any]] = None,
    recommendation: Optional[str] = None,
    reason: Optional[str] = None,
    confidence: Optional[float] = None,
    energy_impact: Optional[float] = None,
    safety_checks: Optional[List[Dict[str, Any]]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    checks = safety_checks or []
    saf = safety_status(checks) if checks else None
    rec = recommendation
    if saf == "BLOCKED" and rec not in (None, "HOLD"):
        rec = "BLOCKED"
    status = None
    if not live:
        status = "AWAITING_TELEMETRY"
    elif rec == "BLOCKED":
        status = "BLOCKED"
    elif rec:
        status = "PROPOSED"
    payload = {
        "opportunity_id": opportunity_id,
        "live": live,
        "agent_status": "ONLINE" if live else "DEGRADED",
        "current_state": current_state or {},
        "optimized_state": optimized_state or {},
        "recommendation": rec,
        "reason": reason,
        "confidence": confidence,
        "energy_impact": energy_impact,
        "safety_checks": checks,
        "safety_status": saf,
        "status": status,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        payload.update(extra)
    return payload


def parse_ts(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def telemetry_age_seconds(payload: Dict[str, Any]) -> Optional[float]:
    stamps = []
    ts = parse_ts(payload.get("timestamp"))
    if ts:
        stamps.append(ts)
    for v in payload.values():
        if isinstance(v, dict):
            t = parse_ts(v.get("timestamp"))
            if t:
                stamps.append(t)
    if not stamps:
        return None
    latest = max(stamps)
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - latest.astimezone(timezone.utc)).total_seconds())


def freshness(age_s: Optional[float]) -> str:
    if age_s is None:
        return "OFFLINE"
    if age_s <= 15:
        return "LIVE"
    if age_s <= 120:
        return "RECENT"
    if age_s <= 900:
        return "STALE"
    return "OFFLINE"
