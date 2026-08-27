from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from database.models_platform import ControlCommandDB, HvacApprovalDB
from database.session import SessionLocal


def required(mode: str) -> bool:
    return (mode or "").upper() in ("APPROVAL_REQUIRED", "MANUAL")


def record_pending(command_id: str, opportunity: str, building_id: Optional[str], requested_by: Optional[str]) -> int:
    db = SessionLocal()
    try:
        row = HvacApprovalDB(
            request_id=command_id,
            building_id=building_id,
            opportunity_id=opportunity,
            requested_by=requested_by,
            status="PENDING",
            action="DISPATCH",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return int(row.id)
    finally:
        db.close()


def status_for(command_id: str) -> Optional[str]:
    db = SessionLocal()
    try:
        row = db.query(HvacApprovalDB).filter_by(request_id=command_id).order_by(HvacApprovalDB.id.desc()).first()
        return row.status if row else None
    finally:
        db.close()


def approve_command(command_id: str, *, approved_by: Optional[str] = "operator") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """PROPOSED → APPROVED on control_commands + HvacApprovalDB."""
    from backend.agents.runtime.command import get_command

    cid = (command_id or "").strip()
    if not cid:
        return False, "MISSING_COMMAND_ID", None

    db = SessionLocal()
    try:
        row = db.query(ControlCommandDB).filter_by(command_id=cid).first()
        if row is None:
            return False, "NOT_FOUND", None
        status = (row.status or "").upper()
        if status == "APPROVED":
            return True, "ALREADY_APPROVED", get_command(cid)
        if status not in ("PROPOSED", "PENDING"):
            return False, f"INVALID_STATUS:{status}", get_command(cid)

        row.status = "APPROVED"
        approval = (
            db.query(HvacApprovalDB)
            .filter_by(request_id=cid)
            .order_by(HvacApprovalDB.id.desc())
            .first()
        )
        if approval is None:
            approval = HvacApprovalDB(
                request_id=cid,
                building_id=row.building_id,
                opportunity_id=row.opportunity,
                requested_by=row.requested_by,
                status="APPROVED",
                action="DISPATCH",
                approved_by=approved_by,
                timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            db.add(approval)
            db.flush()
        else:
            approval.status = "APPROVED"
            approval.approved_by = approved_by
            approval.timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
        row.approval_id = str(approval.id)
        db.commit()
    finally:
        db.close()

    return True, "APPROVED", get_command(cid)
