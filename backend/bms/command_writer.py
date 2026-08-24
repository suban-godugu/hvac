"""Supervised BMS writes. Dataset and SAFE MODE never write."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from backend.bms.base import WRITE_DISABLED, WriteOutcome, utc_now
from backend.middleware.request_id import current_request_id

WRITE_DIRS = {"WRITE", "READ_WRITE", "RW"}


def write_enabled_flag() -> bool:
    return os.getenv("HVAC_BMS_WRITE_ENABLED", "0").strip() in ("1", "true", "TRUE")


def simulated_writes_allowed() -> bool:
    """Synthetic plant only. Never production BMS."""
    from backend.bms.connection_manager import is_simulation_mode
    from backend.services.hvac_safety_contract import is_safe_mode

    if not is_simulation_mode() or is_safe_mode():
        return False
    if os.getenv("HVAC_USE_SIMULATION", "0").strip() not in ("1", "true", "TRUE"):
        return False
    # Align with SimulatorBMSGateway — sim writes need an explicit allow flag.
    return os.getenv("HVAC_ALLOW_SIM_WRITES", "0").strip() in ("1", "true", "TRUE")


def control_writes_status() -> str:
    if physical_writes_allowed():
        return "LIVE WRITE ENABLED"
    if simulated_writes_allowed():
        return "SIM WRITE ENABLED"
    return "WRITE DISABLED"


def has_point_mappings() -> bool:
    try:
        from database.models_bms import EquipmentPointMappingDB
        from database.session import SessionLocal

        db = SessionLocal()
        try:
            return db.query(EquipmentPointMappingDB).count() > 0
        finally:
            db.close()
    except Exception:
        return False


def connection_writes_armed() -> bool:
    try:
        from backend.bms.connection_manager import get_connection_manager

        row = get_connection_manager().current_row()
        return bool(row and row.write_enabled)
    except Exception:
        return False


def physical_writes_allowed() -> bool:
    """Live BMS + env + armed connection + mappings + not SAFE MODE. Never in Dataset."""
    from backend.bms.connection_manager import is_simulation_mode
    from backend.services.hvac_safety_contract import is_safe_mode, production_bms_connected

    if is_simulation_mode() or is_safe_mode():
        return False
    if not write_enabled_flag():
        return False
    if not production_bms_connected():
        return False
    if not has_point_mappings():
        return False
    return connection_writes_armed()


def write_disabled_body(message: Optional[str] = None, code: str = WRITE_DISABLED) -> Dict[str, Any]:
    return {
        "code": code,
        "message": message or "BMS writes are disabled until HVAC_BMS_WRITE_ENABLED=1 and write-enable after mapping review.",
        "request_id": current_request_id(),
    }


def _deny(code: str, message: str, point_id: str, value: float) -> WriteOutcome:
    return WriteOutcome(
        success=False,
        code=code,
        message=message,
        point_id=point_id,
        value=value,
        timestamp=utc_now().isoformat(),
    )


def resolve_write_target(point_id: str) -> Tuple[Optional[str], Optional[WriteOutcome], Optional[str]]:
    """Map canonical AHU-01.sat_setpoint to a discovered BMS identifier."""
    from database.models_bms import BmsPointDB, EquipmentPointMappingDB
    from database.session import SessionLocal

    pid = (point_id or "").strip()
    if not pid:
        return None, _deny("MISSING_VALUES", "point_id is required.", pid, 0), None
    equipment_id, _, canonical = pid.partition(".")
    db = SessionLocal()
    try:
        mapping = None
        if equipment_id and canonical:
            mapping = (
                db.query(EquipmentPointMappingDB)
                .filter(
                    EquipmentPointMappingDB.equipment_id == equipment_id,
                    EquipmentPointMappingDB.canonical_point == canonical,
                )
                .first()
            )
        pt = None
        if mapping:
            pt = db.query(BmsPointDB).filter(BmsPointDB.id == mapping.bms_point_id).first()
            direction = (mapping.direction or "READ").upper()
            if direction not in WRITE_DIRS:
                return None, _deny("MAPPING_READ_ONLY", "Mapped point is read-only.", pid, 0), mapping.direction
            if pt is None:
                return None, _deny("MAPPING_INVALID", "Mapped BMS point is missing.", pid, 0), direction
            if not pt.writable:
                return None, _deny("MAPPING_READ_ONLY", "Discovered BMS point is not writable.", pid, 0), direction
            return pt.point_identifier, None, direction
        pt = db.query(BmsPointDB).filter(BmsPointDB.point_identifier == pid).first()
        if pt is None:
            return None, _deny("MAPPING_REQUIRED", "Point is not mapped to a discovered BMS object.", pid, 0), None
        if not pt.writable:
            return None, _deny("MAPPING_READ_ONLY", "Discovered BMS point is not writable.", pid, 0), None
        return pt.point_identifier, None, None
    finally:
        db.close()


def _simulated_write(point_id: str, value: float, priority: int = 10) -> WriteOutcome:
    from backend.bms.simulation_telemetry import apply_simulated_write

    apply_simulated_write(point_id, float(value))
    return WriteOutcome(
        success=True,
        code="SIM_WRITE",
        message="Applied to synthetic plant only. Production BMS was not written.",
        point_id=point_id,
        value=float(value),
        timestamp=utc_now().isoformat(),
    )


def write_point(point_id: str, value: float, priority: int = 10) -> WriteOutcome:
    from backend.bms.connection_manager import get_connection_manager, is_simulation_mode
    from backend.services.hvac_safety_contract import is_safe_mode

    if is_simulation_mode():
        if simulated_writes_allowed():
            return _simulated_write(point_id, value, priority)
        return _deny("SIMULATION_BLOCKED", "Dataset mode cannot write to a production BMS.", point_id, value)
    if is_safe_mode():
        return _deny("SAFE_MODE", "SAFE MODE blocks all BMS writes.", point_id, value)
    if not physical_writes_allowed():
        return _deny(
            WRITE_DISABLED,
            "Supervised writes are off. Set HVAC_BMS_WRITE_ENABLED=1, complete mapping, then ENABLE WRITES.",
            point_id,
            value,
        )
    ident, err, _dir = resolve_write_target(point_id)
    if err is not None:
        return err
    adapter = get_connection_manager().adapter()
    if adapter is None:
        return _deny("BMS_OFFLINE", "Production BMS gateway is not connected.", point_id, value)
    try:
        return adapter.execute_write(ident or point_id, float(value), int(priority or 10))
    except Exception as exc:
        return _deny("BMS_CONNECTION_FAILED", str(exc), point_id, value)


def write_points(writes: List[Dict[str, Any]]) -> List[WriteOutcome]:
    return [write_point(str(w.get("point_id") or ""), float(w.get("value") or 0), int(w.get("priority") or 10)) for w in writes]


def enable_supervised_writes(*, confirm: bool = False) -> Dict[str, Any]:
    from backend.bms.connection_manager import get_connection_manager, is_simulation_mode
    from backend.services.hvac_safety_contract import is_safe_mode, production_bms_connected

    if is_simulation_mode():
        return {**write_disabled_body("Dataset mode cannot enable production writes.", "SIMULATION_MODE"), "enabled": False}
    if is_safe_mode():
        return {**write_disabled_body("SAFE MODE blocks write enable.", "SAFE_MODE"), "enabled": False}
    if not write_enabled_flag():
        return {**write_disabled_body("HVAC_BMS_WRITE_ENABLED is 0."), "enabled": False}
    if not production_bms_connected():
        return {**write_disabled_body("Connect Live BMS before enabling writes.", "BMS_OFFLINE"), "enabled": False}
    if not has_point_mappings():
        return {**write_disabled_body("Map discovered points to canonical names first.", "MAPPING_REQUIRED"), "enabled": False}
    if not confirm:
        return {**write_disabled_body("Safety review confirmation is required.", "CONFIRM_REQUIRED"), "enabled": False}
    mgr = get_connection_manager()
    mgr.set_write_enabled(True)
    return {
        "enabled": True,
        "code": "WRITE_ENABLED",
        "message": "Supervised writes armed. APPLY / VERIFY / ROLLBACK still go through evaluate_dispatch().",
        "write_enabled": True,
        "request_id": current_request_id(),
    }


def disable_supervised_writes() -> Dict[str, Any]:
    from backend.bms.connection_manager import get_connection_manager

    get_connection_manager().set_write_enabled(False)
    return {"enabled": False, "code": WRITE_DISABLED, "write_enabled": False, "request_id": current_request_id()}
