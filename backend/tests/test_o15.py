import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from backend.agents.official_opportunities.o15_air_cooled_hp import evaluate_air_cooled_hp
from backend.services.hvac_safety_contract import evaluate_dispatch
from backend.services.o15_service import apply_command, create_command, evaluate_o15, ingest_points, optimize
from backend.agents.runtime.command import get_command


LIVE = {
    "HEAD_PRESSURE": 210.0,
    "HP_SETPOINT": 220.0,
    "COND_TEMP": 42.0,
    "OAT": 28.0,
    "FAN_SPEED": 55.0,
    "FAN_STATE": 1,
    "FAN_POWER_KW": 8.0,
    "LOAD": 60.0,
    "POWER": 80.0,
    "quality": "GOOD",
    "source": "LIVE_BMS",
    "age_seconds": 2,
}


class TestO15AirCooledHp(unittest.TestCase):
    def test_missing_telemetry_not_live(self):
        out = evaluate_air_cooled_hp({})
        self.assertFalse(out["live"])
        self.assertEqual(out["recommendation"], "HOLD")

    def test_float_when_oat_and_tcond_available(self):
        out = evaluate_air_cooled_hp(LIVE)
        self.assertEqual(out["recommendation"], "FLOAT_HEAD_PRESSURE")
        self.assertAlmostEqual(out["optimized_state"]["recommended_condensing_temp_c"], 38.0, places=1)
        self.assertGreater(out["optimized_state"]["recommended_fan_speed_pct"], LIVE["FAN_SPEED"])
        self.assertIn("8", out["reason"])
        self.assertIn("12", out["reason"])
        self.assertEqual(out["energy_impact_class"], "PREDICTED")
        self.assertIsNone(out["verified_savings_kw"])
        self.assertTrue(out["live"])

    def test_hold_when_tcond_in_deadband(self):
        tel = dict(LIVE, COND_TEMP=38.0)
        out = evaluate_air_cooled_hp(tel)
        self.assertEqual(out["recommendation"], "HOLD")

    def test_over_condense_reduces_fan(self):
        tel = dict(LIVE, COND_TEMP=32.0)
        out = evaluate_air_cooled_hp(tel)
        self.assertEqual(out["recommendation"], "FLOAT_HEAD_PRESSURE")
        self.assertLess(out["optimized_state"]["recommended_fan_speed_pct"], LIVE["FAN_SPEED"])
        self.assertIn("over-condensing", out["reason"].lower())

    def test_stale_hold(self):
        tel = dict(LIVE, quality="STALE", age_seconds=400)
        out = evaluate_air_cooled_hp(tel)
        self.assertEqual(out["recommendation"], "HOLD")
        self.assertIn("STALE", out["reason"])

    def test_bad_quality_hold(self):
        tel = dict(LIVE, quality="BAD")
        out = evaluate_air_cooled_hp(tel)
        self.assertEqual(out["recommendation"], "HOLD")

    def test_simulation_not_live(self):
        tel = dict(LIVE, source="SIMULATION")
        out = evaluate_air_cooled_hp(tel)
        self.assertFalse(out["live"])
        self.assertEqual(out["status"], "SIMULATION")

    def test_engineering_limit_reject_when_configured(self):
        tel = dict(LIVE, HEAD_PRESSURE=320.0)
        cfg = {"max_head_pressure": 280.0}
        out = evaluate_air_cooled_hp(tel, cfg)
        self.assertEqual(out["recommendation"], "REJECT")

    def test_rate_of_change_reject(self):
        tel = dict(LIVE, FAN_SPEED=10.0, COND_TEMP=50.0)
        out = evaluate_air_cooled_hp(tel, {"fan_trim_pct": 40.0, "max_fan_step_pct": 5.0})
        self.assertEqual(out["recommendation"], "REJECT")

    def test_no_invented_hp_target_without_curve(self):
        out = evaluate_air_cooled_hp(LIVE)
        self.assertIsNone(out["optimized_state"]["recommended_head_pressure"])
        self.assertEqual(out["optimized_state"]["saturation_curve_source"], "NOT_CONFIGURED")

    def test_configurable_saturation_curve(self):
        curve = [{"t_c": 30, "hp": 140}, {"t_c": 40, "hp": 180}]
        out = evaluate_air_cooled_hp(LIVE, {"saturation_curve_json": curve, "approach_c": 10.0})
        self.assertIsNotNone(out["optimized_state"]["recommended_head_pressure"])
        self.assertEqual(out["optimized_state"]["saturation_curve_source"], "CONFIGURABLE")

    def test_simulation_write_rejected(self):
        ok, reason, _ = evaluate_dispatch(
            {
                "id": "O15",
                "source": "SIMULATION",
                "telemetry": {"source": "SIMULATION", "quality": "GOOD", "age_seconds": 1},
                "supervisory": {"decision": "OPTIMIZE"},
                "safety": {"status": "PASS"},
                "confidence": 0.9,
                "current_value": 55,
                "target_value": 57,
            }
        )
        self.assertFalse(ok)
        self.assertIn("simulation", reason.lower())

    def test_safe_mode_write_rejected(self):
        prev = os.environ.get("HVAC_SAFE_MODE")
        os.environ["HVAC_SAFE_MODE"] = "1"
        try:
            ok, reason, info = evaluate_dispatch(
                {
                    "id": "O15",
                    "source": "LIVE_BMS",
                    "telemetry": {"source": "LIVE_BMS", "quality": "GOOD", "age_seconds": 1, "raw": "LIVE"},
                    "supervisory": {"decision": "OPTIMIZE"},
                    "safety": {"status": "PASS"},
                    "confidence": 0.9,
                    "current_value": 55,
                    "target_value": 57,
                }
            )
            self.assertFalse(ok)
            self.assertEqual(info.get("code"), "SAFE_MODE")
        finally:
            if prev is None:
                os.environ.pop("HVAC_SAFE_MODE", None)
            else:
                os.environ["HVAC_SAFE_MODE"] = prev

    def test_bms_offline_apply_blocked(self):
        ingest_points(
            [
                {"point_id": "ACC.OAT", "value": 28, "unit": "°C", "source": "LIVE_BMS", "quality": "GOOD"},
                {"point_id": "ACC.CondTemp", "value": 42, "unit": "°C", "source": "LIVE_BMS", "quality": "GOOD"},
                {"point_id": "ACC.HeadPressure", "value": 210, "unit": "psig", "source": "LIVE_BMS", "quality": "GOOD"},
                {"point_id": "ACC.FanSpeed", "value": 55, "unit": "%", "source": "LIVE_BMS", "quality": "GOOD"},
            ]
        )
        o15_state = evaluate_o15(persist=True)
        self.assertTrue(o15_state.get("recommendation") in ("FLOAT_HEAD_PRESSURE", "HOLD", "REJECT"))
        cmd = create_command({})
        self.assertEqual(cmd.get("opportunity"), "O15")
        cid = cmd["command_id"]
        again = create_command({"command_id": cid})
        self.assertEqual(again["command_id"], cid)
        with self.assertRaises(Exception):
            apply_command(cid, confirm=True)

    def test_dashboard_http_contract(self):
        from fastapi.testclient import TestClient
        from backend.main import app

        client = TestClient(app)
        res = client.get("/api/agents/variable-speed/o15/dashboard")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body.get("opportunity_id") or (body.get("header") or {}).get("opportunity"), "O15")
        if not body.get("live"):
            self.assertNotEqual((body.get("header") or {}).get("bms"), "LIVE")
            self.assertNotEqual(body.get("ui_state"), "LIVE")
        ingest_points(
            [
                {"point_id": "ACC.OAT", "value": 26, "unit": "°C", "source": "LIVE_BMS", "quality": "GOOD"},
                {"point_id": "ACC.CondTemp", "value": 40, "unit": "°C", "source": "LIVE_BMS", "quality": "GOOD"},
                {"point_id": "ACC.HeadPressure", "value": 200, "unit": "psig", "source": "LIVE_BMS", "quality": "GOOD"},
                {"point_id": "ACC.FanSpeed", "value": 60, "unit": "%", "source": "LIVE_BMS", "quality": "GOOD"},
                {"point_id": "ACC.FanPower", "value": 7, "unit": "kW", "source": "LIVE_BMS", "quality": "GOOD"},
            ]
        )
        out = optimize()
        self.assertIn(out.get("recommendation"), ("FLOAT_HEAD_PRESSURE", "HOLD", "REJECT"))
        if out.get("command"):
            self.assertTrue(get_command(out["command"]["command_id"]))


if __name__ == "__main__":
    unittest.main()
