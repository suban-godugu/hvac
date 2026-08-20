import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from backend.agents.official_opportunities.o16_water_cooled_hp import (
    O16WaterCooledHeadPressureOptimizer,
    evaluate_water_cooled_hp,
)
from backend.services.hvac_safety_contract import evaluate_dispatch
from backend.services.o16_service import apply_command, create_command, evaluate_o16, ingest_points, optimize, save_config, verify
from backend.agents.runtime.command import get_command

LIVE = {
    "CEWT": 29.4,
    "CLWT": 33.1,
    "HEAD_PRESSURE": 220.0,
    "COND_TEMP": 38.0,
    "CW_FLOW": 400.0,
    "PUMP_SPEED": 80.0,
    "PUMP_STATE": 1,
    "PUMP_POWER_KW": 18.2,
    "VALVE_POSITION": 70.0,
    "LOAD": 47.0,
    "COOLING_CALL": 1,
    "quality": "GOOD",
    "source": "LIVE_BMS",
    "age_seconds": 2,
}

CFG = {
    "control_strategy": "VSD_PUMP",
    "target_head_pressure": 190.0,
    "pump_trim_pct": 2.0,
    "hp_deadband": 2.0,
    "high_load_pct": 90.0,
}


class TestO16WaterCooledHp(unittest.TestCase):
    def test_missing_telemetry_not_live(self):
        out = evaluate_water_cooled_hp({})
        self.assertFalse(out["live"])
        self.assertEqual(out["recommendation"], "HOLD")

    def test_state_construction(self):
        out = evaluate_water_cooled_hp(LIVE, CFG)
        cs = out["current_state"]
        self.assertEqual(cs["cewt_c"], 29.4)
        self.assertEqual(cs["cw_delta_t_c"], 3.7)
        self.assertIsNotNone(cs["load_ratio"])

    def test_low_load_optimize_pump(self):
        out = evaluate_water_cooled_hp(LIVE, CFG)
        self.assertEqual(out["recommendation"], "OPTIMIZE_HP")
        self.assertLess(out["optimized_state"]["recommended_pump_speed_pct"], LIVE["PUMP_SPEED"])
        self.assertEqual(out["energy_impact_class"], "PREDICTED")
        self.assertIsNone(out["verified_savings_kw"])
        self.assertTrue(out["live"])

    def test_optimizer_class(self):
        opt = O16WaterCooledHeadPressureOptimizer()
        out = opt.evaluate(LIVE, CFG)
        self.assertEqual(out["recommendation"], "OPTIMIZE_HP")

    def test_high_load_hold(self):
        tel = dict(LIVE, LOAD=95.0)
        out = evaluate_water_cooled_hp(tel, CFG)
        self.assertEqual(out["recommendation"], "HOLD")
        self.assertIn("High cooling load", out["reason"])

    def test_hold_without_configured_target(self):
        out = evaluate_water_cooled_hp(LIVE, {"control_strategy": "VSD_PUMP"})
        self.assertEqual(out["recommendation"], "HOLD")
        self.assertIn("target_head_pressure", out["reason"])

    def test_stale_hold(self):
        tel = dict(LIVE, quality="STALE", age_seconds=400)
        out = evaluate_water_cooled_hp(tel, CFG)
        self.assertEqual(out["recommendation"], "HOLD")
        self.assertIn("STALE", out["reason"])

    def test_bad_quality_hold(self):
        tel = dict(LIVE, quality="BAD")
        out = evaluate_water_cooled_hp(tel, CFG)
        self.assertEqual(out["recommendation"], "HOLD")

    def test_simulation_not_live(self):
        tel = dict(LIVE, source="SIMULATION")
        out = evaluate_water_cooled_hp(tel, CFG)
        self.assertFalse(out["live"])
        self.assertEqual(out["status"], "SIMULATION")

    def test_min_head_pressure_reject(self):
        tel = dict(LIVE, HEAD_PRESSURE=140.0)
        out = evaluate_water_cooled_hp(tel, {**CFG, "min_head_pressure": 180.0})
        self.assertEqual(out["recommendation"], "BLOCKED")

    def test_min_flow_reject(self):
        tel = dict(LIVE, CW_FLOW=50.0)
        out = evaluate_water_cooled_hp(tel, {**CFG, "min_cw_flow": 200.0})
        self.assertEqual(out["recommendation"], "BLOCKED")

    def test_pump_speed_limit(self):
        out = evaluate_water_cooled_hp(LIVE, {**CFG, "min_pump_speed_pct": 79.0})
        self.assertEqual(out["recommendation"], "BLOCKED")

    def test_valve_limit(self):
        tel = dict(LIVE, COOLING_CALL=0, VALVE_POSITION=40.0)
        out = evaluate_water_cooled_hp(tel, {"control_strategy": "VALVE", "shared_pump": True, "min_valve_pct": 10.0, "isolate_valve_pct": 0.0})
        self.assertEqual(out["recommendation"], "BLOCKED")

    def test_rate_of_change(self):
        out = evaluate_water_cooled_hp(LIVE, {**CFG, "pump_trim_pct": 40.0, "max_pump_step_pct": 5.0})
        self.assertEqual(out["recommendation"], "BLOCKED")

    def test_simulation_write_rejected(self):
        ok, reason, _ = evaluate_dispatch(
            {
                "id": "O16",
                "source": "SIMULATION",
                "telemetry": {"source": "SIMULATION", "quality": "GOOD", "age_seconds": 1},
                "supervisory": {"decision": "OPTIMIZE"},
                "safety": {"status": "PASS"},
                "confidence": 0.9,
                "current_value": 80,
                "target_value": 78,
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
                    "id": "O16",
                    "source": "LIVE_BMS",
                    "telemetry": {"source": "LIVE_BMS", "quality": "GOOD", "age_seconds": 1, "raw": "LIVE"},
                    "supervisory": {"decision": "OPTIMIZE"},
                    "safety": {"status": "PASS"},
                    "confidence": 0.9,
                    "current_value": 80,
                    "target_value": 78,
                }
            )
            self.assertFalse(ok)
            self.assertEqual(info.get("code"), "SAFE_MODE")
        finally:
            if prev is None:
                os.environ.pop("HVAC_SAFE_MODE", None)
            else:
                os.environ["HVAC_SAFE_MODE"] = prev

    def test_bms_offline_apply_blocked_and_idempotency(self):
        save_config({"target_head_pressure": 190.0, "control_strategy": "VSD_PUMP", "control_mode": "ADVISORY"})
        ingest_points(
            [
                {"point_id": "CW.SupplyTemp", "value": 29.4, "unit": "°C", "source": "LIVE_BMS", "quality": "GOOD"},
                {"point_id": "CW.ReturnTemp", "value": 33.1, "unit": "°C", "source": "LIVE_BMS", "quality": "GOOD"},
                {"point_id": "CW.HeadPressure", "value": 220, "source": "LIVE_BMS", "quality": "GOOD"},
                {"point_id": "CW.PumpSpeed", "value": 80, "unit": "%", "source": "LIVE_BMS", "quality": "GOOD"},
                {"point_id": "CW.PumpPower", "value": 18.2, "unit": "kW", "source": "LIVE_BMS", "quality": "GOOD"},
                {"point_id": "CW.Load", "value": 47, "unit": "%", "source": "LIVE_BMS", "quality": "GOOD"},
                {"point_id": "CW.CoolingCall", "value": 1, "source": "LIVE_BMS", "quality": "GOOD"},
            ]
        )
        state = evaluate_o16(persist=True)
        self.assertIn(state.get("recommendation"), ("OPTIMIZE_HP", "HOLD", "BLOCKED", "ISOLATE_UNIT"))
        cmd = create_command({})
        self.assertEqual(cmd.get("opportunity"), "O16")
        cid = cmd["command_id"]
        again = create_command({"command_id": cid})
        self.assertEqual(again["command_id"], cid)
        with self.assertRaises(Exception):
            apply_command(cid, confirm=True)
        v = verify(cid)
        self.assertFalse(v.get("ok"))
        self.assertTrue(get_command(cid))

    def test_dashboard_http_contract(self):
        from fastapi.testclient import TestClient
        from backend.main import app

        client = TestClient(app)
        res = client.get("/api/agents/variable-speed/o16/dashboard")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body.get("opportunity") or body.get("opportunity_id") or (body.get("header") or {}).get("opportunity"), "O16")
        if not body.get("live"):
            self.assertNotEqual((body.get("header") or {}).get("bms"), "LIVE")
            self.assertNotEqual(body.get("ui_state"), "LIVE")
        health = client.get("/api/agents/variable-speed/o16/health")
        self.assertEqual(health.status_code, 200)
        out = optimize()
        self.assertIn(out.get("recommendation"), ("OPTIMIZE_HP", "HOLD", "BLOCKED", "ISOLATE_UNIT"))
        dash = client.get("/api/agents/variable-speed/o16/dashboard").json()
        self.assertIn("savings", dash)
        self.assertIn("predicted_kw", dash["savings"])


if __name__ == "__main__":
    unittest.main()
