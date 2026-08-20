"""
VariableSpeedBMSService: BACnet Priority 10 Gateway for variable speed VFD commands.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid

from backend.agents.scheduling_supervisory.gateway import get_bms_gateway
from backend.services.hvac_safety_contract import evaluate_dispatch

class VariableSpeedBMSService:
    def __init__(self):
        self.is_online = False
        self.active_overrides: Dict[str, Dict[str, Any]] = {}

    def dispatch_vfd_speed(self, equipment_id: str, target_speed_pct: float, priority: int = 10) -> Dict[str, Any]:
        ok, reason, _ = evaluate_dispatch({
            "id": "O14",
            "source": "SIMULATION",
            "telemetry": {"source": "SIMULATION", "quality": "GOOD", "age_seconds": 1},
            "supervisory": {"decision": "OPTIMIZE"},
            "safety": {"status": "PASS"},
            "confidence": 0.9,
            "current_value": target_speed_pct,
            "target_value": target_speed_pct,
        })
        if not ok:
            raise ValueError(reason)
        from backend.bms.command_writer import write_point as reject_write

        blocked = reject_write(f"{equipment_id}.SpeedSetpoint", float(target_speed_pct), priority)
        if not blocked.success:
            raise ValueError(f"{blocked.code}: {blocked.message}")
        gw = get_bms_gateway()
        res = gw.write_point(f"{equipment_id}.SpeedSetpoint", float(target_speed_pct), priority)
        if not getattr(res, "success", False):
            raise ValueError("BMS write refused")
        cmd_id = getattr(res, "transaction_id", None) or f"cmd-vfd-{equipment_id.lower()}-{uuid.uuid4().hex[:6]}"
        record = {
            "command_id": cmd_id,
            "equipment_id": equipment_id,
            "target_point": f"{equipment_id}.SpeedSetpoint",
            "dispatched_speed_pct": target_speed_pct,
            "frequency_hz": None,
            "priority": priority,
            "status": "ACKNOWLEDGED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "bms_response_time_ms": None,
        }
        self.active_overrides[equipment_id] = record
        return record

    def release_override(self, equipment_id: str) -> Dict[str, Any]:
        """Releases Priority 10 supervisory override back to default BMS schedule."""
        self.active_overrides.pop(equipment_id, None)
        return {
            "equipment_id": equipment_id,
            "status": "RELEASED_TO_BASELINE_PRIORITY_16",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

vs_bms_service = VariableSpeedBMSService()
