"""
VariableSpeedTelemetryService: Ingestion, validation, and real-time normalization
for all variable-speed VFD equipment points.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.data_pipeline.variable_speed_simulator import vs_simulator

class VariableSpeedTelemetryService:
    def __init__(self):
        self.simulator = vs_simulator

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns live normalized VFD telemetry with quality flags."""
        return self.simulator.generate_telemetry()

    def get_equipment_points(self, equipment_id: str) -> Dict[str, Any]:
        """Returns filtered telemetry for specific equipment."""
        sim = self.get_telemetry()
        eq = equipment_id.upper()
        if "FAN" in eq or "AHU" in eq:
            return sim.get("fan", {})
        elif "CHW" in eq:
            return sim.get("chw_pump", {})
        elif "CW" in eq or "COND" in eq:
            return sim.get("condenser_pump", {})
        elif "CT" in eq or "TOWER" in eq:
            return sim.get("cooling_tower", {})
        elif "PUMP" in eq:
            return sim.get("pump", {})
        return sim

vs_telemetry_service = VariableSpeedTelemetryService()
