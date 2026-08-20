"""
VentilationSafetyService: High-level guardrail registry and evaluation wrapper.
"""
from typing import Dict, Any, List, Optional
from backend.agents.ventilation_airflow.safety_engine import ventilation_safety_engine

class VentilationSafetyService:
    def __init__(self):
        self.engine = ventilation_safety_engine

    def validate_command(self, opportunity_code: str, current_value: float, proposed_value: float, context: Optional[Dict[str, Any]] = None):
        return self.engine.evaluate_safety(opportunity_code, current_value, proposed_value, context)

    def get_guardrail_definitions(self) -> Dict[str, Any]:
        return self.engine.GUARDRAILS

ventilation_safety_service = VentilationSafetyService()
