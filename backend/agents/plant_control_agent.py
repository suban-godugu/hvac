"""Plant Control agent — O5–O9. Index only; engines stay in plant_control/."""
from __future__ import annotations

from typing import Any, Dict

from backend.agents._agent_spec import require_oid, row, stamp

AGENT_ID = "plant-control"
TITLE = "Plant Control Parameter Optimizations"
HREF = "/agents/plant-control"
API_PREFIX = "/api/agents/plant-control"
ORCHESTRATOR = "backend.agents.plant_control.plant_control_agent.PlantControlAgent"
IDS = ("O5", "O6", "O7", "O8", "O9")

OPPORTUNITIES = [
    row("O5", "Duct Static Pressure Reset", "/agents/plant-control/duct-static-pressure", "backend.agents.plant_control.o5_duct_static_pressure.engine.O5DuctStaticPressureAgent", "Trim-and-respond duct static pressure for fan kW reduction."),
    row("O6", "Heating Hot Water Temperature Reset", "/agents/plant-control/temperature-reset?mode=HHW", "backend.agents.plant_control.o6_heating_water_reset.engine", "Lowest HHW flow temperature that still meets heating demand."),
    row("O7", "Chilled Water Temperature Reset", "/agents/plant-control/temperature-reset?mode=CHW", "backend.agents.plant_control.o7_chilled_water_reset.engine", "Raise CHW supply in mild weather without losing dehumidification."),
    row("O8", "Condenser Water Temperature Reset", "/agents/plant-control/temperature-reset?mode=CW", "backend.agents.plant_control.o8_condenser_water_reset.engine", "Track wet-bulb with tower approach."),
    row("O9", "Retrofit of Electronic Expansion Valve", "/agents/plant-control/electronic-expansion-valve", "backend.agents.plant_control.o9_electronic_expansion_valve.engine.O9ElectronicExpansionValveAgent", "TXV to EXV retrofit engineering assessment."),
]


def describe() -> Dict[str, Any]:
    return {"agent_id": AGENT_ID, "title": TITLE, "href": HREF, "api_prefix": API_PREFIX, "orchestrator": ORCHESTRATOR, "opportunities": list(OPPORTUNITIES)}


def evaluate(oid: str, persist: bool = False, **kwargs: Any) -> Dict[str, Any]:
    key = require_oid(oid, IDS)
    from backend.services.plant_control_service import plant_control_service as pcs

    if key == "O5":
        return stamp(key, pcs.get_o5_state())
    if key == "O6":
        return stamp(key, pcs.get_o6_state())
    if key == "O7":
        return stamp(key, pcs.get_o7_state())
    if key == "O8":
        return stamp(key, pcs.get_o8_state())
    return stamp(key, pcs.get_o9_assessment())
