"""JSON structured logs. Never print() for control-path events."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.middleware.request_id import current_request_id


def log_event(
    level: str,
    service: str,
    event: str,
    *,
    building_id: Optional[str] = None,
    opportunity: Optional[str] = None,
    command_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level.upper(),
        "service": service,
        "event": event,
        "request_id": current_request_id(),
    }
    if building_id:
        payload["building_id"] = building_id
    if opportunity:
        payload["opportunity"] = opportunity
    if command_id:
        payload["command_id"] = command_id
    if extra:
        payload.update(extra)
    sys.stdout.write(json.dumps(payload, default=str) + "\n")
    sys.stdout.flush()
