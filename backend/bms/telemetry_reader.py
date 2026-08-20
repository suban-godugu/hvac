"""Read mapped BMS points into canonical telemetry. Never coerce missing to 0."""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional

from backend.bms.base import PointReading
from backend.bms.connection_manager import get_connection_manager
from backend.services.canonical_telemetry_service import record_point
from backend.services.hvac_safety_contract import STALE_SECONDS


_STOP = threading.Event()
_THREAD: Optional[threading.Thread] = None


def _quality_for(reading: PointReading, connected: bool) -> str:
    if not connected:
        return "MISSING"
    if reading.value is None:
        q = (reading.quality or "MISSING").upper()
        return q if q in ("MISSING", "BAD", "STALE") else "MISSING"
    q = (reading.quality or "GOOD").upper()
    return q if q else "GOOD"


def ingest_reading(
    *,
    equipment_id: str,
    canonical_point: str,
    reading: PointReading,
    building_id: Optional[str] = None,
    connected: bool = False,
) -> Dict[str, Any]:
    source = "LIVE_BMS" if connected else "UNKNOWN"
    quality = _quality_for(reading, connected)
    value = reading.value
    if value is None and quality not in ("MISSING", "BAD", "STALE"):
        quality = "MISSING"
    return record_point(
        point_id=f"{equipment_id}.{canonical_point}",
        value=value,
        unit=reading.unit,
        source=source,
        quality=quality,
        building_id=building_id,
        equipment_id=equipment_id,
    )


def poll_once(include_unmapped: bool = True) -> List[Dict[str, Any]]:
    from database.models_bms import BmsPointDB, EquipmentPointMappingDB
    from database.session import SessionLocal

    mgr = get_connection_manager()
    connected = mgr.is_production_connected()
    adapter = mgr.adapter()
    out: List[Dict[str, Any]] = []
    if adapter is None or not connected:
        return out
    db = SessionLocal()
    try:
        mappings = db.query(EquipmentPointMappingDB).all()
        mapped_ids = {m.bms_point_id for m in mappings}
        for m in mappings:
            pt = db.query(BmsPointDB).filter(BmsPointDB.id == m.bms_point_id).first()
            if pt is None:
                continue
            reading = adapter.read_point(pt.point_identifier)
            out.append(
                ingest_reading(
                    equipment_id=m.equipment_id,
                    canonical_point=m.canonical_point,
                    reading=reading,
                    connected=True,
                )
            )
        if include_unmapped:
            extras = db.query(BmsPointDB).filter(~BmsPointDB.id.in_(mapped_ids) if mapped_ids else True).all() if mapped_ids else db.query(BmsPointDB).all()
            for pt in extras:
                reading = adapter.read_point(pt.point_identifier)
                value = reading.value
                quality = _quality_for(reading, True)
                out.append(
                    record_point(
                        point_id=pt.point_identifier,
                        value=value,
                        unit=pt.unit or reading.unit,
                        source="LIVE_BMS",
                        quality=quality,
                        equipment_id=None,
                    )
                )
    finally:
        db.close()
    return out


def _loop(interval: float) -> None:
    while not _STOP.is_set():
        try:
            poll_once(include_unmapped=False)
        except Exception:
            pass
        _STOP.wait(interval)


def start_reader(interval: float = 2.0) -> None:
    global _THREAD
    if _THREAD and _THREAD.is_alive():
        return
    _STOP.clear()
    _THREAD = threading.Thread(target=_loop, args=(max(1.0, interval),), name="bms-telemetry-reader", daemon=True)
    _THREAD.start()


def stop_reader() -> None:
    _STOP.set()
