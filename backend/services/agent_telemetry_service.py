"""Single read path for O1–O20. Agents never query BACnet/Modbus/MQTT."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from backend.bms.point_mapper import resolve_canonical_name
from backend.services.canonical_telemetry_service import as_contract, latest_points
from backend.services.hvac_safety_contract import STALE_SECONDS, classify_telemetry, is_demo_source, is_safe_mode
from backend.services.opportunity_feature_catalog import catalog_for


def _now_row(point_id: str, building_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    from database.session import SessionLocal
    from database.models_platform import CanonicalTelemetryDB

    db = SessionLocal()
    try:
        q = db.query(CanonicalTelemetryDB).filter(CanonicalTelemetryDB.point_id == point_id)
        if building_id:
            q = q.filter(CanonicalTelemetryDB.building_id == building_id)
        row = q.order_by(CanonicalTelemetryDB.timestamp.desc(), CanonicalTelemetryDB.id.desc()).first()
        return as_contract(row) if row else None
    finally:
        db.close()


def _qualified(equipment_id: str, canonical_point: str) -> str:
    return f"{equipment_id}.{resolve_canonical_name(canonical_point)}"


def _feature_payload(row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not row:
        return {"value": None, "unit": None, "quality": "MISSING", "source": None, "age_seconds": None, "timestamp": None, "classified": "MISSING"}
    value = row.get("value")
    quality = str(row.get("quality") or "MISSING").upper()
    if value is None and quality not in ("MISSING", "BAD", "STALE"):
        quality = "MISSING"
    src = row.get("source")
    classified = classify_telemetry(
        {"quality": quality, "age_seconds": row.get("age_seconds"), "value": value, "source": src},
        src,
    )
    return {
        "value": value,
        "unit": row.get("unit"),
        "quality": quality,
        "source": src,
        "age_seconds": row.get("age_seconds"),
        "timestamp": row.get("timestamp"),
        "classified": classified.get("status"),
        "point_id": row.get("point_id"),
    }


def get_point(
    equipment_id: str,
    canonical_point: str,
    building_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    pid = _qualified(equipment_id, canonical_point)
    row = _now_row(pid, building_id)
    if row:
        return row
    # Fallback scan of latest cache — exact qualified id only.
    for item in latest_points(building_id, limit=200):
        if str(item.get("point_id") or "") == pid:
            return item
    return None


def get_points(requests: Sequence[Dict[str, str]], building_id: Optional[str] = None) -> Dict[str, Optional[Dict[str, Any]]]:
    out: Dict[str, Optional[Dict[str, Any]]] = {}
    for req in requests:
        name = req.get("name") or req.get("canonical_point") or ""
        eq = req.get("equipment_id") or ""
        canon = req.get("canonical_point") or name
        out[name] = get_point(eq, canon, building_id)
    return out


def get_equipment_snapshot(equipment_id: str, building_id: Optional[str] = None) -> Dict[str, Any]:
    rows = []
    for item in latest_points(building_id, limit=200):
        if str(item.get("equipment_id") or "") == equipment_id:
            rows.append(item)
    return {"equipment_id": equipment_id, "points": rows}


def _overall_source(features: Dict[str, Dict[str, Any]]) -> Tuple[Optional[str], Optional[str], Optional[float]]:
    ages = []
    sources = []
    qualities = []
    for feat in features.values():
        if feat.get("value") is None and str(feat.get("quality") or "").upper() == "MISSING":
            continue
        if feat.get("source"):
            sources.append(str(feat["source"]))
        if feat.get("quality"):
            qualities.append(str(feat["quality"]).upper())
        if feat.get("age_seconds") is not None:
            ages.append(float(feat["age_seconds"]))
    age = max(ages) if ages else None
    if any(is_demo_source(s) or "KAGGLE" in str(s).upper() or str(s).upper() in ("TRAINING_DATA", "ML_MODEL", "MODEL_PREDICTION", "MODEL PREDICTION") for s in sources):
        src = next((s for s in sources if is_demo_source(s) or str(s).upper() in ("KAGGLE", "TRAINING_DATA", "ML_MODEL", "MODEL_PREDICTION", "MODEL PREDICTION")), sources[0] if sources else None)
    elif sources and all(str(s).upper() in ("LIVE_BMS", "BMS") for s in sources):
        src = "LIVE_BMS"
    elif sources:
        src = sources[0]
    else:
        src = None
    quality = "BAD" if "BAD" in qualities else ("STALE" if "STALE" in qualities else ("GOOD" if qualities and all(q == "GOOD" for q in qualities) else (qualities[0] if qualities else None)))
    return src, quality, age


def get_agent_context(
    opportunity_id: str,
    equipment_id: Optional[str] = None,
    building_id: Optional[str] = None,
) -> Dict[str, Any]:
    spec = catalog_for(opportunity_id)
    oid = opportunity_id.strip().upper()
    eq = equipment_id or spec["equipment_id"]
    features: Dict[str, Dict[str, Any]] = {}
    missing: List[str] = []
    for req in spec["required"]:
        row = get_point(req["equipment_id"], req["canonical_point"], building_id)
        payload = _feature_payload(row)
        features[req["name"]] = payload
        # Occupancy 0 is valid. Missing is null/MISSING/BAD with no value.
        if payload["value"] is None:
            missing.append(req["name"])

    src, quality, age = _overall_source(features)
    tel_class = classify_telemetry({"quality": quality, "age_seconds": age, "source": src, "value": 1 if not missing else None}, src)

    from backend.bms.connection_manager import get_connection_manager

    connected = bool(get_connection_manager().is_production_connected())
    safe = is_safe_mode()

    if missing:
        status = "WAITING_FOR_TELEMETRY"
    elif tel_class.get("status") == "BAD" or quality == "BAD":
        status = "BAD_TELEMETRY"
    elif tel_class.get("status") == "STALE" or quality == "STALE":
        status = "STALE"
    elif not connected and (not src or str(src).upper() in ("LIVE_BMS", "BMS")) and tel_class.get("status") != "SIMULATED":
        if src is None or tel_class.get("status") == "LIVE":
            status = "BMS_OFFLINE"
        else:
            status = tel_class.get("status") or "BMS_OFFLINE"
    elif safe:
        status = "SAFE_MODE"
    else:
        status = "READY"

    # WRITE_DISABLED never replaces READY for calculation.
    return {
        "opportunity": oid,
        "equipment_id": eq,
        "telemetry": {
            "source": src,
            "quality": quality,
            "age_seconds": age,
            "classified": tel_class.get("status"),
        },
        "features": features,
        "missing_features": missing,
        "status": status,
        "control": "WRITE_DISABLED",
        "kind": spec.get("kind") or "CONTROL",
        "safeMode": safe,
        "bmsConnected": connected,
    }


def feature_value(context: Dict[str, Any], name: str) -> Optional[float]:
    feat = (context.get("features") or {}).get(name) or {}
    val = feat.get("value")
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None
