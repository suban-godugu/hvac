import unittest
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from backend.agents.official_opportunities.o11_night_purge import evaluate_night_purge
from backend.agents.official_opportunities.o13_dcv_co import evaluate_dcv_co
from backend.agents.official_opportunities.o14_secondary_chw import evaluate_secondary_chw
from backend.agents.official_opportunities.o15_air_cooled_hp import evaluate_air_cooled_hp
from backend.agents.official_opportunities.o16_water_cooled_hp import evaluate_water_cooled_hp
from backend.agents.official_opportunities.o18_training import evaluate_training


class TestOfficialOpportunityAgents(unittest.TestCase):
    def test_o11_missing_telemetry_not_live(self):
        out = evaluate_night_purge({})
        self.assertFalse(out["live"])
        self.assertEqual(out["recommendation"], "BLOCKED")

    def test_o11_stale_style_missing_zone(self):
        out = evaluate_night_purge({"OAT": 18, "OA_DAMPER": 40, "FAN_STATE": 1, "OCCUPANCY": 0})
        self.assertFalse(out["live"])

    def test_o11_night_eligible(self):
        out = evaluate_night_purge(
            {
                "OAT": 18.0,
                "ZONE_TEMP": 25.8,
                "OA_DAMPER": 42,
                "FAN_STATE": 1,
                "FAN_SPEED": 1200,
                "OCCUPANCY": 1,
                "ECONOMIZER": 1,
                "AHU_AVAILABLE": 1,
                "AIRFLOW_CFM": 7800,
                "local_hour": 23,
            }
        )
        self.assertTrue(out["live"])
        self.assertEqual(out["recommendation"], "ENABLE")
        self.assertEqual(out["safety_status"], "PASS")
        self.assertIsNotNone(out["energy_impact"])

    def test_o11_occupied_blocked(self):
        out = evaluate_night_purge(
            {
                "OAT": 18.0,
                "ZONE_TEMP": 25.8,
                "OA_DAMPER": 42,
                "FAN_STATE": 1,
                "OCCUPANCY": 40,
                "ECONOMIZER": 1,
                "local_hour": 23,
            }
        )
        self.assertEqual(out["recommendation"], "BLOCKED")
        self.assertEqual(out["safety_status"], "BLOCKED")

    def test_o13_alarm_suppresses_energy(self):
        out = evaluate_dcv_co({"CO_PPM": 62, "FAN_STATE": 1, "FAN_SPEED": 30})
        self.assertEqual(out["recommendation"], "MAX_VENTILATION")
        self.assertEqual(out["energy_impact"], 0.0)

    def test_o13_missing_co(self):
        self.assertFalse(evaluate_dcv_co({})["live"])

    def test_o14_missing_not_live(self):
        self.assertFalse(evaluate_secondary_chw({})["live"])

    def test_o15_envelope(self):
        ok = evaluate_air_cooled_hp(
            {
                "HEAD_PRESSURE": 210,
                "COND_TEMP": 42,
                "OAT": 28,
                "FAN_SPEED": 55,
                "quality": "GOOD",
                "source": "LIVE_BMS",
                "age_seconds": 1,
            }
        )
        self.assertTrue(ok["live"])
        self.assertEqual(ok["recommendation"], "FLOAT_HEAD_PRESSURE")
        blocked = evaluate_air_cooled_hp(
            {"HEAD_PRESSURE": 320, "COND_TEMP": 50, "OAT": 38, "quality": "GOOD", "source": "LIVE_BMS"},
            {"max_head_pressure": 280},
        )
        self.assertEqual(blocked["recommendation"], "REJECT")

    def test_o16_requires_cewt(self):
        self.assertFalse(evaluate_water_cooled_hp({"CLWT": 32})["live"])
        out = evaluate_water_cooled_hp(
            {
                "CEWT": 29.4,
                "CLWT": 33.1,
                "LOAD": 65,
                "PUMP_STATE": 1,
                "quality": "GOOD",
                "source": "LIVE_BMS",
                "age_seconds": 1,
            }
        )
        self.assertTrue(out["live"])
        self.assertEqual(out["recommendation"], "HOLD")

    def test_o18_no_invented_people(self):
        out = evaluate_training({})
        self.assertFalse(out["live"])

    def test_in_memory_vent_is_simulation(self):
        from backend.services.ventilation_telemetry_service import ventilation_telemetry_service
        from backend.services.official_opportunity_runtime import sample_o11, sample_o13
        from backend.services.official_catalog import CATALOG

        self.assertEqual(len(CATALOG), 20)
        pts = ventilation_telemetry_service.get_all_points()
        self.assertEqual(pts["WEATHER.OutdoorDryBulb"]["source"], "SIMULATION")
        sampled = sample_o11()
        self.assertIsNotNone(sampled.get("OAT"))
        self.assertIsNotNone(sample_o13().get("CO_PPM"))
        weather = pts["WEATHER.OutdoorDryBulb"]
        sim = evaluate_air_cooled_hp(
            {
                "OAT": weather.get("value"),
                "HEAD_PRESSURE": 200,
                "COND_TEMP": 40,
                "source": weather.get("source"),
                "quality": weather.get("quality") or "GOOD",
            }
        )
        self.assertFalse(sim["live"])
        self.assertEqual(sim["status"], "SIMULATION")


if __name__ == "__main__":
    unittest.main()
