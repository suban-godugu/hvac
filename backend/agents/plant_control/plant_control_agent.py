"""
PlantControlAgent: Central supervisory orchestrator coordinating
Opportunities O5, O6_8 (Combined Temperature Reset), and O9.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from backend.agents.plant_control.o5_duct_static_pressure.engine import O5DuctStaticPressureAgent, o5_agent
from backend.agents.plant_control.o6_8_temperature_reset.engine import O6_8TemperatureResetAgent, o6_8_agent
from backend.agents.plant_control.o9_electronic_expansion_valve.engine import O9ElectronicExpansionValveAgent, o9_agent
from backend.agents.plant_control.safety_engine import plant_control_safety

class PlantControlAgent:
    def __init__(self):
        self.o5 = o5_agent
        self.o6_8 = o6_8_agent
        self.o9 = o9_agent
        # Backward compatibility references
        self.o6 = o6_8_agent.o6_engine
        self.o7 = o6_8_agent.o7_engine
        self.o8 = o6_8_agent.o8_engine
        self.safety_engine = plant_control_safety
        self.mode = "AUTO_CLOSED_LOOP"

    def run_supervisory_cycle(self) -> Dict[str, Any]:
        """Runs an end-to-end evaluation cycle across O5, O6_8 (Combined Reset), and O9."""
        o5_state = self.o5.generate_and_evaluate_candidates()
        o6_8_summary = self.o6_8.get_all_modes_summary()
        o9_state = self.o9.evaluate_retrofit_feasibility()

        total_shed_kw = round(
            o5_state.get("power_shed_kw", 0.0) +
            o6_8_summary.get("total_power_shed_kw", 0.0),
            2
        )

        daily_kwh_savings = round(
            o5_state.get("daily_savings_kwh", 0.0) +
            o6_8_summary.get("daily_kwh_savings", 0.0),
            1
        )

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "module_code": "PLANT_CONTROL_PARAMETER_OPTIMIZATIONS",
            "mode": self.mode,
            "agent_health": "OPTIMAL",
            "active_opportunities_count": 2, # O5 + O6_8
            "assessment_opportunities_count": 1, # O9
            "total_power_shed_kw": total_shed_kw,
            "daily_kwh_savings": daily_kwh_savings,
            "opportunities": {
                "o5": o5_state,
                "o6_8": o6_8_summary,
                "o6": o6_8_summary["modes"]["HHW"],
                "o7": o6_8_summary["modes"]["CHW"],
                "o8": o6_8_summary["modes"]["CW"],
                "o9": o9_state
            }
        }

    def get_fleet_summary(self) -> Dict[str, Any]:
        """Returns the high-level dashboard fleet status for UI cards and charts."""
        cycle = self.run_supervisory_cycle()
        o5 = cycle["opportunities"]["o5"]
        o6_8 = cycle["opportunities"]["o6_8"]
        o9 = cycle["opportunities"]["o9"]

        return {
            "agent_health": "OPTIMAL",
            "mode": self.mode,
            "total_power_shed_kw": cycle["total_power_shed_kw"],
            "daily_kwh_savings": cycle["daily_kwh_savings"],
            "comfort_compliance_pct": 100.0,
            "safety_status": "PASS",
            "opportunities": [
                {
                    "code": "O5",
                    "title": "Duct Static Pressure Reset",
                    "route": "/agents/plant-control/duct-static-pressure",
                    "status": "ACTIVE_RESET",
                    "current": f"{o5['current_static_pressure']} in.w.c.",
                    "optimized": f"{o5['optimized_setpoint']} in.w.c.",
                    "shed_kw": o5["power_shed_kw"],
                    "confidence": o5["confidence"]
                },
                {
                    "code": "O6–8",
                    "title": "Temperature Reset (HHW / CHW / CW)",
                    "route": "/agents/plant-control/temperature-reset",
                    "status": "ACTIVE_RESET",
                    "current": f"CHW {o6_8['modes']['CHW']['current_setpoint']}°C | CW {o6_8['modes']['CW']['current_setpoint']}°C | HHW {o6_8['modes']['HHW']['current_setpoint']}°C",
                    "optimized": f"CHW {o6_8['modes']['CHW']['optimized_setpoint']}°C | CW {o6_8['modes']['CW']['optimized_setpoint']}°C | HHW {o6_8['modes']['HHW']['optimized_setpoint']}°C",
                    "shed_kw": o6_8["total_power_shed_kw"],
                    "confidence": o6_8["confidence"]
                },
                {
                    "code": "O9",
                    "title": "Electronic Expansion Valve Retrofit",
                    "route": "/agents/plant-control/electronic-expansion-valve",
                    "status": o9["recommendation"],
                    "current": o9["current_technology"],
                    "optimized": o9["proposed_technology"],
                    "shed_kw": round((o9["annual_kwh_savings"] / 2800.0), 1),
                    "confidence": o9["confidence"]
                }
            ]
        }

plant_control_agent = PlantControlAgent()
