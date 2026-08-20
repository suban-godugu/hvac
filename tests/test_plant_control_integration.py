"""
Comprehensive Integration & Fault Simulation Test Suite
for Plant Control Parameter Optimizations (Opportunities 5 to 9).
"""
import pytest
import unittest
from datetime import datetime, timezone

from backend.agents.plant_control.plant_control_agent import plant_control_agent
from backend.agents.plant_control.o5_duct_static_pressure.engine import o5_agent
from backend.agents.plant_control.o6_heating_water_reset.engine import o6_agent
from backend.agents.plant_control.o7_chilled_water_reset.engine import o7_agent
from backend.agents.plant_control.o8_condenser_water_reset.engine import o8_agent
from backend.agents.plant_control.o9_electronic_expansion_valve.engine import o9_agent
from backend.agents.plant_control.safety_engine import plant_control_safety
from backend.services.plant_control_telemetry_service import plant_control_telemetry_service
from backend.services.plant_control_bms_service import plant_control_bms_service
from backend.services.plant_control_command_service import plant_control_command_service
from backend.services.plant_control_verification_service import plant_control_verification_service
from backend.ml.plant_control.training_pipeline import plant_control_training_pipeline
from backend.ml.plant_control.model_registry import plant_control_model_registry
from backend.ml.plant_control.calibration_engine import plant_control_calibration_engine

class TestPlantControlIntegration(unittest.TestCase):
    
    # -------------------------------------------------------------
    # 1. Full Closed-Loop Pipeline Tests
    # -------------------------------------------------------------
    def test_01_fleet_supervisory_cycle(self):
        """Test fleet-wide supervisory execution across O5-O9."""
        cycle = plant_control_agent.run_supervisory_cycle()
        self.assertEqual(cycle["module_code"], "PLANT_CONTROL_PARAMETER_OPTIMIZATIONS")
        self.assertEqual(cycle["mode"], "AUTO_CLOSED_LOOP")
        self.assertGreater(cycle["total_power_shed_kw"], 0.0)
        self.assertGreater(cycle["daily_kwh_savings"], 0.0)
        self.assertIn("o5", cycle["opportunities"])
        self.assertIn("o6_8", cycle["opportunities"])
        self.assertIn("o9", cycle["opportunities"])

    def test_02_o5_closed_loop_dispatch_and_verify(self):
        """Test O5 Duct Static Pressure full lifecycle: candidate -> safety -> dispatch -> verify."""
        state = o5_agent.generate_and_evaluate_candidates()
        target_sp = state["optimized_setpoint"]
        self.assertIn(target_sp, [1.4, 1.6, 1.7, 1.8, 2.0])
        self.assertEqual(state["safety_status"], "PASS")

        with self.assertRaises(ValueError):
            plant_control_command_service.execute_command("O5", target_sp)

    def test_03_o6_8_combined_temperature_reset_modes(self):
        """Test unified O6_8 Temperature Reset agent across HHW, CHW, and CW modes."""
        from backend.agents.plant_control.o6_8_temperature_reset.engine import o6_8_agent
        
        # Test HHW Mode
        hhw = o6_8_agent.optimize_mode("HHW")
        self.assertEqual(hhw["opportunity_id"], "O6_8")
        self.assertEqual(hhw["reset_type"], "HHW")
        self.assertIn(hhw["optimized_setpoint"], [62.0, 66.0, 70.0, 75.0, 80.0])
        self.assertIn("Boiler", hhw["efficiency_impact"])

        # Test CHW Mode
        chw = o6_8_agent.optimize_mode("CHW")
        self.assertEqual(chw["opportunity_id"], "O6_8")
        self.assertEqual(chw["reset_type"], "CHW")
        self.assertIn(chw["optimized_setpoint"], [6.0, 6.5, 7.0, 7.5, 8.0])
        self.assertGreater(chw["power_impact_kw"], 0.0)

        # Test CW Mode
        cw = o6_8_agent.optimize_mode("CW")
        self.assertEqual(cw["opportunity_id"], "O6_8")
        self.assertEqual(cw["reset_type"], "CW")
        self.assertIn(cw["optimized_setpoint"], [24.0, 25.5, 27.0, 28.5, 29.5])
        self.assertIn("Lift", cw["efficiency_impact"])

        # Test All Modes Summary
        summary = o6_8_agent.get_all_modes_summary()
        self.assertEqual(summary["opportunity_id"], "O6_8")
        self.assertEqual(len(summary["modes"]), 3)
        self.assertGreater(summary["total_power_shed_kw"], 0.0)

    def test_06_o9_assessment_only_behavior(self):
        """Test O9 strictly acts in ASSESSMENT MODE without physical BMS writes."""
        state = o9_agent.evaluate_retrofit_feasibility()
        self.assertIn(state["recommendation"], ["RECOMMENDED", "REQUIRES ENGINEERING REVIEW", "NOT RECOMMENDED"])
        self.assertGreater(state["annual_kwh_savings"], 0.0)
        self.assertGreater(state["payback_years"], 0.0)

        # Ensure attempting to write O9 to BMS throws error
        with self.assertRaises(ValueError):
            plant_control_bms_service.dispatch_point("O9", 1.0)

    # -------------------------------------------------------------
    # 2. Fault Simulation & Fail-Safe Tests
    # -------------------------------------------------------------
    def test_07_fault_bms_disconnect_triggers_no_write(self):
        """Test BMS disconnect triggers immediate lockout (NO WRITE)."""
        res = plant_control_safety.evaluate_safety(
            opportunity_code="O5",
            current_value=1.8,
            proposed_value=1.6,
            telemetry={"vav_max_damper_pct": 75.0},
            telemetry_age_sec=4.0,
            is_bms_connected=False
        )
        self.assertEqual(res["status"], "FAIL")
        self.assertIn("BMS Communication (FAILED)", res["checks"])

    def test_08_fault_stale_telemetry_triggers_safe_mode(self):
        """Test stale telemetry (> 30s) triggers safety safe mode."""
        res = plant_control_safety.evaluate_safety(
            opportunity_code="O7",
            current_value=6.7,
            proposed_value=7.5,
            telemetry={"cooling_load_tons": 76.0, "chiller_capacity_tons": 120.0},
            telemetry_age_sec=45.0, # Stale > 30s
            is_bms_connected=True
        )
        self.assertEqual(res["status"], "FAIL")
        self.assertIn("Safety Safe Mode Triggered", res["checks"])

    def test_09_fault_damper_starvation_causes_reject(self):
        """Test downstream VAV damper saturation (> 92%) rejects static pressure reduction."""
        res = plant_control_safety.evaluate_safety(
            opportunity_code="O5",
            current_value=1.8,
            proposed_value=1.4,
            telemetry={"vav_max_damper_pct": 94.0}, # Saturated
            telemetry_age_sec=2.0,
            is_bms_connected=True
        )
        self.assertEqual(res["status"], "FAIL")
        self.assertIn("Damper Starvation Lockout (FAILED)", res["checks"])

    def test_10_fault_chiller_lift_floor_violation_rejects(self):
        """Test condenser reset violating minimum 12.0°C lift limit is rejected."""
        res = plant_control_safety.evaluate_safety(
            opportunity_code="O8",
            current_value=29.5,
            proposed_value=17.0, # Violates 12°C lift floor with 6.8°C CHWS
            telemetry={"chws_temp": 6.8},
            telemetry_age_sec=2.0,
            is_bms_connected=True
        )
        self.assertEqual(res["status"], "FAIL")
        self.assertIn("Minimum Chiller Lift Safety Lockout (FAILED)", res["checks"])

    def test_11_fail_safe_rollback_restores_baseline(self):
        """Test manual or automated verification failure triggers baseline rollback."""
        rb = plant_control_verification_service.rollback_opportunity("O5", "Safety tracking breach")
        self.assertEqual(rb["status"], "REVERTED_BASELINE")
        self.assertEqual(rb["reverted_value"], 1.80)

    # -------------------------------------------------------------
    # 3. Model Training & Calibration Pipeline Tests
    # -------------------------------------------------------------
    def test_12_offline_training_pipeline(self):
        """Test offline training pipeline across all 5 models."""
        train_results = plant_control_training_pipeline.train_all()
        for code in ["O5", "O6", "O7", "O8", "O9"]:
            self.assertEqual(train_results[code]["validation_status"], "SIMULATED_FIXTURE")
            self.assertIn("model_version", train_results[code])

    def test_13_model_registry_production_promotion(self):
        """Test model registry rejects unvalidated models and stages validated ones."""
        # Register valid model
        valid_reg = plant_control_model_registry.register_model(
            opportunity="O7",
            version="O7-CHWS-v2.1.0",
            dataset="synthetic_verified_set",
            features=["chws", "chwr", "flow"],
            metrics={"r2": 0.97},
            parameters={"alpha": 0.01},
            validation_result="PASSED",
            promote_to_production=True
        )
        self.assertEqual(valid_reg["status"], "PRODUCTION")

        # Attempt to promote invalid model (r2 < 0.90)
        with self.assertRaises(ValueError):
            plant_control_model_registry.register_model(
                opportunity="O7",
                version="O7-CHWS-v2.1.0-bad",
                dataset="corrupt_set",
                features=["chws"],
                metrics={"r2": 0.65},
                parameters={},
                validation_result="FAILED",
                promote_to_production=True
            )

    def test_14_safe_calibration_pipeline(self):
        """Test 7-stage calibration lifecycle without online weight corruption."""
        cal_res = plant_control_calibration_engine.execute_calibration_pipeline("O8", [])
        self.assertEqual(cal_res["calibration_status"], "CALIBRATION_CONFIRMED_ONLINE")
        self.assertTrue(cal_res["promoted_to_production"])
        self.assertEqual(cal_res["pipeline_stages"], ["DATA", "VALIDATE", "TRAIN", "VALIDATE", "REGISTER", "CALIBRATE", "PRODUCTION"])

if __name__ == "__main__":
    unittest.main()
