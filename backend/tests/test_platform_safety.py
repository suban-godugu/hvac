"""Shared safety contract: simulation/stale/missing cannot dispatch to BMS."""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from backend.services.hvac_safety_contract import evaluate_dispatch
from backend.agents.scheduling_supervisory.gateway import SimulatorBMSGateway, ProductionBMSGateway, reset_bms_gateway


class TestDispatchContract(unittest.TestCase):
    def test_simulation_blocked(self):
        ok, reason, _ = evaluate_dispatch(
            {
                "id": "O17",
                "source": "SIMULATION",
                "telemetry": {"raw": "LIVE", "source": "SIMULATION", "quality": "GOOD", "ageSeconds": 1},
                "supervisory": {"decision": "OPTIMIZE"},
                "safety": {"status": "PASS", "passed": True},
                "confidence": 0.9,
                "current_value": 10,
                "target_value": 9,
            }
        )
        self.assertFalse(ok)
        self.assertIn("Demo/simulation", reason)

    def test_demo_blocked(self):
        ok, _, _ = evaluate_dispatch({"id": "O11", "source": "DEMO", "telemetry": {"raw": "LIVE", "source": "DEMO"}, "supervisory": {"decision": "OPTIMIZE"}, "safety": {"status": "PASS"}, "confidence": 0.9, "current_value": 1, "target_value": 2})
        self.assertFalse(ok)

    def test_stale_hold(self):
        ok, reason, c = evaluate_dispatch(
            {
                "id": "O12",
                "source": "LIVE_BMS",
                "telemetry": {"raw": "STALE", "source": "LIVE_BMS", "quality": "STALE", "ageSeconds": 400},
                "supervisory": {"decision": "OPTIMIZE"},
                "safety": {"status": "PASS"},
                "confidence": 0.9,
                "current_value": 1,
                "target_value": 2,
            }
        )
        self.assertFalse(ok)
        self.assertEqual(c["status"], "STALE")
        self.assertIn("SAFE_HOLD", reason)

    def test_missing_wait(self):
        ok, reason, c = evaluate_dispatch(
            {
                "id": "O13",
                "source": "LIVE_BMS",
                "telemetry": {"raw": "MISSING", "source": "LIVE_BMS", "quality": "MISSING"},
                "supervisory": {"decision": "OPTIMIZE"},
                "safety": {"status": "PASS"},
                "confidence": 0.9,
                "current_value": 1,
                "target_value": 2,
            }
        )
        self.assertFalse(ok)
        self.assertEqual(c["decision_hint"], "WAIT_FOR_TELEMETRY")

    def test_simulator_gateway_write_blocked(self):
        gw = SimulatorBMSGateway()
        res = gw.write_point("AHU-1-SAT-SP", 14.5)
        self.assertFalse(res.success)

    def test_production_gateway_not_connected(self):
        reset_bms_gateway()
        gw = ProductionBMSGateway()
        self.assertFalse(gw.is_production_connected())
        res = gw.write_point("AHU-1-SAT-SP", 14.5)
        self.assertFalse(res.success)

    def test_viewer_cannot_dispatch(self):
        ok, reason, _ = evaluate_dispatch(
            {
                "id": "O1",
                "source": "LIVE_BMS",
                "telemetry": {"raw": "LIVE", "source": "LIVE_BMS", "quality": "GOOD", "ageSeconds": 2},
                "supervisory": {"decision": "OPTIMIZE"},
                "safety": {"status": "PASS", "passed": True},
                "confidence": 0.99,
                "current_value": 10,
                "target_value": 9,
                "user": {"role": "viewer"},
            }
        )
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
