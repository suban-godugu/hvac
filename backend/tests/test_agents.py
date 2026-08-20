import unittest
import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.scheduling_supervisory.o1_optimum_start_stop.predictor import ThermalResponsePredictor
from agents.scheduling_supervisory.o1_optimum_start_stop.optimizer import OptimumStartStopOptimizer
from agents.scheduling_supervisory.o1_optimum_start_stop.verifier import OptimumStartStopVerifier
from agents.scheduling_supervisory.o2_space_temperature.optimizer import SpaceTempOptimizer
from agents.scheduling_supervisory.o3_master_ahu_sat.optimizer import SATOptimizer
from agents.scheduling_supervisory.o4_chiller_staging.optimizer import ChillerStagingOptimizer
from agents.scheduling_supervisory.safety.guardrails import SafetyGuardrails
from agents.scheduling_supervisory.state import ZoneState, AHUState, ChillerState, ChillerPlantState

class TestHVACSupervisoryAgents(unittest.TestCase):

    def setUp(self):
        self.predictor = ThermalResponsePredictor()
        self.o1_opt = OptimumStartStopOptimizer()
        self.o1_ver = OptimumStartStopVerifier()
        self.o2_opt = SpaceTempOptimizer()
        self.o3_opt = SATOptimizer()
        self.o4_opt = ChillerStagingOptimizer()
        self.guardrails = SafetyGuardrails()

    def test_o1_start_stop_prediction(self):
        # When zone is 25°C and target is 22.5°C with mild OAT 22°C
        precool_min = self.predictor.predict_precool_minutes(25.0, 22.5, 22.0, 300.0)
        self.assertGreater(precool_min, 20.0)
        self.assertLess(precool_min, 60.0)

        # Full O1 optimizer output check
        result = self.o1_opt.optimize("06:00", 24.5, 22.5, 24.0, 400.0, "08:00", "18:00")
        self.assertIn("optimal_start_time", result)
        self.assertIn("start_delay_minutes", result)
        self.assertGreater(result["start_delay_minutes"], 0)

        # Verifier check
        ver = self.o1_ver.verify(result)
        self.assertTrue(ver["is_valid"])

    def test_o2_space_temp_deadband(self):
        zones = [
            ZoneState(id="Z1", name="Zone 1", temp_actual=23.0, cooling_sp=23.0, heating_sp=21.0, occupied=True),
            ZoneState(id="Z2", name="Zone 2", temp_actual=24.0, cooling_sp=23.0, heating_sp=21.0, occupied=False) # Unoccupied
        ]
        result = self.o2_opt.optimize_setpoints(zones)
        self.assertEqual(result["unoccupied_count"], 1)
        self.assertGreater(result["total_shed_kw_est"], 0.0)

    def test_o3_ahu_sat_trim_and_respond(self):
        # 0 critical requests -> Trim warmer
        zones = [
            ZoneState(id="Z1", name="Zone 1", temp_actual=22.5, cooling_sp=22.5, damper_pos=40.0),
            ZoneState(id="Z2", name="Zone 2", temp_actual=22.4, cooling_sp=22.5, damper_pos=45.0)
        ]
        ahu = AHUState(id="AHU-1", name="Floor 1 AHU", sat_actual=13.0, sat_setpoint=13.0, vav_zones=zones)
        result = self.o3_opt.optimize_sat(ahu)
        self.assertEqual(result["action"], "TRIM_WARMER")
        self.assertGreater(result["target_sat_sp"], 13.0)

    def test_o4_chiller_staging(self):
        ch1 = ChillerState(id="CH-1", name="Chiller 1", status=True, capacity_tons=120.0, current_tons=70.0)
        ch2 = ChillerState(id="CH-2", name="Chiller 2", status=False, capacity_tons=120.0, current_tons=0.0)
        plant = ChillerPlantState(chillers=[ch1, ch2], total_tons=70.0, chws_temp=6.8, chwr_temp=12.2, flow_rate_lps=11.0)
        result = self.o4_opt.optimize_staging(plant, oat=24.0)
        self.assertEqual(result["recommended_active_count"], 1)
        self.assertGreaterEqual(result["target_chws_sp"], 6.7)

    def test_safety_guardrails_clamp(self):
        # Test extreme out-of-bounds SAT
        unsafe_decisions = {
            "o3_sat": {"target_sat_sp": 9.0}, # Too cold, below 11.5°C
            "o4_chiller": {"target_chws_sp": 4.0} # Too cold, below 5.0°C
        }
        report = self.guardrails.validate_and_clamp_all(unsafe_decisions)
        self.assertEqual(unsafe_decisions["o3_sat"]["target_sat_sp"], 11.5)
        self.assertEqual(unsafe_decisions["o4_chiller"]["target_chws_sp"], 5.0)
        self.assertGreater(len(report["clamped_setpoints"]), 0)

if __name__ == "__main__":
    unittest.main()
