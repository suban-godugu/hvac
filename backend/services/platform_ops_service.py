"""Persist control-path audit and SAFE_MODE. Product alert/approval queues are not exposed."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from database.session import SessionLocal
from database.models_platform import ControlAuditLogDB, PlatformSettingDB


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def record_control_audit(
    *,
    user: Optional[Dict[str, Any]],
    action: str,
    opportunity_id: Optional[str] = None,
    previous_value: Any = None,
    requested_value: Any = None,
    decision: Optional[str] = None,
    safety_status: Optional[str] = None,
    telemetry_status: Optional[str] = None,
    approval_status: Optional[str] = None,
    reason: Optional[str] = None,
    request_id: Optional[str] = None,
    building_id: Optional[str] = None,
) -> str:
    rid = request_id or uuid.uuid4().hex
    user = user or {}
    db = SessionLocal()
    try:
        db.add(
            ControlAuditLogDB(
                request_id=rid,
                user_id=user.get("user_id"),
                role=user.get("role"),
                timestamp=_now(),
                building_id=building_id or user.get("building_id"),
                opportunity_id=opportunity_id,
                action=action,
                previous_value=None if previous_value is None else str(previous_value),
                requested_value=None if requested_value is None else str(requested_value),
                decision=decision,
                safety_status=safety_status,
                telemetry_status=telemetry_status,
                approval_status=approval_status,
                reason=reason,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
    return rid


def get_safe_mode() -> bool:
    from backend.services.hvac_safety_contract import is_safe_mode

    return is_safe_mode()


def set_safe_mode(enabled: bool) -> None:
    db = SessionLocal()
    try:
        row = db.query(PlatformSettingDB).filter_by(key="SAFE_MODE").first()
        val = "1" if enabled else "0"
        if row:
            row.value = val
            row.updated_at = _now()
        else:
            db.add(PlatformSettingDB(key="SAFE_MODE", value=val, updated_at=_now()))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
