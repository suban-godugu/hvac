from __future__ import annotations

from typing import Any, Dict, Optional

from backend.middleware.request_id import current_request_id
from backend.services.platform_ops_service import record_control_audit


def audit_command(user: Optional[Dict[str, Any]], action: str, command: Dict[str, Any], reason: Optional[str] = None) -> str:
    return record_control_audit(
        user=user,
        action=action,
        opportunity_id=command.get("opportunity"),
        previous_value=command.get("old_value"),
        requested_value=command.get("new_value"),
        reason=reason or command.get("reason"),
        request_id=current_request_id(),
        building_id=command.get("building_id"),
    )
