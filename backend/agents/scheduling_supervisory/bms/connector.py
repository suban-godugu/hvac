from typing import Dict, Any
from .simulator import BMSSimulator
from ..state import SupervisoryState

class BMSConnector:
    """BACnet / Modbus / IP Gateway abstraction with write validation feedback and simulation backend."""

    def __init__(self, simulator: BMSSimulator = None):
        self.simulator = simulator or BMSSimulator()
        self.point_overrides: Dict[str, Any] = {}

    def read_all_telemetry(self) -> SupervisoryState:
        return self.simulator.state

    def write_point(self, point_id: str, value: Any, priority: int = 8) -> Dict[str, Any]:
        """Simulates writing to BACnet Commandable Point at specified BACnet priority (default 8=Manual / Supervisory)."""
        self.point_overrides[point_id] = value

        # Dispatch write to simulator
        if "SAT-SP" in point_id or "SAT_SP" in point_id:
            for ahu in self.simulator.state.ahus:
                if ahu.id in point_id:
                    ahu.sat_setpoint = float(value)
        elif "CHWS-T-SP" in point_id or "CHWS_SP" in point_id:
            self.simulator.state.chiller_plant.chws_setpoint = float(value)
        elif "CH-2-CMD" in point_id:
            for c in self.simulator.state.chiller_plant.chillers:
                if c.id == "CH-2":
                    c.status = bool(int(value))

        return {
            "success": True,
            "point_id": point_id,
            "written_value": value,
            "priority": priority,
            "feedback_ack": "BMS_WRITE_CONFIRMED"
        }

    def step_simulation(self, elapsed_minutes: int = 5) -> SupervisoryState:
        return self.simulator.step(elapsed_minutes, manual_overrides=self.point_overrides)
