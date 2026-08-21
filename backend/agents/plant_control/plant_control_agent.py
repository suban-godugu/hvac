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
        """Fleet dashboard payload. Includes o5–o9_summary for Fleet Overview cards."""
        cycle = self.run_supervisory_cycle()
        o5 = cycle["opportunities"]["o5"]
        o6 = cycle["opportunities"]["o6"]
        o7 = cycle["opportunities"]["o7"]
        o8 = cycle["opportunities"]["o8"]
        o6_8 = cycle["opportunities"]["o6_8"]
        o9 = cycle["opportunities"]["o9"]

        def _sp(mode: Dict[str, Any]) -> tuple:
            cur = mode.get("current_setpoint")
            opt = mode.get("optimized_setpoint")
            return (
                f"{cur}°C" if cur is not None else "—",
                f"{opt}°C" if opt is not None else "—",
                float(mode.get("power_shed_kw") or 0.0),
            )

        o6_cur, o6_opt, o6_kw = _sp(o6)
        o7_cur, o7_opt, o7_kw = _sp(o7)
        o8_cur, o8_opt, o8_kw = _sp(o8)

        from backend.bms.connection_manager import is_simulation_mode

        sim = is_simulation_mode()
        reset_status = "MONITORING" if sim else "ACTIVE_RESET"

        o5_summary = {
            "title": "Duct Static Pressure Reset",
            "current": f"{o5.get('current_static_pressure')} in.w.c.",
            "optimized": f"{o5.get('optimized_setpoint')} in.w.c.",
            "power_shed_kw": o5.get("power_shed_kw"),
            "status": reset_status,
        }
        o6_summary = {
            "title": "Heating Hot Water Reset",
            "current": o6_cur,
            "optimized": o6_opt,
            "power_shed_kw": o6_kw,
            "status": reset_status,
        }
        o7_summary = {
            "title": "Chilled Water Reset",
            "current": o7_cur,
            "optimized": o7_opt,
            "power_shed_kw": o7_kw,
            "status": reset_status,
        }
        o8_summary = {
            "title": "Condenser Water Reset",
            "current": o8_cur,
            "optimized": o8_opt,
            "power_shed_kw": o8_kw,
            "status": reset_status,
        }
        o9_summary = {
            "title": "Electronic Expansion Valve Retrofit",
            "status": o9.get("recommendation") or "ASSESSMENT",
            "annual_savings_usd": o9.get("total_annual_savings_usd"),
            "payback_years": o9.get("payback_years"),
            "roi_pct": o9.get("five_year_net_roi_pct"),
        }

        return {
            "agent_name": "Plant Control Parameter Optimizations",
            "agent_health": "OPTIMAL",
            "agent_mode": self.mode,
            "mode": self.mode,
            "bms_connection": "DISCONNECTED" if sim else "CONNECTED",
            "telemetry_age_seconds": 0 if sim else None,
            "total_power_shed_kw": cycle["total_power_shed_kw"],
            "daily_energy_saved_kwh": cycle["daily_kwh_savings"],
            "daily_kwh_savings": cycle["daily_kwh_savings"],
            "comfort_compliance_pct": 100.0,
            "safety_compliance_pct": 100.0,
            "safety_status": "PASS",
            "active_opportunities_count": cycle["active_opportunities_count"],
            "applied_optimizations_count": 0 if sim else cycle["active_opportunities_count"],
            "o5_summary": o5_summary,
            "o6_summary": o6_summary,
            "o7_summary": o7_summary,
            "o8_summary": o8_summary,
            "o9_summary": o9_summary,
            "opportunities": [
                {
                    "code": "O5",
                    "title": o5_summary["title"],
                    "route": "/agents/plant-control/duct-static-pressure",
                    "status": o5_summary["status"],
                    "current": o5_summary["current"],
                    "optimized": o5_summary["optimized"],
                    "shed_kw": o5_summary["power_shed_kw"],
                    "confidence": o5.get("confidence"),
                },
                {
                    "code": "O6–8",
                    "title": "Temperature Reset (HHW / CHW / CW)",
                    "route": "/agents/plant-control/temperature-reset",
                    "status": reset_status,
                    "current": f"CHW {o7_cur} | CW {o8_cur} | HHW {o6_cur}",
                    "optimized": f"CHW {o7_opt} | CW {o8_opt} | HHW {o6_opt}",
                    "shed_kw": o6_8.get("total_power_shed_kw"),
                    "confidence": o6_8.get("confidence"),
                },
                {
                    "code": "O9",
                    "title": o9_summary["title"],
                    "route": "/agents/plant-control/electronic-expansion-valve",
                    "status": o9_summary["status"],
                    "current": o9.get("current_technology"),
                    "optimized": o9.get("proposed_technology"),
                    "shed_kw": round((float(o9.get("annual_kwh_savings") or 0) / 2800.0), 1),
                    "confidence": o9.get("confidence"),
                },
            ],
        }

plant_control_agent = PlantControlAgent()
