"""
PumpSpeedOptimizationAgent: Optimizes secondary distribution pump VFD speeds
according to actual flow requirements and differential pressure setpoint.
"""
from typing import Dict, Any, Optional
from backend.agents.variable_speed.common_engine import vs_engine
from backend.data_pipeline.variable_speed_simulator import vs_simulator

class PumpSpeedOptimizationAgent:
    def __init__(self):
        self.agent_id = "pump_speed_optimization_agent"
        self.equipment_id = "PUMP-GEN-01"
        self.engine = vs_engine
        self.mode = "AUTO_CLOSED_LOOP"

    def optimize(self, telemetry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        t = telemetry
        if not t:
            sim = vs_simulator.generate_telemetry()
            t = sim.get("pump", {})
        return self.engine.optimize_pump_speed(t)

pump_speed_agent = PumpSpeedOptimizationAgent()
