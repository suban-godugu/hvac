"""Operations & Maintenance agent — O17–O20. Index only; engines stay in operations_maintenance/."""
from __future__ import annotations

from typing import Any, Dict

from backend.agents._agent_spec import require_oid, row, stamp

AGENT_ID = "operations"
TITLE = "Operations & Maintenance"
HREF = "/agents/operations-maintenance"
API_PREFIX = "/api/agents/operations-maintenance"
ORCHESTRATOR = "backend.agents.operations_maintenance.OperationsMaintenanceAgentOrchestrator"
IDS = ("O17", "O18", "O19", "O20")

OPPORTUNITIES = [
    row("O17", "Energy Management Planning", "/agents/operations-maintenance/energy-management-planning", "backend.agents.operations_maintenance.o17_energy_planning_engine.evaluate_o17", "Energy-management opportunities, targets, and baseline deviations."),
    row("O18", "Energy Management Training & Awareness", "/agents/operations-maintenance/training-awareness", "backend.agents.operations_maintenance.o18_training_engine.evaluate_o18", "Operator and occupant training related to HVAC energy use."),
    row("O19", "Energy Efficiency Maintenance", "/agents/operations-maintenance/equipment-maintenance", "backend.agents.operations_maintenance.o19_maintenance_engine.evaluate_o19", "Efficiency-focused maintenance that avoids unnecessary HVAC energy use."),
    row("O20", "Management of System Control Software", "/agents/operations-maintenance/control-software", "backend.agents.operations_maintenance.o20_control_software_engine.evaluate_o20", "Control-system health, configuration, and software issues."),
]


def describe() -> Dict[str, Any]:
    return {"agent_id": AGENT_ID, "title": TITLE, "href": HREF, "api_prefix": API_PREFIX, "orchestrator": ORCHESTRATOR, "opportunities": list(OPPORTUNITIES)}


def evaluate(oid: str, persist: bool = False, **kwargs: Any) -> Dict[str, Any]:
    key = require_oid(oid, IDS)
    from backend.services.operations_maintenance_opportunity_service import evaluate_opportunity

    return stamp(key, evaluate_opportunity(key, persist=persist))
