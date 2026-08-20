"""
ChwPumpOptimizationAgent: Optimizes Chilled Water secondary pump VFD speeds
maintaining required delta-T and cooling coil capacity without chiller lift penalties.
"""
from typing import Dict, Any, Optional
from backend.agents.variable_speed.common_engine import vs_engine
from backend.data_pipeline.variable_speed_simulator import vs_simulator

class ChwPumpOptimizationAgent:
    def __init__(self):
        self.agent_id = "chw_pump_optimization_agent"
        self.equipment_id = "CHW-PUMP-01"
        self.engine = vs_engine
        self.mode = "AUTO_CLOSED_LOOP"

    def optimize(self, telemetry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        t = telemetry
        if not t:
            sim = vs_simulator.generate_telemetry()
            t = sim.get("chw_pump", {})
        return self.engine.optimize_chw_pump_speed(t)

chw_pump_agent = ChwPumpOptimizationAgent()
