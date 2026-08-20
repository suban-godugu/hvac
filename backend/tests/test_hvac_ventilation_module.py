"""Ventilation module O10–O13 public API."""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from backend.agents.ventilation_airflow.o10_o13_engines import evaluate_o11, evaluate_o12, evaluate_o13
from backend.services.hvac_ventilation_module import canonical_oid, get_opportunities, get_opportunity, dispatch_gate, _as_module_opportunity
from backend.services.ventilation_opportunity_service import ensure_demo_telemetry, evaluate_opportunity
from database.session import init_db, SessionLocal


class TestCanonicalIds(unittest.TestCase):
    def test_aliases(self):
        self.assertEqual(canonical_oid("011"), "O11")
        self.assertEqual(canonical_oid("o12"), "O12")
        self.assertEqual(canonical_oid("013"), "O13")
        self.assertEqual(canonical_oid("O10"), "O10")
        self.assertEqual(canonical_oid("010"), "O10")


class TestAgents(unittest.TestCase):
    def test_o11_missing(self):
        out = evaluate_o11({})
        self.assertFalse(out["available"])

    def test_o11_daytime_standby(self):
        out = evaluate_o11(
            {"outdoor_temp_c": 18, "return_temp_c": 24, "supply_airflow_cfm": 7800, "occupied": True, "occupancy": 40},
            hour=14,
        )
        self.assertTrue(out["available"])
        self.assertEqual(out["eligibility"], "PURGE NOT ELIGIBLE")
        self.assertEqual(out["supervisory_decision"], "HOLD")

    def test_o11_eligible_night(self):
        out = evaluate_o11(
            {
                "outdoor_temp_c": 16,
                "return_temp_c": 24,
                "supply_airflow_cfm": 4000,
                "occupied": False,
                "occupancy": 0,
                "fan_power_kw": 5,
            },
            hour=22,
        )
        self.assertEqual(out["eligibility"], "PURGE ELIGIBLE")
        self.assertEqual(out["supervisory_decision"], "OPTIMIZE")
        self.assertGreater(out["optimized_airflow_cfm"], out["current_airflow_cfm"])

    def test_o12_never_below_min(self):
        out = evaluate_o12({"co2_ppm": 500, "supply_airflow_cfm": 7800, "occupancy": 10, "building_area_sqft": 75000})
        self.assertTrue(out["available"])
        self.assertGreaterEqual(out["optimized_airflow_cfm"], out["required_ventilation_cfm"])

    def test_o12_missing(self):
        self.assertFalse(evaluate_o12({})["available"])

    def test_o12_occupancy_raises_floor(self):
        low = evaluate_o12({"co2_ppm": 650, "supply_airflow_cfm": 7800, "occupancy": 8, "building_area_sqft": 75000})
        high = evaluate_o12({"co2_ppm": 650, "supply_airflow_cfm": 7800, "occupancy": 200, "building_area_sqft": 75000})
        self.assertGreaterEqual(high["required_ventilation_cfm"], low["required_ventilation_cfm"])
        self.assertGreaterEqual(high["optimized_airflow_cfm"], high["required_ventilation_cfm"])

    def test_o12_high_co2_does_not_trim(self):
        out = evaluate_o12({"co2_ppm": 1400, "supply_airflow_cfm": 4000, "occupancy": 80, "building_area_sqft": 75000})
        self.assertGreaterEqual(out["optimized_airflow_cfm"], out["current_airflow_cfm"])
        self.assertEqual(out["iaq_compliance"], "FAIL")
        self.assertEqual(out["supervisory_decision"], "INCREASE_VENTILATION")
        self.assertNotEqual(out["supervisory_decision"], "OPTIMIZE")

    def test_o11_missing_oat(self):
        out = evaluate_o11({"return_temp_c": 24, "supply_airflow_cfm": 4000, "occupancy": 0}, hour=22)
        self.assertFalse(out["available"])

    def test_o11_missing_occupancy_holds(self):
        out = evaluate_o11(
            {"outdoor_temp_c": 16, "return_temp_c": 24, "supply_airflow_cfm": 4000},
            hour=22,
        )
        self.assertEqual(out["eligibility"], "PURGE NOT ELIGIBLE")
        self.assertEqual(out["supervisory_decision"], "HOLD")

    def test_o11_high_humidity_holds(self):
        out = evaluate_o11(
            {
                "outdoor_temp_c": 16,
                "return_temp_c": 24,
                "supply_airflow_cfm": 4000,
                "occupied": False,
                "occupancy": 0,
                "outdoor_rh_percent": 92,
            },
            hour=22,
        )
        self.assertEqual(out["eligibility"], "PURGE NOT ELIGIBLE")
        self.assertEqual(out["supervisory_decision"], "HOLD")

    def test_o11_outside_window(self):
        out = evaluate_o11(
            {"outdoor_temp_c": 16, "return_temp_c": 24, "supply_airflow_cfm": 4000, "occupied": False, "occupancy": 0},
            hour=14,
        )
        self.assertEqual(out["eligibility"], "PURGE NOT ELIGIBLE")
        self.assertEqual(out["supervisory_decision"], "HOLD")

    def test_o13_very_high_co(self):
        out = evaluate_o13({"co_ppm": 180, "supply_airflow_cfm": 7350, "damper_percent": 40})
        self.assertEqual(out["supervisory_decision"], "BLOCK")
        self.assertGreater(out["optimized_airflow_cfm"], out["current_airflow_cfm"])

    def test_o13_low_co_damper_bounds(self):
        low = evaluate_o13({"co_ppm": 8, "supply_airflow_cfm": 7350, "damper_percent": 5})
        if low.get("optimized_damper_pct") is not None:
            self.assertGreaterEqual(low["optimized_damper_pct"], 15)
        high = evaluate_o13({"co_ppm": 62, "supply_airflow_cfm": 7350, "damper_percent": 120})
        self.assertLessEqual(high["optimized_damper_pct"], 100)
        self.assertGreaterEqual(high["optimized_damper_pct"], 15)

    def test_o13_high_co_blocks_trim(self):
        out = evaluate_o13({"co_ppm": 62, "supply_airflow_cfm": 7350})
        self.assertEqual(out["safety_status"], "FAIL")
        self.assertEqual(out["supervisory_decision"], "BLOCK")
        self.assertGreaterEqual(out["optimized_airflow_cfm"], out["current_airflow_cfm"])

    def test_o13_normal_may_trim(self):
        out = evaluate_o13({"co_ppm": 12.5, "supply_airflow_cfm": 7350, "return_airflow_cfm": 7350, "fan_power_kw": 8})
        self.assertEqual(out["iaq_compliance"], "PASS")
        self.assertIn(out["supervisory_decision"], ("OPTIMIZE", "HOLD"))

    def test_o13_missing(self):
        self.assertFalse(evaluate_o13({})["available"])

    def test_o13_warn_increases(self):
        out = evaluate_o13({"co_ppm": 28, "supply_airflow_cfm": 7350})
        self.assertEqual(out["supervisory_decision"], "INCREASE_VENTILATION")
        self.assertGreater(out["optimized_airflow_cfm"], out["current_airflow_cfm"])


class TestModuleApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        db = SessionLocal()
        try:
            ensure_demo_telemetry(db, force=True)
        finally:
            db.close()

    def test_dashboard_includes_o10(self):
        dash = get_opportunities()
        ids = [o["id"] for o in dash["opportunities"]]
        self.assertEqual(ids, ["O10", "O11", "O12", "O13"])
        self.assertEqual(dash["module"]["ids"], ["O10", "O11", "O12", "O13"])
        blob = str(dash)
        self.assertIn("Economy Cycle", blob)

    def test_detail_shape(self):
        for oid in ("O10", "O11", "O12", "O13"):
            r = get_opportunity(oid)
            self.assertEqual(r["id"], oid)
            self.assertIn("telemetry", r)
            self.assertIn("current", r)
            self.assertIn("optimized", r)
            self.assertIn("energy", r)
            self.assertIn("recommendation", r)
            self.assertIn("supervisory", r)
            self.assertIn("safety", r)
            self.assertIn("failSafe", r)
            self.assertIn("dispatch", r)

    def test_o10_setpoint_is_damper(self):
        r = get_opportunity("O10")
        damper = r["current"]["damperPct"]
        if damper is not None:
            self.assertLessEqual(damper, 100)
            self.assertGreaterEqual(damper, 0)
            self.assertEqual(r["recommendation"]["current"], damper)

    def test_stale_state_mapping(self):
        r = get_opportunity("O11")
        self.assertEqual(r["telemetryStatus"], "SIMULATED")
        self.assertFalse(r["dispatch"]["eligible"])

    def test_demo_bms_offline(self):
        dash = get_opportunities()
        self.assertEqual(dash["module"]["bms"]["status"], "OFFLINE")
        self.assertEqual(dash["module"]["telemetry"]["state"], "SIMULATED")
        self.assertEqual(len(dash["opportunities"]), 4)
        self.assertEqual(dash["module"]["kpis"]["liveCount"], 0)

    def test_stale_safe_hold(self):
        raw = evaluate_opportunity("O11")
        raw["telemetry"]["state"] = "STALE"
        raw["telemetry"]["source"] = "BMS"
        out = _as_module_opportunity(raw)
        self.assertEqual(out["supervisory"]["decision"], "SAFE_HOLD")
        self.assertFalse(out["dispatch"]["eligible"])

    def test_missing_wait_for_telemetry(self):
        out = _as_module_opportunity(
            {
                "opportunityId": "O12",
                "status": "UNAVAILABLE",
                "telemetry": {"state": "UNAVAILABLE", "source": "BMS"},
            }
        )
        self.assertEqual(out["supervisory"]["decision"], "WAIT_FOR_TELEMETRY")
        self.assertFalse(out["dispatch"]["eligible"])

    def test_dispatch_gate_live_optimize(self):
        ok, reason, _classified = dispatch_gate(
            {
                "telemetry": {"raw": "LIVE", "source": "BMS", "quality": "GOOD", "ageSeconds": 2},
                "source": "BMS",
                "supervisory": {"decision": "OPTIMIZE"},
                "safety": {"status": "PASS", "passed": True},
                "confidence": 0.9,
                "current": {"airflowCfm": 2400},
                "optimized": {"airflowCfm": 1550},
            }
        )
        self.assertFalse(ok)
        self.assertIn("BMS", reason)

    def test_dispatch_gate_high_co2_blocked(self):
        ok, reason, _classified = dispatch_gate(
            {
                "telemetry": {"raw": "LIVE", "source": "BMS"},
                "source": "BMS",
                "supervisory": {"decision": "INCREASE_VENTILATION"},
                "safety": {"status": "FAIL", "passed": False},
                "current": {"airflowCfm": 4000},
                "optimized": {"airflowCfm": 4000},
            }
        )
        self.assertFalse(ok)


    def test_o10_command_mapping(self):
        from backend.services.ventilation_command_service import ventilation_command_service

        mapping = ventilation_command_service.POINT_MAPPINGS["O10"]
        self.assertEqual(mapping["target_point"], "AHU-01.OutdoorAirDamperPositionSetpoint")
        self.assertEqual(mapping["default_unit"], "%")


if __name__ == "__main__":
    unittest.main()
