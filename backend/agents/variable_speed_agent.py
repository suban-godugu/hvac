"""Variable Speed agent — O14–O16. Index only; engines stay in official_opportunities/."""
from __future__ import annotations

from typing import Any, Dict, Optional

from backend.agents._agent_spec import require_oid, row, stamp

AGENT_ID = "variable-speed"
TITLE = "Variable Speed Systems"
HREF = "/agents/variable-speed"
API_PREFIX = "/api/agents/variable-speed"
ORCHESTRATOR = "backend.agents.variable_speed.variable_speed_agent.VariableSpeedAgent"
IDS = ("O14", "O15", "O16")

OPPORTUNITIES = [
    row("O14", "Optimised Secondary Chilled Water Pumping", "/agents/variable-speed/chilled-water-pump", "backend.agents.official_opportunities.o14_secondary_chw.evaluate_secondary_chw", "Secondary CHW pump speed vs differential pressure."),
    row("O15", "Variable Head Pressure Control — Air-Cooled Condensers", "/agents/variable-speed/air-cooled-head-pressure", "backend.agents.official_opportunities.o15_air_cooled_hp.evaluate_air_cooled_hp", "Air-cooled condenser head-pressure control."),
    row("O16", "Variable Head Pressure Control — Water-Cooled Condensers", "/agents/variable-speed/water-cooled-head-pressure", "backend.agents.official_opportunities.o16_water_cooled_hp.evaluate_water_cooled_hp", "Water-cooled condenser head pressure and pumping energy."),
]


def describe() -> Dict[str, Any]:
    return {"agent_id": AGENT_ID, "title": TITLE, "href": HREF, "api_prefix": API_PREFIX, "orchestrator": ORCHESTRATOR, "opportunities": list(OPPORTUNITIES)}


def evaluate(oid: str, persist: bool = False, building_id: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
    key = require_oid(oid, IDS)
    if key == "O14":
        from backend.services.o14_service import evaluate_o14

        return stamp(key, evaluate_o14(persist=persist, building_id=building_id))
    if key == "O15":
        from backend.services.o15_service import evaluate_o15

        return stamp(key, evaluate_o15(persist=persist, building_id=building_id))
    from backend.services.o16_service import evaluate_o16

    return stamp(key, evaluate_o16(persist=persist, building_id=building_id))
