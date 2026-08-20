"""Deterministic opportunity agents. LLM must not invent recommendations."""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from backend.agents.runtime.apply import apply_setpoint
from backend.agents.runtime.verification import rollback_command, verify_command
from backend.knowledge.hvac_guide_catalog import catalog_record, is_advisory, source_reference
from backend.middleware.request_id import current_request_id
from backend.services.hvac_safety_contract import evaluate_dispatch


CONTROL_METHODS = ("evaluate", "recommend", "validate", "explain", "get_state", "prepare_dispatch", "dispatch", "verify", "rollback")
ADVISORY_METHODS = ("evaluate", "recommend", "validate", "explain", "get_state")


def _pick(payload: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


def wrap_opportunity_payload(oid: str, raw: Dict[str, Any], request_id: Optional[str] = None) -> Dict[str, Any]:
    """Envelope around an existing engine result. Does not invent telemetry values."""
    src = dict(raw or {})
    catalog = catalog_record(oid) or {}
    rid = request_id or src.get("request_id") or current_request_id() or str(uuid.uuid4())
    provenance = src.get("provenance")
    if not isinstance(provenance, dict):
        provenance = {
            "source": src.get("source") or src.get("telemetry_source"),
            "quality": src.get("quality") or src.get("telemetry_quality"),
            "age_seconds": src.get("telemetry_age") or src.get("age_seconds"),
            "label": src.get("ui_state") or src.get("classified_status") or src.get("provenance_label"),
        }
    energy = src.get("energy_impact")
    energy_class = src.get("energy_impact_class")
    if energy is None and energy_class is None:
        energy_class = "NO_DATA"
    elif energy_class is None:
        energy_class = "ESTIMATED" if energy is not None else "NO_DATA"
    out = {
        "request_id": rid,
        "opportunity_id": oid,
        "status": src.get("status") or src.get("ui_state"),
        "provenance": provenance,
        "current": src.get("current") if "current" in src else src.get("current_state"),
        "recommended": src.get("recommended") if "recommended" in src else src.get("optimized_state"),
        "decision": src.get("decision") or src.get("supervisory_decision"),
        "confidence": src.get("confidence"),
        "safety": src.get("safety") or src.get("safety_result"),
        "rationale": src.get("rationale") or src.get("reasons") or src.get("reason"),
        "energy_impact": energy,
        "energy_impact_class": energy_class,
        "source_reference": src.get("source_reference") or catalog.get("source_reference") or source_reference(oid),
        "engine": src,
    }
    if out["current"] is None:
        val = _pick(src, "current_value")
        out["current"] = None if val is None else {"value": val, "unit": src.get("unit")}
    if out["recommended"] is None:
        val = _pick(src, "recommended_value", "optimized_value", "target_value")
        out["recommended"] = None if val is None else {"value": val, "unit": src.get("unit")}
    return out


class BaseOpportunityAgent:
    opportunity_id: str = ""
    class_name: str = "BaseOpportunityAgent"

    def evaluate(self, persist: bool = False, **kwargs: Any) -> Dict[str, Any]:
        from backend.agents.registry import evaluate as registry_evaluate

        raw = registry_evaluate(self.opportunity_id, persist=persist, **kwargs)
        return wrap_opportunity_payload(self.opportunity_id, raw)

    def recommend(self, persist: bool = False, **kwargs: Any) -> Dict[str, Any]:
        return self.evaluate(persist=persist, **kwargs)

    def validate(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        body = payload or {}
        catalog = catalog_record(self.opportunity_id)
        missing_inputs = []
        if catalog:
            current = body.get("current") or body.get("telemetry") or {}
            if isinstance(current, dict) and not current:
                missing_inputs = list(catalog.get("required_inputs") or [])
        return {
            "opportunity_id": self.opportunity_id,
            "advisory": is_advisory(self.opportunity_id),
            "ok": not missing_inputs,
            "missing_inputs": missing_inputs,
            "source_reference": source_reference(self.opportunity_id),
        }

    def explain(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Structured why-this-recommendation. Does not invent engineering step 4."""
        body = payload or self.evaluate(persist=False)
        engine = body.get("engine") if isinstance(body.get("engine"), dict) else body
        catalog = catalog_record(self.opportunity_id) or {}
        calc = engine.get("calculation") or engine.get("rule_applied") or engine.get("engineering_rule")
        steps = [
            {"step": 1, "label": "Telemetry observed", "detail": engine.get("telemetry") or engine.get("current") or body.get("current")},
            {"step": 2, "label": "Current operating condition", "detail": engine.get("current_state") or body.get("current")},
            {"step": 3, "label": "Guide strategy applicable", "detail": catalog.get("strategy_summary")},
            {"step": 4, "label": "Engineering calculation/rule applied", "detail": calc, "invented": False},
            {"step": 5, "label": "Equipment constraints", "detail": engine.get("constraints") or engine.get("limits")},
            {"step": 6, "label": "Recommended action", "detail": body.get("recommended") or engine.get("recommended_value")},
            {"step": 7, "label": "Expected effect", "detail": engine.get("expected_effect") or body.get("energy_impact")},
            {"step": 8, "label": "Safety restrictions", "detail": body.get("safety") or engine.get("blockers")},
        ]
        if calc is None:
            steps[3]["detail"] = None
            steps[3]["note"] = "NO_DATA — rule output is only shown when the engine calculated it"
        return {
            "opportunity_id": self.opportunity_id,
            "decision": body.get("decision"),
            "steps": steps,
            "source_reference": catalog.get("source_reference"),
        }

    def get_state(self, **kwargs: Any) -> Dict[str, Any]:
        return self.evaluate(persist=False, **kwargs)

    def prepare_dispatch(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if is_advisory(self.opportunity_id):
            return {
                "allowed": False,
                "code": "ADVISORY_ONLY",
                "message": f"{self.opportunity_id} does not automatically write HVAC setpoints.",
                "request_id": current_request_id(),
            }
        ctx = dict(context or {})
        ctx.setdefault("opportunity_id", self.opportunity_id)
        ok, reason, classified = evaluate_dispatch(ctx)
        if ok:
            return {"allowed": True, "code": "PASS", "message": reason, "request_id": current_request_id(), **classified}
        return {
            "allowed": False,
            "code": classified.get("code") or "SAFETY_FAIL",
            "message": reason,
            "request_id": current_request_id(),
            **classified,
        }

    def dispatch(self, context: Dict[str, Any]) -> Dict[str, Any]:
        gate = self.prepare_dispatch(context)
        if not gate.get("allowed"):
            return gate
        command_id = context.get("command_id")
        point_id = context.get("point_id")
        value = context.get("target_value")
        if not command_id or not point_id or value is None:
            return {
                "allowed": False,
                "code": "MISSING_TARGET",
                "message": "Dispatch requires command_id, point_id, and target_value from the engine.",
                "request_id": current_request_id(),
            }
        success, reason = apply_setpoint(str(command_id), str(point_id), float(value), context)
        return {
            "allowed": success,
            "code": "PASS" if success else "SAFETY_FAIL",
            "message": reason,
            "request_id": current_request_id(),
        }

    def verify(self, command_id: str, expected: Optional[float] = None) -> Dict[str, Any]:
        if is_advisory(self.opportunity_id):
            return self.prepare_dispatch({})
        ok, reason = verify_command(command_id, expected=expected)
        return {"ok": ok, "result": reason, "request_id": current_request_id()}

    def rollback(self, command_id: str) -> Dict[str, Any]:
        if is_advisory(self.opportunity_id):
            return self.prepare_dispatch({})
        ok, reason = rollback_command(command_id)
        return {"ok": ok, "result": reason, "request_id": current_request_id()}


class OptimumStartStopAgent(BaseOpportunityAgent):
    opportunity_id = "O1"
    class_name = "OptimumStartStopAgent"


class SpaceTemperatureAgent(BaseOpportunityAgent):
    opportunity_id = "O2"
    class_name = "SpaceTemperatureAgent"


class MasterAHUSATAgent(BaseOpportunityAgent):
    opportunity_id = "O3"
    class_name = "MasterAHUSATAgent"


class ChillerStagingAgent(BaseOpportunityAgent):
    opportunity_id = "O4"
    class_name = "ChillerStagingAgent"


class DuctStaticPressureAgent(BaseOpportunityAgent):
    opportunity_id = "O5"
    class_name = "DuctStaticPressureAgent"


class HHWResetAgent(BaseOpportunityAgent):
    opportunity_id = "O6"
    class_name = "HHWResetAgent"


class CHWResetAgent(BaseOpportunityAgent):
    opportunity_id = "O7"
    class_name = "CHWResetAgent"


class CWResetAgent(BaseOpportunityAgent):
    opportunity_id = "O8"
    class_name = "CWResetAgent"


class EEVRetrofitAgent(BaseOpportunityAgent):
    opportunity_id = "O9"
    class_name = "EEVRetrofitAgent"


class EconomyCycleAgent(BaseOpportunityAgent):
    opportunity_id = "O10"
    class_name = "EconomyCycleAgent"


class NightPurgeAgent(BaseOpportunityAgent):
    opportunity_id = "O11"
    class_name = "NightPurgeAgent"


class CO2DCVAgent(BaseOpportunityAgent):
    opportunity_id = "O12"
    class_name = "CO2DCVAgent"


class CODCVAgent(BaseOpportunityAgent):
    opportunity_id = "O13"
    class_name = "CODCVAgent"


class SecondaryCHWPumpAgent(BaseOpportunityAgent):
    opportunity_id = "O14"
    class_name = "SecondaryCHWPumpAgent"


class AirCooledHeadPressureAgent(BaseOpportunityAgent):
    opportunity_id = "O15"
    class_name = "AirCooledHeadPressureAgent"


class WaterCooledHeadPressureAgent(BaseOpportunityAgent):
    opportunity_id = "O16"
    class_name = "WaterCooledHeadPressureAgent"


class EnergyManagementPlanningAgent(BaseOpportunityAgent):
    opportunity_id = "O17"
    class_name = "EnergyManagementPlanningAgent"


class TrainingAwarenessAgent(BaseOpportunityAgent):
    opportunity_id = "O18"
    class_name = "TrainingAwarenessAgent"


class EnergyEfficiencyMaintenanceAgent(BaseOpportunityAgent):
    opportunity_id = "O19"
    class_name = "EnergyEfficiencyMaintenanceAgent"


class ControlSoftwareManagementAgent(BaseOpportunityAgent):
    opportunity_id = "O20"
    class_name = "ControlSoftwareManagementAgent"


AGENT_CLASSES = {
    "O1": OptimumStartStopAgent,
    "O2": SpaceTemperatureAgent,
    "O3": MasterAHUSATAgent,
    "O4": ChillerStagingAgent,
    "O5": DuctStaticPressureAgent,
    "O6": HHWResetAgent,
    "O7": CHWResetAgent,
    "O8": CWResetAgent,
    "O9": EEVRetrofitAgent,
    "O10": EconomyCycleAgent,
    "O11": NightPurgeAgent,
    "O12": CO2DCVAgent,
    "O13": CODCVAgent,
    "O14": SecondaryCHWPumpAgent,
    "O15": AirCooledHeadPressureAgent,
    "O16": WaterCooledHeadPressureAgent,
    "O17": EnergyManagementPlanningAgent,
    "O18": TrainingAwarenessAgent,
    "O19": EnergyEfficiencyMaintenanceAgent,
    "O20": ControlSoftwareManagementAgent,
}


class OpportunityAgentRegistry:
    def __init__(self) -> None:
        self._agents = {oid: cls() for oid, cls in AGENT_CLASSES.items()}

    def get(self, oid: str) -> BaseOpportunityAgent:
        key = (oid or "").strip().upper()
        agent = self._agents.get(key)
        if not agent:
            raise ValueError(f"Unknown official opportunity {oid!r}. Use O1–O20.")
        return agent

    def all_ids(self):
        return tuple(f"O{i}" for i in range(1, 21))


opportunity_agent_registry = OpportunityAgentRegistry()
