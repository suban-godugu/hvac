"""Map Safe-RL winner to O* CommandContract rows (PROPOSED only)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.agents.runtime.command import propose
from backend.agents.runtime.contracts import CommandContract


def map_to_commands(
    winner: Optional[Dict[str, Any]],
    *,
    zone_id: str,
    decision_id: str,
) -> List[Dict[str, Any]]:
    """Propose O-mapped control_commands; never apply or write BMS."""
    if not winner or winner.get("action_id") == "hold":
        return []
    if not winner.get("feasible", True):
        return []
    opp = winner.get("mapped_opportunity")
    point = winner.get("point_id")
    new_value = winner.get("new_value")
    if not opp or not point or new_value is None:
        return []

    reason = f"SAFE_RL→{opp} {winner.get('action_id')} (decision {decision_id})"
    contract = CommandContract(
        opportunity=str(opp),
        building=winner.get("building_id"),
        equipment=winner.get("equipment_id"),
        point=str(point),
        old_value=winner.get("old_value"),
        new_value=float(new_value),
        reason=reason,
        engine_version="safe_rl/1.0",
        config_version="1.0",
        safety_gates=[{"gate": "SAFE_RL_RECOMMEND", "decision_id": decision_id, "zone_id": zone_id}],
    )
    cmd = propose(contract, status="PROPOSED")
    return [cmd]
