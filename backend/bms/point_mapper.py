"""Canonical HVAC point names. These are not BACnet addresses."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

CANONICAL_POINTS: Dict[str, List[str]] = {
    "AHU": [
        "supply_air_temperature",
        "return_air_temperature",
        "sat_setpoint",
        "fan_speed",
        "duct_static_pressure",
        "static_setpoint",
        "oa_damper",
        "cooling_valve",
        "heating_valve",
        "enable",
        "co2",
    ],
    "CH": [
        "chw_supply_temperature",
        "chw_return_temperature",
        "chw_supply_setpoint",
        "load",
        "power",
        "status",
        "enable",
        "head_pressure",
        "suction_temperature",
        "discharge_pressure",
        "condenser_water_temperature",
        "condenser_pressure",
        "runtime",
        "energy",
        "alarms",
    ],
    "P": [
        "speed",
        "differential_pressure",
        "flow",
        "status",
        "enable",
    ],
    "VFD": [
        "speed",
        "command",
        "status",
    ],
    "ZONE": [
        "zone_temperature",
        "cooling_setpoint",
        "heating_setpoint",
        "occupancy",
        "co2",
        "co_ppm",
    ],
    "SITE": [
        "outdoor_air_temperature",
        "occupancy_schedule",
    ],
    "HHW": [
        "hhw_supply_temperature",
        "hhw_return_temperature",
        "hhw_setpoint",
        "heating_demand",
        "status",
        "enable",
    ],
    "CW": [
        "cw_supply_temperature",
        "cw_return_temperature",
        "cw_setpoint",
        "status",
        "enable",
    ],
}

# Catalog aliases only — not BMS addresses.
FEATURE_ALIASES = {
    "cooling_load": "load",
    "oat": "outdoor_air_temperature",
    "sat": "supply_air_temperature",
}


def resolve_canonical_name(name: str) -> str:
    key = (name or "").strip()
    return FEATURE_ALIASES.get(key, key)


def canonical_catalog() -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    examples = {
        "AHU": "AHU-01",
        "CH": "CH-01",
        "P": "P-01",
        "VFD": "VFD-01",
        "ZONE": "ZONE-01",
        "SITE": "SITE",
        "HHW": "HHW-01",
        "CW": "CW-01",
    }
    for kind, points in CANONICAL_POINTS.items():
        eq = examples[kind]
        for p in points:
            rows.append({"equipment_id": eq, "canonical_point": p, "qualified": f"{eq}.{p}"})
    return rows


def mapping_to_dict(row: Any, point: Any = None, reading: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = {
        "id": row.id,
        "equipment_id": row.equipment_id,
        "canonical_point": row.canonical_point,
        "bms_point_id": row.bms_point_id,
        "direction": row.direction,
        "safety_enabled": bool(row.safety_enabled),
        "qualified": f"{row.equipment_id}.{row.canonical_point}",
    }
    if point is not None:
        payload.update(
            {
                "point_identifier": point.point_identifier,
                "object_type": point.object_type,
                "object_instance": point.object_instance,
                "unit": point.unit,
                "readable": bool(point.readable),
                "writable": bool(point.writable),
                "enabled": bool(point.enabled),
                "min_value": point.min_value,
                "max_value": point.max_value,
            }
        )
    if reading:
        payload["current_value"] = reading.get("value")
        payload["quality"] = reading.get("quality")
        payload["source"] = reading.get("source")
        payload["timestamp"] = reading.get("timestamp")
        payload["age_seconds"] = reading.get("age_seconds")
    return payload
