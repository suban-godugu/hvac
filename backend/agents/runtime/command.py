from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.agents.runtime.contracts import CommandContract
from database.models_platform import ControlCommandDB
from database.session import SessionLocal


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _dump(row: ControlCommandDB) -> Dict[str, Any]:
    return {
        "id": row.id,
        "command_id": row.command_id,
        "opportunity": row.opportunity,
        "building_id": row.building_id,
        "equipment_id": row.equipment_id,
        "point_id": row.point_id,
        "old_value": row.old_value,
        "new_value": row.new_value,
        "reason": row.reason,
        "engine_version": row.engine_version,
        "config_version": row.config_version,
        "safety_gates": row.safety_gates,
        "requested_by": row.requested_by,
        "approval_id": row.approval_id,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "applied_at": row.applied_at.isoformat() if row.applied_at else None,
        "verified_at": row.verified_at.isoformat() if row.verified_at else None,
        "rollback_at": row.rollback_at.isoformat() if row.rollback_at else None,
        "payload_json": row.payload_json,
    }


def propose(contract: CommandContract, status: str = "PROPOSED") -> Dict[str, Any]:
    cid = contract.command_id or f"cmd_{uuid.uuid4().hex[:12]}"
    contract.command_id = cid
    db = SessionLocal()
    try:
        row = ControlCommandDB(
            id=cid,
            command_id=cid,
            opportunity=contract.opportunity,
            building_id=contract.building,
            equipment_id=contract.equipment,
            point_id=contract.point,
            old_value=contract.old_value,
            new_value=contract.new_value,
            reason=contract.reason,
            engine_version=contract.engine_version,
            config_version=contract.config_version,
            safety_gates=contract.safety_gates,
            requested_by=contract.requested_by,
            approval_id=contract.approval_id,
            status=status,
            created_at=_now(),
            payload_json=contract.as_dict(),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _dump(row)
    finally:
        db.close()


def set_status(command_id: str, status: str, **times) -> Optional[Dict[str, Any]]:
    db = SessionLocal()
    try:
        row = db.query(ControlCommandDB).filter_by(command_id=command_id).first()
        if not row:
            return None
        row.status = status
        for key in ("applied_at", "verified_at", "rollback_at"):
            if times.get(key):
                setattr(row, key, times[key] if not isinstance(times[key], bool) else _now())
        if status == "APPLIED":
            row.applied_at = _now()
        if status == "VERIFIED":
            row.verified_at = _now()
        if status == "ROLLED_BACK":
            row.rollback_at = _now()
        db.commit()
        return _dump(row)
    finally:
        db.close()


def get_command(command_id: str) -> Optional[Dict[str, Any]]:
    db = SessionLocal()
    try:
        row = db.query(ControlCommandDB).filter_by(command_id=command_id).first()
        return _dump(row) if row else None
    finally:
        db.close()


def list_commands(building_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        q = db.query(ControlCommandDB).order_by(ControlCommandDB.created_at.desc())
        if building_id:
            q = q.filter(ControlCommandDB.building_id == building_id)
        return [_dump(r) for r in q.limit(limit).all()]
    except Exception:
        return []
    finally:
        db.close()


def active_for_point(point_id: str) -> Optional[Dict[str, Any]]:
    db = SessionLocal()
    try:
        row = (
            db.query(ControlCommandDB)
            .filter(
                ControlCommandDB.point_id == point_id,
                ControlCommandDB.status.in_(("APPROVED", "APPLYING", "APPLIED", "VERIFYING")),
            )
            .order_by(ControlCommandDB.created_at.desc())
            .first()
        )
        return _dump(row) if row else None
    except Exception:
        return None
    finally:
        db.close()
