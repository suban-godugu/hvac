"""
FanSpeedOptimizationAgent: Optimizes variable-speed AHU/supply fans to minimize fan kW
while satisfying airflow demand, duct static pressure, and critical zone dampers.
"""
from typing import Dict, Any, Optional
from backend.agents.variable_speed.common_engine import vs_engine
from backend.data_pipeline.variable_speed_simulator import vs_simulator

class FanSpeedOptimizationAgent:
    def __init__(self):
        self.agent_id = "fan_speed_optimization_agent"
        self.equipment_id = "AHU-FAN-01"
        self.engine = vs_engine
        self.mode = "AUTO_CLOSED_LOOP"

    def optimize(self, telemetry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        t = telemetry
        if not t:
            sim = vs_simulator.generate_telemetry()
            t = sim.get("fan", {})
            t["weather"] = sim.get("weather", {})
        return self.engine.optimize_fan_speed(t)

fan_speed_agent = FanSpeedOptimizationAgent()
