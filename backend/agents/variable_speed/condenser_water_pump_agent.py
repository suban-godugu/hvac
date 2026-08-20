"""
CondenserWaterPumpAgent: Optimizes Condenser Water (CW) pump VFD speed based on chiller
heat rejection load and cooling tower interaction.
"""
from typing import Dict, Any, Optional
from backend.agents.variable_speed.common_engine import vs_engine
from backend.data_pipeline.variable_speed_simulator import vs_simulator

class CondenserWaterPumpAgent:
    def __init__(self):
        self.agent_id = "condenser_water_pump_agent"
        self.equipment_id = "CW-PUMP-01"
        self.engine = vs_engine
        self.mode = "AUTO_CLOSED_LOOP"

    def optimize(self, telemetry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        t = telemetry
        if not t:
            sim = vs_simulator.generate_telemetry()
            t = sim.get("condenser_pump", {})
        return self.engine.optimize_condenser_pump_speed(t)

condenser_water_pump_agent = CondenserWaterPumpAgent()
