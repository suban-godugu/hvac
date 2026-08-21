"""Canonical telemetry ingest + latest-read. Never coerce missing to 0."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.services.hvac_safety_contract import (
    STALE_SECONDS,
    classify_telemetry,
    ingest_quality,
    is_demo_source,
    normalize_telemetry_source,
    accepts_telemetry_source,
)
from backend.services.ttl_cache import cache_clear, cache_get, cache_set

_LATEST_TTL = float(os.getenv("HVAC_LATEST_POINTS_TTL", "2.5"))
_CACHE_PREFIX = "latest_points"

LIVE_SOURCES = {"LIVE_BMS", "BMS"}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def record_point(
    point_id: str,
    value: Optional[float],
    unit: Optional[str],
    source: str,
    quality: str,
    building_id: Optional[str] = None,
    asset_id: Optional[str] = None,
    equipment_id: Optional[str] = None,
    timestamp: Optional[datetime] = None,
) -> Dict[str, Any]:
    ts = timestamp or _now()
    age = max(0.0, (_now() - ts).total_seconds())
    src = normalize_telemetry_source(source)
    q = ingest_quality(value, quality)
    if is_demo_source(src) and q == "LIVE":
        q = "GOOD"
    if age > STALE_SECONDS and q == "GOOD" and src in LIVE_SOURCES:
        q = "STALE"
    from database.session import SessionLocal
    from database.models_platform import CanonicalTelemetryDB

    row = CanonicalTelemetryDB(
        point_id=point_id,
        building_id=building_id,
        asset_id=asset_id or equipment_id,
        equipment_id=equipment_id or asset_id,
        timestamp=ts,
        value=value,
        unit=unit,
        source=src,
        quality=q,
        age_seconds=age,
    )
    db = SessionLocal()
    try:
        db.add(row)
        db.commit()
        db.refresh(row)
        payload = as_contract(row)
        cache_clear(_CACHE_PREFIX)
    except Exception:
        db.rollback()
        payload = {
            "point_id": point_id,
            "building_id": building_id,
            "asset_id": asset_id or equipment_id,
            "equipment_id": equipment_id or asset_id,
            "timestamp": ts.isoformat() if ts else None,
            "value": value,
            "unit": unit,
            "source": src,
            "quality": q,
            "age_seconds": age,
            "classified": classify_telemetry({"quality": q, "age_seconds": age, "value": value, "raw": q, "source": src}, src)["status"],
        }
    finally:
        db.close()
    return payload


def as_contract(row: Any) -> Dict[str, Any]:
    age = getattr(row, "age_seconds", None)
    payload = {
        "point_id": row.point_id,
        "building_id": row.building_id,
        "asset_id": row.asset_id,
        "equipment_id": getattr(row, "equipment_id", None) or row.asset_id,
        "timestamp": row.timestamp.isoformat() if row.timestamp else None,
        "value": row.value,
        "unit": row.unit,
        "source": row.source,
        "quality": row.quality,
        "age_seconds": age,
    }
    classified = classify_telemetry(
        {"quality": row.quality, "age_seconds": age, "value": row.value, "raw": row.quality, "source": row.source},
        row.source,
    )
    payload["classified"] = classified["status"]
    return payload


def latest_points(building_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    from database.session import SessionLocal
    from database.models_platform import CanonicalTelemetryDB

    key = (_CACHE_PREFIX, building_id or "", int(limit))
    cached = cache_get(key)
    if cached is not None:
        return cached

    db = SessionLocal()
    try:
        q = db.query(CanonicalTelemetryDB)
        if building_id:
            q = q.filter(CanonicalTelemetryDB.building_id == building_id)
        fetch = max(int(limit) * 6, 80)
        rows = q.order_by(CanonicalTelemetryDB.timestamp.desc(), CanonicalTelemetryDB.id.desc()).limit(fetch).all()
        payload: List[Dict[str, Any]] = []
        seen = set()
        for r in rows:
            if not accepts_telemetry_source(r.source):
                continue
            pid = r.point_id
            if pid in seen:
                continue
            seen.add(pid)
            payload.append(as_contract(r))
            if len(payload) >= limit:
                break
        cache_set(key, payload, _LATEST_TTL)
        return payload
    finally:
        db.close()


def find_point_by_suffix(points: List[Dict[str, Any]]) -> Callable[..., Optional[Dict[str, Any]]]:
    """Index latest points once, then look up by equipment_id + point_id substring."""
    indexed: Dict[Any, List[Tuple[str, Dict[str, Any]]]] = {}
    for row in points:
        pid = (row.get("point_id") or "").lower()
        indexed.setdefault(row.get("equipment_id"), []).append((pid, row))

    def find(equipment_id: Any, *suffixes: str) -> Optional[Dict[str, Any]]:
        rows = indexed.get(equipment_id) or []
        for suffix in suffixes:
            needle = suffix.lower()
            for pid, row in rows:
                if needle in pid:
                    return row
        return None

    return find


def query_telemetry(
    building_id: Optional[str] = None,
    point_id: Optional[str] = None,
    asset_id: Optional[str] = None,
    opportunity_id: Optional[str] = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    del opportunity_id  # reserved for join to opportunity point maps
    from database.session import SessionLocal
    from database.models_platform import CanonicalTelemetryDB

    db = SessionLocal()
    try:
        q = db.query(CanonicalTelemetryDB)
        if building_id:
            q = q.filter(CanonicalTelemetryDB.building_id == building_id)
        if point_id:
            q = q.filter(CanonicalTelemetryDB.point_id == point_id)
        if asset_id:
            q = q.filter(CanonicalTelemetryDB.asset_id == asset_id)
        rows = q.order_by(CanonicalTelemetryDB.timestamp.desc()).limit(limit).all()
        return [as_contract(r) for r in rows]
    finally:
        db.close()
