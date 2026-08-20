"""Scheduling agent — O1–O4. Index only; engines stay in scheduling_supervisory/."""
from __future__ import annotations

from typing import Any, Dict

from backend.agents._agent_spec import require_oid, row, stamp

AGENT_ID = "scheduling"
TITLE = "Scheduling & Supervisory Agent"
HREF = "/agents/scheduling"
API_PREFIX = "/api/agents/scheduling"
ORCHESTRATOR = "backend.agents.scheduling_supervisory.agent.SchedulingSupervisoryAgent"
IDS = ("O1", "O2", "O3", "O4")

OPPORTUNITIES = [
    row("O1", "Optimum Start/Stop Programming", "/agents/scheduling/optimum-start-stop", "backend.agents.scheduling_supervisory.o1_engine.OptimumStartStopEngine", "Thermodynamic pull-down trajectory and coasting stop."),
    row("O2", "Space Temperature Set Points & Control Bands", "/agents/scheduling/space-temperature", "backend.agents.scheduling_supervisory.o2_engine.SpaceTemperatureOptimizationEngine", "Occupancy-driven setpoint floating and deadband expansion."),
    row("O3", "Master Air Handling Unit Supply Air Temperature Signal", "/agents/scheduling/master-ahu-sat", "backend.agents.scheduling_supervisory.o3_engine.MasterAHUSATOptimizationEngine", "Guideline 36 trim and respond with rogue-zone isolation."),
    row("O4", "Staging of Chillers & Compressors", "/agents/scheduling/chiller-staging", "backend.agents.scheduling_supervisory.o4_engine.ChillerCompressorStagingEngine", "Thermal tonnage matching and CHWS reset."),
]


def describe() -> Dict[str, Any]:
    return {"agent_id": AGENT_ID, "title": TITLE, "href": HREF, "api_prefix": API_PREFIX, "orchestrator": ORCHESTRATOR, "opportunities": list(OPPORTUNITIES)}


def evaluate(oid: str, persist: bool = False, **kwargs: Any) -> Dict[str, Any]:
    """Read-only studio snapshot. Dispatch still requires evaluate_dispatch."""
    key = require_oid(oid, IDS)
    if key == "O1":
        from backend.services.o1_service import o1_service

        return stamp(key, o1_service.get_studio())
    if key == "O2":
        from backend.services.o2_service import o2_service

        return stamp(key, o2_service.get_studio(kwargs.get("zone_id", "VAV-101")))
    if key == "O3":
        from backend.services.o3_service import o3_service

        return stamp(key, o3_service.get_studio())
    from backend.services.o4_service import o4_service

    return stamp(key, o4_service.get_studio())
