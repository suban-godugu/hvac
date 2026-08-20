"""Stamp BMS/source/quality on plant-control payloads so the UI never infers LIVE."""
from __future__ import annotations

from typing import Any, Dict, Optional

from backend.services.hvac_safety_contract import classify_telemetry, production_bms_connected
from backend.services.plant_control_telemetry_service import plant_control_telemetry_service


def stamp_plant_provenance(payload: Dict[str, Any], opportunity: str) -> Dict[str, Any]:
    pts = plant_control_telemetry_service.get_opportunity_telemetry(opportunity)
    pt = pts[0] if pts else {}
    src = pt.get("source") or "NO DATA"
    quality = pt.get("quality") or "MISSING"
    classified = classify_telemetry({"source": src, "quality": quality, "raw": quality}, src)
    connected = production_bms_connected()
    out = dict(payload)
    out["bms_connection"] = "CONNECTED" if connected else "OFFLINE"
    out["bms_status"] = out["bms_connection"]
    out["source"] = src
    out["telemetry_source"] = src
    out["telemetry_quality"] = classified.get("status") or quality
    out["classified"] = classified.get("status")
    return out


def telemetry_for_dispatch(opportunity: str) -> Dict[str, Any]:
    pts = plant_control_telemetry_service.get_opportunity_telemetry(opportunity)
    pt: Optional[Dict[str, Any]] = pts[0] if pts else None
    src = (pt or {}).get("source") or "NO DATA"
    quality = (pt or {}).get("quality") or "MISSING"
    return {
        "source": src,
        "telemetry": {"source": src, "quality": quality, "raw": quality},
    }
