"""Build Rule Engine evaluation context from telemetry + limits."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from backend.agents.runtime.safety import load_limits
from backend.config.engineering_limits import get_limits_config
from backend.services.canonical_telemetry_service import latest_points
from backend.services.hvac_safety_contract import is_safe_mode


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _latest_normalized(zone_id: str, building_id: Optional[str]) -> Optional[Dict[str, Any]]:
    try:
        from backend.services.ai_normalized_telemetry import build_ai_records

        end = _now()
        start = end - timedelta(minutes=30)
        payload = build_ai_records(
            zone_id=zone_id or "ZONE-01",
            t0=start.isoformat(),
            t1=end.isoformat(),
            step_seconds=60,
            building_id=building_id,
        )
        for row in reversed(payload.get("records") or []):
            q = str(row.get("quality") or "").upper()
            if q in ("GOOD", "STALE"):
                return row
    except Exception:
        return None
    return None


def _point_lookup(building_id: Optional[str]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    try:
        for p in latest_points(building_id, limit=500):
            pid = str(p.get("point_id") or "")
            if pid:
                out[pid] = p
    except Exception:
        pass
    return out


def build_rule_context(raw: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Normalize caller payload into a full Rule Engine context."""
    ctx = dict(raw or {})
    building_id = ctx.get("building_id") or os.getenv("HVAC_DEFAULT_BUILDING_ID") or "bldg-corp-hq-01"
    zone_id = ctx.get("zone_id") or "ZONE-01"
    point_id = ctx.get("point_id")
    action = str(ctx.get("action") or "EVALUATE").upper()

    points = _point_lookup(building_id)
    point_row = points.get(str(point_id or ""), {}) if point_id else {}
    old_value = ctx.get("old_value")
    if old_value is None and point_row.get("value") is not None:
        old_value = point_row.get("value")
    new_value = ctx.get("new_value")
    if new_value is None:
        new_value = ctx.get("target_value")

    normalized = ctx.get("normalized")
    if normalized is None:
        normalized = _latest_normalized(zone_id, building_id)

    engineering = get_limits_config()
    eng_limits = load_limits(building_id)

    telemetry = ctx.get("telemetry") or {}
    if not telemetry and point_row:
        telemetry = {
            "source": point_row.get("source"),
            "quality": point_row.get("quality"),
            "age_seconds": point_row.get("age_seconds"),
            "value": point_row.get("value"),
        }
    if not telemetry and normalized:
        telemetry = {
            "source": normalized.get("Source") or normalized.get("source"),
            "quality": normalized.get("quality"),
            "age_seconds": 0,
        }

    return {
        **ctx,
        "action": action,
        "building_id": building_id,
        "zone_id": zone_id,
        "point_id": point_id,
        "old_value": old_value,
        "new_value": new_value,
        "target_value": new_value,
        "current_value": old_value if ctx.get("current_value") is None else ctx.get("current_value"),
        "opportunity_id": ctx.get("opportunity_id") or ctx.get("opportunity") or ctx.get("id"),
        "normalized": normalized,
        "points": points,
        "point_row": point_row,
        "engineering_limits_db": eng_limits,
        "engineering_config": engineering,
        "telemetry": telemetry,
        "safe_mode": is_safe_mode(),
        "decision": ctx.get("decision") or "OPTIMIZE",
        "supervisory": ctx.get("supervisory") or {"decision": ctx.get("decision") or "OPTIMIZE"},
        "safety": ctx.get("safety") or {"status": "PASS", "passed": True},
        "confidence": ctx.get("confidence") if ctx.get("confidence") is not None else 0.9,
        "approval_status": ctx.get("approval_status"),
        "user": ctx.get("user") or {},
        "strict": os.getenv("HVAC_RULE_ENGINE_STRICT", "1").strip() not in ("0", "false", "FALSE"),
        "skip_audit": bool(ctx.get("skip_audit")),
    }
