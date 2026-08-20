import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from backend.agents.official_opportunities.o14_secondary_chw import evaluate_secondary_chw
from backend.services.hvac_safety_contract import evaluate_dispatch
from backend.services.o14_service import apply_command, create_command, evaluate_o14, ingest_points, optimize
from backend.agents.runtime.command import get_command


LIVE = {
    "INDEX_DP": 18.0,
    "DP_SETPOINT": 22.0,
    "MOST_OPEN_VALVE_PCT": 72.0,
    "VALVE_AVG_PCT": 55.0,
    "FLOW": 420.0,
    "SPEED_PCT": 78.0,
    "POWER_KW": 12.4,
    "COOLING_CALL": 1,
    "quality": "GOOD",
    "source": "LIVE_BMS",
    "age_seconds": 2,
}


class TestO14SecondaryChw(unittest.TestCase):
    def test_missing_telemetry_not_live(self):
        out = evaluate_secondary_chw({})
        self.assertFalse(out["live"])
        self.assertEqual(out["recommendation"], "HOLD")

    def test_dp_reset_when_valves_below_95(self):
        out = evaluate_secondary_chw(LIVE)
        self.assertEqual(out["recommendation"], "RESET_DP")
        self.assertLess(out["optimized_state"]["recommended_dp_setpoint"], LIVE["DP_SETPOINT"])
        self.assertIn("95", out["reason"])
        self.assertEqual(out["energy_impact_class"], "PREDICTED")
        self.assertIsNone(out["verified_savings_kw"])

    def test_hold_when_most_open_at_target(self):
        tel = dict(LIVE, MOST_OPEN_VALVE_PCT=95.0)
        out = evaluate_secondary_chw(tel)
        self.assertEqual(out["recommendation"], "HOLD")

    def test_hold_when_valve_100_no_invented_increase(self):
        tel = dict(LIVE, MOST_OPEN_VALVE_PCT=100.0)
        out = evaluate_secondary_chw(tel)
        self.assertEqual(out["recommendation"], "HOLD")
        self.assertIn("balancing", out["reason"].lower())

    def test_stale_hold(self):
        tel = dict(LIVE, quality="STALE", age_seconds=400)
        out = evaluate_secondary_chw(tel)
        self.assertEqual(out["recommendation"], "HOLD")
        self.assertIn("STALE", out["reason"])

    def test_bad_quality_hold(self):
        tel = dict(LIVE, quality="BAD")
        out = evaluate_secondary_chw(tel)
        self.assertEqual(out["recommendation"], "HOLD")

    def test_simulation_not_live(self):
        tel = dict(LIVE, source="SIMULATION")
        out = evaluate_secondary_chw(tel)
        self.assertFalse(out["live"])
        self.assertEqual(out["status"], "SIMULATION")

    def test_engineering_limit_reject(self):
        tel = dict(LIVE, INDEX_DP=22.0)
        cfg = {"min_dp": 21.5, "dp_setpoint_trim": 2.0, "most_open_valve_target_pct": 95.0}
        out = evaluate_secondary_chw(tel, cfg)
        self.assertEqual(out["recommendation"], "REJECT")

    def test_cooling_call_off(self):
        tel = dict(LIVE, COOLING_CALL=0)
        out = evaluate_secondary_chw(tel)
        self.assertEqual(out["recommendation"], "HOLD")

    def test_simulation_write_rejected(self):
        ok, reason, _ = evaluate_dispatch(
            {
                "id": "O14",
                "source": "SIMULATION",
                "telemetry": {"source": "SIMULATION", "quality": "GOOD", "age_seconds": 1},
                "supervisory": {"decision": "OPTIMIZE"},
                "safety": {"status": "PASS"},
                "confidence": 0.9,
                "current_value": 22,
                "target_value": 21.5,
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
                    "id": "O14",
                    "source": "LIVE_BMS",
                    "telemetry": {"source": "LIVE_BMS", "quality": "GOOD", "age_seconds": 1, "raw": "LIVE"},
                    "supervisory": {"decision": "OPTIMIZE"},
                    "safety": {"status": "PASS"},
                    "confidence": 0.9,
                    "current_value": 22,
                    "target_value": 21.5,
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
                {"point_id": "SCHW.IndexDP", "value": 18, "unit": "psi", "source": "LIVE_BMS", "quality": "GOOD"},
                {"point_id": "SCHW.DPSetpoint", "value": 22, "unit": "psi", "source": "LIVE_BMS", "quality": "GOOD"},
                {"point_id": "SCHW.MostOpenValve", "value": 70, "unit": "%", "source": "LIVE_BMS", "quality": "GOOD"},
                {"point_id": "SCHW.CoolingCall", "value": 1, "unit": "", "source": "LIVE_BMS", "quality": "GOOD"},
            ]
        )
        o14_service_state = evaluate_o14(persist=True)
        self.assertTrue(o14_service_state.get("recommendation") in ("RESET_DP", "HOLD", "REJECT"))
        cmd = create_command({})
        self.assertEqual(cmd.get("opportunity"), "O14")
        cid = cmd["command_id"]
        again = create_command({"command_id": cid})
        self.assertEqual(again["command_id"], cid)
        with self.assertRaises(Exception):
            apply_command(cid, confirm=True)

    def test_dashboard_http_contract(self):
        from fastapi.testclient import TestClient
        from backend.main import app

        client = TestClient(app)
        res = client.get("/api/agents/variable-speed/o14/dashboard")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body.get("opportunity_id"), "O14")
        self.assertNotEqual(body.get("ui_state"), "LIVE") if not body.get("live") else True
        if not body.get("live"):
            self.assertNotEqual((body.get("header") or {}).get("bms"), "LIVE")
        ingest_points(
            [
                {"point_id": "SCHW.IndexDP", "value": 16, "unit": "psi", "source": "LIVE_BMS", "quality": "GOOD"},
                {"point_id": "SCHW.DPSetpoint", "value": 20, "unit": "psi", "source": "LIVE_BMS", "quality": "GOOD"},
                {"point_id": "SCHW.MostOpenValve", "value": 60, "unit": "%", "source": "LIVE_BMS", "quality": "GOOD"},
                {"point_id": "SCHW.Speed", "value": 80, "unit": "%", "source": "LIVE_BMS", "quality": "GOOD"},
                {"point_id": "SCHW.Power", "value": 11, "unit": "kW", "source": "LIVE_BMS", "quality": "GOOD"},
                {"point_id": "SCHW.CoolingCall", "value": 1, "source": "LIVE_BMS", "quality": "GOOD"},
            ]
        )
        out = optimize()
        self.assertEqual(out.get("opportunity_id"), "O14")
        if out.get("command"):
            self.assertTrue(get_command(out["command"]["command_id"]))


if __name__ == "__main__":
    unittest.main()
