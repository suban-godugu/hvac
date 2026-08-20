"""
RollbackEngine: Automatically restores verified safe baseline values through BMS Gateway.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from backend.agents.scheduling_supervisory.state import CandidateAction, BMSWriteResult
from backend.agents.scheduling_supervisory.gateway import BMSGatewayBase


class RollbackEngine:
    def __init__(self, gateway: BMSGatewayBase):
        self.gateway = gateway
        self.rollback_history: List[Dict[str, Any]] = []

    def execute_rollback(
        self,
        action: CandidateAction,
        reason: str = "Verification threshold violation / Safety trip"
    ) -> BMSWriteResult:
        """
        Executes an immediate rollback to the action's rollback_value / safe baseline.
        """
        rollback_val = action.rollback_value if action.rollback_value is not None else action.current_value
        if rollback_val is None:
            rollback_val = 0.0

        write_res = self.gateway.write_point(
            point_id=action.point_id,
            value=rollback_val,
            priority=8  # High priority override for safety reversion
        )

        record = {
            "action_id": action.id,
            "point_id": action.point_id,
            "rolled_back_from": action.proposed_value,
            "restored_value": rollback_val,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
            "success": write_res.success
        }
        self.rollback_history.append(record)
        return write_res
