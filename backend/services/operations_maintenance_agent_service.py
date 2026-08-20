"""O&M agent service facade — orchestrates O17–O20 engines."""
from backend.agents.operations_maintenance import om_orchestrator, ENGINES

def evaluate_om_agent(oid: str, snapshot: dict) -> dict:
    return om_orchestrator.evaluate(oid, snapshot)

__all__ = ["om_orchestrator", "ENGINES", "evaluate_om_agent"]
