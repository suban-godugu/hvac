from __future__ import annotations

from typing import Any, Dict, Optional

from backend.agents.runtime.command import active_for_point

PRIORITY = {
    "SAFETY": 0,
    "EQUIPMENT_PROTECTION": 1,
    "COMFORT": 2,
    "OPERATIONAL_STABILITY": 3,
    "OPTIMIZATION": 4,
}


def resolve(incoming: Dict[str, Any]) -> Dict[str, Any]:
    """Keep one active command per point. Higher-priority (lower number) wins."""
    point_id = incoming.get("point") or incoming.get("point_id")
    if not point_id:
        return {"action": "ALLOW", "reason": "no-point"}
    existing = active_for_point(point_id)
    if not existing:
        return {"action": "ALLOW", "reason": "no-conflict"}
    inc_p = PRIORITY.get((incoming.get("priority") or "OPTIMIZATION").upper(), 4)
    # Existing applied optimization yields to safety
    if inc_p == 0:
        return {"action": "OVERRIDE", "reason": "SAFETY", "existing": existing}
    return {"action": "HOLD", "reason": "ACTIVE_COMMAND", "existing": existing}
