"""Ventilation agent — O10–O13. Index only; engines stay in ventilation_airflow/."""
from __future__ import annotations

from typing import Any, Dict

from backend.agents._agent_spec import require_oid, row, stamp

AGENT_ID = "ventilation"
TITLE = "Ventilation & Air Flow Optimizations"
HREF = "/agents/ventilation-airflow"
API_PREFIX = "/api/agents/ventilation-airflow"
ORCHESTRATOR = "backend.agents.ventilation_airflow.o10_o13_engines"
IDS = ("O10", "O11", "O12", "O13")

OPPORTUNITIES = [
    row("O10", "Economy Cycle", "/agents/ventilation-airflow/economy-cycle", "backend.agents.ventilation_airflow.o10_o13_engines.evaluate_o10", "Enthalpy economizer outdoor-air free cooling."),
    row("O11", "Night Purge", "/agents/ventilation-airflow/night-purge", "backend.agents.official_opportunities.o11_night_purge.evaluate_night_purge", "Night-time outdoor-air purge of stored building heat."),
    row("O12", "Demand Control Ventilation — CO₂", "/agents/ventilation-airflow/demand-ventilation", "backend.agents.ventilation_airflow.o10_o13_engines.evaluate_o12", "Occupancy- and CO₂-driven outdoor-air optimization."),
    row("O13", "Demand Control Ventilation — CO", "/agents/ventilation-airflow/dcv-co", "backend.agents.official_opportunities.o13_dcv_co.evaluate_dcv_co", "CO-based ventilation for carparks and loading docks."),
]


def describe() -> Dict[str, Any]:
    return {"agent_id": AGENT_ID, "title": TITLE, "href": HREF, "api_prefix": API_PREFIX, "orchestrator": ORCHESTRATOR, "opportunities": list(OPPORTUNITIES)}


def evaluate(oid: str, persist: bool = False, **kwargs: Any) -> Dict[str, Any]:
    key = require_oid(oid, IDS)
    from backend.services.ventilation_opportunity_service import evaluate_opportunity

    return stamp(key, evaluate_opportunity(key, persist=persist))
