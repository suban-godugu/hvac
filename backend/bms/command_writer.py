"""Phase 1: physical BMS writes are never executed."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from backend.bms.base import WRITE_DISABLED, WriteOutcome, utc_now
from backend.middleware.request_id import current_request_id


def write_enabled_flag() -> bool:
    return os.getenv("HVAC_BMS_WRITE_ENABLED", "0").strip() in ("1", "true", "TRUE")


def physical_writes_allowed() -> bool:
    """Phase 1 commissioning: no physical writes regardless of UI."""
    return False


def write_disabled_body(message: Optional[str] = None) -> Dict[str, Any]:
    return {
        "code": WRITE_DISABLED,
        "message": message or "BMS writes are disabled during read-only commissioning.",
        "request_id": current_request_id(),
    }


def write_point(point_id: str, value: float, priority: int = 10) -> WriteOutcome:
    del priority
    return WriteOutcome(
        success=False,
        code=WRITE_DISABLED,
        message="BMS writes are disabled during read-only commissioning.",
        point_id=point_id,
        value=value,
        timestamp=utc_now().isoformat(),
    )


def write_points(writes: List[Dict[str, Any]]) -> List[WriteOutcome]:
    return [write_point(str(w.get("point_id") or ""), float(w.get("value") or 0), int(w.get("priority") or 10)) for w in writes]
