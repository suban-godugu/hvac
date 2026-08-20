"""
CoolingTowerFanOptimizationAgent: Determines optimal cooling tower fan VFD speeds
to minimize combined cooling tower fan power PLUS chiller compressor power.
"""
from typing import Dict, Any, Optional
from backend.agents.variable_speed.common_engine import vs_engine
from backend.data_pipeline.variable_speed_simulator import vs_simulator

class CoolingTowerFanOptimizationAgent:
    def __init__(self):
        self.agent_id = "cooling_tower_fan_optimization_agent"
        self.equipment_id = "CT-FAN-01"
        self.engine = vs_engine
        self.mode = "AUTO_CLOSED_LOOP"

    def optimize(self, telemetry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        t = telemetry
        if not t:
            sim = vs_simulator.generate_telemetry()
            t = sim.get("cooling_tower", {})
            t["wet_bulb_c"] = sim.get("weather", {}).get("wet_bulb_c", 21.0)
        return self.engine.optimize_cooling_tower_fan_speed(t)

cooling_tower_fan_agent = CoolingTowerFanOptimizationAgent()
