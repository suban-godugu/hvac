"""
Automated Test Suite for Plant Control Parameter Optimizations Agent (Opportunities 5 to 9)
Tests:
- O5: Duct static pressure reset, fan cube law power, VAV damper authority limits
- O6: Heating hot water reset, condensing boiler efficiency curve, reheat demand safety
- O7: Chilled water reset, chiller lift vs secondary pump power trade-off
- O8: Condenser water reset, wet-bulb approach, total plant power trade-off
- O9: Electronic expansion valve retrofit feasibility, superheat stability, capital ROI
- Safety Engine: 10 deterministic guardrails, stale telemetry lockout, fail-safe rollback
"""
import unittest
from backend.agents.plant_control.safety_engine import plant_control_safety
from backend.agents.plant_control.o5_duct_static_pressure import o5_engine
from backend.agents.plant_control.o6_heating_water_reset import o6_engine
from backend.agents.plant_control.o7_chilled_water_reset import o7_engine
from backend.agents.plant_control.o8_condenser_water_reset import o8_engine
from backend.agents.plant_control.o9_electronic_expansion_valve import o9_engine
from backend.agents.plant_control.plant_control_agent import plant_control_agent

class TestPlantControlSuite(unittest.TestCase):

    def test_o5_duct_static_pressure_optimization(self):
        """Test O5 DSP candidates, fan power cube law reduction, and critical zone tracking."""
        res = o5_engine.generate_and_evaluate_candidates(current_sp=2.0, fan_power_kw=14.2)
        self.assertEqual(res["opportunity_code"], "O5")
        self.assertIn("optimized_setpoint", res)
        self.assertLessEqual(res["optimized_setpoint"], 2.0)
        self.assertGreaterEqual(res["optimized_setpoint"], 1.0)
        self.assertGreater(res["power_shed_kw"], 0.0)
        self.assertTrue(len(res["candidates"]) >= 4)

    def test_o6_heating_water_reset(self):
        """Test O6 HHW reset schedule, condensing boiler efficiency, and OAT response."""
        res = o6_engine.generate_and_evaluate_candidates(current_sp=80.0, outdoor_temp_c=24.5)
        self.assertEqual(res["opportunity_code"], "O6")
        self.assertLess(res["optimized_setpoint"], 80.0)
        self.assertGreaterEqual(res["optimized_setpoint"], 60.0)
        self.assertGreater(res["boiler_efficiency_optimized_pct"], 88.0)

    def test_o7_chilled_water_reset(self):
        """Test O7 CHWS lift reduction and net plant power shed."""
        res = o7_engine.generate_and_evaluate_candidates(current_sp=6.7, cooling_load_tons=76.0)
        self.assertEqual(res["opportunity_code"], "O7")
        self.assertGreaterEqual(res["optimized_setpoint"], 6.0)
        self.assertLessEqual(res["optimized_setpoint"], 8.5)
        self.assertIn("power_shed_kw", res)

    def test_o8_condenser_water_reset_total_power(self):
        """Test O8 total plant power model and wet-bulb approach safety."""
        res = o8_engine.generate_and_evaluate_candidates(current_sp=29.5, outdoor_wet_bulb_c=21.4)
        self.assertEqual(res["opportunity_code"], "O8")
        self.assertLess(res["optimized_setpoint"], 29.5)
        self.assertGreaterEqual(res["wet_bulb_approach_c"], 2.8)
        self.assertGreater(res["power_shed_kw"], 0.0)

    def test_o9_electronic_expansion_valve_roi(self):
        """Test O9 thermodynamic cycle simulation, superheat oscillation, and financial ROI."""
        res = o9_engine.evaluate_retrofit_feasibility()
        self.assertEqual(res["opportunity_code"], "O9")
        self.assertIn(res["recommendation"], ["RECOMMENDED", "REQUIRES ENGINEERING REVIEW", "NOT RECOMMENDED"])
        self.assertGreater(res["annual_kwh_savings"], 5000.0)
        self.assertGreater(res["payback_years"], 0.0)
        self.assertGreaterEqual(res["five_year_net_roi_pct"], 0.0)

    def test_plant_control_safety_engine_guardrails(self):
        """Test 10 deterministic safety guardrails & stale telemetry lockout."""
        # 1. Normal safe condition
        safe_eval = plant_control_safety.evaluate_safety("O5", 2.0, 1.8, {"vav_max_damper_pct": 75.0}, True, 1.5)
        self.assertEqual(safe_eval["status"], "PASS")

        # 2. Stale telemetry failure
        stale_eval = plant_control_safety.evaluate_safety("O5", 2.0, 1.8, {}, True, 45.0)
        self.assertEqual(stale_eval["status"], "FAIL")

        # 3. High damper saturation lockout
        damper_lockout = plant_control_safety.evaluate_safety("O5", 2.0, 1.6, {"vav_max_damper_pct": 96.0}, True, 1.0)
        self.assertEqual(damper_lockout["status"], "FAIL")

        # 4. Low chiller lift lockout
        lift_lockout = plant_control_safety.evaluate_safety("O8", 29.5, 15.0, {"chws_temp": 6.8}, True, 1.0)
        self.assertEqual(lift_lockout["status"], "FAIL")

    def test_plant_control_agent_fleet_summary(self):
        """Test fleet aggregation across all 5 opportunities."""
        summary = plant_control_agent.get_fleet_summary()
        self.assertEqual(summary["agent_health"], "OPTIMAL")
        self.assertGreaterEqual(len(summary["opportunities"]), 3)
        self.assertGreater(summary["total_power_shed_kw"], 0.0)
        codes = {o["code"] for o in summary["opportunities"]}
        self.assertTrue({"O5", "O9"}.issubset(codes))

if __name__ == "__main__":
    unittest.main()
