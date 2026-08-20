from __future__ import annotations

from typing import Any, Dict, Optional

from database.models_platform import HvacApprovalDB
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
