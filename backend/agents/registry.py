"""Five HVAC agents: Scheduling, Plant Control, Ventilation, Variable Speed, Operations."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from backend.agents import operations_agent, plant_control_agent, scheduling_agent, variable_speed_agent, ventilation_agent
from backend.agents.opportunities.base_opportunity_agent import opportunity_agent_registry

AGENTS = (
    scheduling_agent,
    plant_control_agent,
    ventilation_agent,
    variable_speed_agent,
    operations_agent,
)

_BY_OID = {row["opportunity_id"]: mod for mod in AGENTS for row in mod.OPPORTUNITIES}


def list_agents() -> List[Dict[str, Any]]:
    return [mod.describe() for mod in AGENTS]


def agent_for_opportunity(oid: str):
    key = (oid or "").strip().upper()
    return _BY_OID.get(key)


def evaluate(oid: str, persist: bool = False, **kwargs: Any) -> Dict[str, Any]:
    key = (oid or "").strip().upper()
    mod = _BY_OID.get(key)
    if not mod:
        raise ValueError(f"Unknown official opportunity {oid!r}. Use O1–O20 (O6, O7, O8 separate).")
    return mod.evaluate(key, persist=persist, **kwargs)


def official_ids() -> Tuple[str, ...]:
    return tuple(row["opportunity_id"] for mod in AGENTS for row in mod.OPPORTUNITIES if row["opportunity_id"] != "O6-O8")


def opportunity_agent(oid: str):
    return opportunity_agent_registry.get(oid)
