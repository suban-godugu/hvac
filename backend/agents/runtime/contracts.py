from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

COMMAND_STATES = (
    "PROPOSED",
    "PENDING_APPROVAL",
    "APPROVED",
    "APPLYING",
    "APPLIED",
    "VERIFYING",
    "VERIFIED",
    "VERIFICATION_FAILED",
    "ROLLBACK",
    "ROLLED_BACK",
    "BLOCKED",
)

COORDINATOR_PRIORITY = (
    "SAFETY",
    "EQUIPMENT_PROTECTION",
    "COMFORT",
    "OPERATIONAL_STABILITY",
    "OPTIMIZATION",
)


@dataclass
class CommandContract:
    opportunity: str
    building: Optional[str]
    equipment: Optional[str]
    point: Optional[str]
    old_value: Optional[float]
    new_value: Optional[float]
    reason: str
    engine_version: str = "1.0"
    config_version: str = "1.0"
    safety_gates: List[Dict[str, Any]] = field(default_factory=list)
    command_id: Optional[str] = None
    requested_by: Optional[str] = None
    approval_id: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "opportunity": self.opportunity,
            "building": self.building,
            "equipment": self.equipment,
            "point": self.point,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "reason": self.reason,
            "engine_version": self.engine_version,
            "config_version": self.config_version,
            "safety_gates": self.safety_gates,
            "command_id": self.command_id,
            "requested_by": self.requested_by,
            "approval_id": self.approval_id,
        }
