from __future__ import annotations

from typing import Any, Dict, Optional

from backend.services.hvac_safety_contract import classify_telemetry, is_demo_source
from backend.services.canonical_telemetry_service import latest_points


def build_state(building_id: Optional[str] = None, opportunity: Optional[str] = None) -> Dict[str, Any]:
    points = latest_points(building_id, limit=80)
    live = [p for p in points if p.get("classified") == "LIVE"]
    return {
        "building_id": building_id,
        "opportunity": opportunity,
        "points": points,
        "live_count": len(live),
        "telemetry_status": "LIVE" if live else (points[0].get("classified") if points else "MISSING"),
        "simulation": any(is_demo_source(p.get("source")) for p in points),
    }


def classify_point(tel: Dict[str, Any]) -> Dict[str, Any]:
    return classify_telemetry(tel, tel.get("source"))
