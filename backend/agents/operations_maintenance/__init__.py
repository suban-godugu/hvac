"""Shared O&M agent orchestration for O17–O20."""
from __future__ import annotations
from typing import Any, Dict

from backend.agents.operations_maintenance.o17_energy_planning_engine import evaluate_o17
from backend.agents.operations_maintenance.o18_training_engine import evaluate_o18
from backend.agents.operations_maintenance.o19_maintenance_engine import evaluate_o19
from backend.agents.operations_maintenance.o20_control_software_engine import evaluate_o20

ENGINES = {
    "O17": evaluate_o17,
    "O18": evaluate_o18,
    "O19": evaluate_o19,
    "O20": evaluate_o20,
}


class OperationsMaintenanceAgentOrchestrator:
    def evaluate(self, oid: str, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        fn = ENGINES.get(oid)
        if not fn:
            raise ValueError(f"Unknown O&M opportunity: {oid}")
        return fn(snapshot)


om_orchestrator = OperationsMaintenanceAgentOrchestrator()
