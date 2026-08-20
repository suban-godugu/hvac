"""
Unit and Integration Test Suite for Variable Speed Based Optimisations.
"""
import unittest
from datetime import datetime, timezone

from backend.agents.variable_speed.fan_speed_agent import fan_speed_agent
from backend.agents.variable_speed.pump_speed_agent import pump_speed_agent
from backend.agents.variable_speed.chw_pump_agent import chw_pump_agent
from backend.agents.variable_speed.condenser_water_pump_agent import condenser_water_pump_agent
from backend.agents.variable_speed.cooling_tower_fan_agent import cooling_tower_fan_agent
from backend.agents.variable_speed.variable_speed_agent import variable_speed_agent
from backend.agents.variable_speed.safety_engine import vs_safety_engine
from backend.data_pipeline.variable_speed_simulator import vs_simulator
from backend.services.variable_speed_telemetry_service import vs_telemetry_service
from backend.services.variable_speed_bms_service import vs_bms_service
from backend.services.variable_speed_command_service import vs_command_service
from backend.services.variable_speed_verification_service import vs_verification_service
from backend.services.variable_speed_service import vs_service

class TestVariableSpeedIntegration(unittest.TestCase):

    # 1. Fleet Supervisory Cycle Test
    def test_01_fleet_supervisory_cycle(self):
        """Test fleet-wide supervisory cycle across all 5 VFD equipment types."""
        cycle = variable_speed_agent.run_supervisory_cycle()
        self.assertEqual(cycle["module_code"], "VARIABLE_SPEED_BASED_OPTIMISATIONS")
        self.assertEqual(cycle["mode"], "AUTO_CLOSED_LOOP")
        self.assertEqual(cycle["agent_health"], "OPTIMAL")
        self.assertGreater(cycle["estimated_power_savings_kw"], 0.0)
        self.assertGreater(cycle["total_daily_kwh_savings"], 0.0)
        self.assertEqual(len(cycle["opportunities"]), 5)

    # 2. Fan Speed Optimization Test
    def test_02_fan_speed_optimization(self):
        """Test AHU fan speed modulation and power reduction."""
        res = fan_speed_agent.optimize()
        self.assertEqual(res["opportunity_code"], "VS_FAN")
        self.assertLess(res["optimized_speed"], res["current_speed"])
        self.assertGreater(res["expected_savings_kw"], 0.0)
        self.assertEqual(res["safety_status"], "PASS")

        with self.assertRaises(ValueError):
            vs_command_service.execute_command("AHU-FAN-01", res["optimized_speed"])

    # 3. Pump Speed Optimization Test
    def test_03_pump_speed_optimization(self):
        """Test secondary distribution pump speed optimization."""
        res = pump_speed_agent.optimize()
        self.assertEqual(res["opportunity_code"], "VS_PUMP")
        self.assertLess(res["optimized_speed"], res["current_speed"])
        self.assertGreater(res["expected_savings_kw"], 0.0)
        self.assertEqual(res["safety_status"], "PASS")

    # 4. Chilled Water (CHW) Pump Optimization Test
    def test_04_chw_pump_optimization(self):
        """Test CHW pump optimization maintaining coil delta-T."""
        res = chw_pump_agent.optimize()
        self.assertEqual(res["opportunity_code"], "VS_CHW")
        self.assertLess(res["optimized_speed"], res["current_speed"])
        self.assertGreater(res["expected_savings_kw"], 0.0)
        self.assertEqual(res["safety_status"], "PASS")

    # 5. Condenser Water (CW) Pump Optimization Test
    def test_05_condenser_pump_optimization(self):
        """Test CW pump optimization based on heat rejection load."""
        res = condenser_water_pump_agent.optimize()
        self.assertEqual(res["opportunity_code"], "VS_CW")
        self.assertLess(res["optimized_speed"], res["current_speed"])
        self.assertGreater(res["expected_savings_kw"], 0.0)
        self.assertEqual(res["safety_status"], "PASS")

    # 6. Cooling Tower Fan Optimization Test
    def test_06_cooling_tower_fan_optimization(self):
        """Test Cooling Tower fan speed optimization balancing tower and chiller kW."""
        res = cooling_tower_fan_agent.optimize()
        self.assertEqual(res["opportunity_code"], "VS_CT")
        self.assertLess(res["optimized_speed"], res["current_speed"])
        self.assertGreater(res["expected_savings_kw"], 0.0)
        self.assertEqual(res["safety_status"], "PASS")

    # 7. Safety Constraints & Lockouts Test
    def test_07_safety_constraints_lockouts(self):
        """Test deterministic safety guardrail enforcements."""
        # 1. Below minimum speed limit (<30%)
        res_min = vs_safety_engine.evaluate_safety("AHU_FAN", 72.0, 20.0)
        self.assertFalse(res_min.is_safe)
        self.assertIn("minimum motor cooling limit", res_min.violations[0])

        # 2. Critical zone near saturation lockout (>88%)
        res_crit = vs_safety_engine.evaluate_safety("AHU_FAN", 72.0, 60.0, {"max_vav_damper_pct": 92.0})
        self.assertFalse(res_crit.is_safe)
        self.assertIn("Critical zone damper is near saturation", res_crit.violations[0])

        # 3. Bad telemetry quality lockout
        res_bad = vs_safety_engine.evaluate_safety("CHW_PUMP", 70.0, 60.0, {"quality": "BAD"})
        self.assertFalse(res_bad.is_safe)
        self.assertIn("quality is BAD", res_bad.violations[0])

    # 8. M&V Verification and Rollback Test
    def test_08_verification_and_rollback(self):
        """Test 15-minute M&V verification and fail-safe rollback execution."""
        verif = vs_verification_service.verify_equipment("AHU-FAN-01")
        self.assertEqual(verif["outcome"], "VERIFIED_KEPT")
        self.assertGreater(verif["power_savings_kw"], 0.0)

        with self.assertRaises(ValueError):
            vs_verification_service.rollback_equipment("AHU-FAN-01", "Test Rollback")

    # 9. Simulator Scenarios Test
    def test_09_simulator_scenarios(self):
        """Test physics simulator across different load scenarios."""
        vs_simulator.set_scenario("HIGH_LOAD")
        tel_high = vs_simulator.generate_telemetry()
        self.assertEqual(tel_high["status"], "ONLINE")
        self.assertGreater(tel_high["fan"]["speed_pct"], 75.0)

        vs_simulator.set_scenario("BMS_DISCONNECTED")
        tel_disc = vs_simulator.generate_telemetry()
        self.assertEqual(tel_disc["status"], "BMS_DISCONNECTED")

        # Reset to NORMAL
        vs_simulator.set_scenario("NORMAL")

if __name__ == "__main__":
    unittest.main()
