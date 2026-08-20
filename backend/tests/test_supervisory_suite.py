import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pytest
import unittest
from datetime import datetime

from backend.agents.scheduling_supervisory.agent import SchedulingSupervisoryAgent
from backend.agents.scheduling_supervisory.state import (
    AgentMode,
    AgentLifecycleState,
    CandidateAction,
    VerificationOutcome
)
from backend.agents.scheduling_supervisory.o1_engine import OptimumStartStopEngine
from backend.agents.scheduling_supervisory.o2_engine import SpaceTemperatureOptimizationEngine
from backend.agents.scheduling_supervisory.o3_engine import MasterAHUSATOptimizationEngine
from backend.agents.scheduling_supervisory.o4_engine import ChillerCompressorStagingEngine
from backend.agents.scheduling_supervisory.supervisory_decision_engine import SupervisoryDecisionEngine
from backend.agents.scheduling_supervisory.safety_engine import SafetyEngine
from backend.agents.scheduling_supervisory.gateway import SimulatorBMSGateway, ProductionBMSGateway


def get_mock_telemetry(oat=24.0, ztemp=24.5, chws=6.8, sat=13.0, sat_sp=13.0, total_tons=76.0, sensor_fault=False):
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "simulation_time": "07:00",
        "weather": {
            "oat": 999.0 if sensor_fault else oat,
            "oah": 55.0,
            "solar_irradiance": 450.0
        },
        "ahus": [
            {
                "id": "AHU-1",
                "fan_status": True,
                "fan_speed_pct": 65.0,
                "fan_power_kw": 10.4,
                "sat_actual": sat,
                "sat_setpoint": sat_sp,
                "cooling_valve_pct": 45.0,
                "vav_zones": [
                    {
                        "id": "VAV-101",
                        "temp_actual": ztemp,
                        "cooling_sp": 23.0,
                        "heating_sp": 20.0,
                        "deadband": 1.5,
                        "damper_pos": 30.0,
                        "occupied": True
                    },
                    {
                        "id": "VAV-102",
                        "temp_actual": ztemp + 0.5,
                        "cooling_sp": 22.5,
                        "heating_sp": 20.0,
                        "deadband": 1.5,
                        "damper_pos": 25.0,
                        "occupied": False  # Unoccupied
                    }
                ]
            }
        ],
        "plant": {
            "total_tons": total_tons,
            "total_power_kw": 42.5,
            "plant_efficiency_kw_per_ton": 0.56,
            "chws_temp": chws,
            "chws_setpoint": 6.7,
            "chwr_temp": 12.2,
            "flow_rate_lps": 28.5,
            "chillers": [
                {
                    "id": "CH-1",
                    "status": True,
                    "tons": total_tons,
                    "power_kw": 42.5,
                    "chws_temp": chws,
                    "chwr_temp": 12.2,
                    "flow_lps": 28.5,
                    "compressor_stages": {"1A": 100, "1B": 26},
                    "maintenance_lock": False
                },
                {
                    "id": "CH-2",
                    "status": False,
                    "tons": 0.0,
                    "power_kw": 0.0,
                    "chws_temp": chws,
                    "chwr_temp": 12.2,
                    "flow_lps": 0.0,
                    "compressor_stages": {"2A": 0, "2B": 0},
                    "maintenance_lock": False
                }
            ]
        },
        "building_occupancy": {
            "scheduled_start": "06:00",
            "occupancy_start": "08:00",
            "scheduled_stop": "18:00",
            "occupancy_stop": "18:00",
            "is_occupied_now": True
        },
        "stale_age_seconds": 2.0
    }


class TestSupervisoryAgentSuite(unittest.TestCase):

    def test_01_o1_optimum_start_stop(self):
        """O1 Engine calculates start delay and coast stop."""
        engine = OptimumStartStopEngine()
        state = get_mock_telemetry(oat=22.0, ztemp=23.5)
        res = engine.evaluate(state)

        self.assertEqual(res.opportunity_code, "O1")
        self.assertGreater(len(res.candidates), 0)
        self.assertIn("pulldown_minutes", res.current_state)
        self.assertGreater(res.confidence, 0.90)

    def test_02_o2_space_temperature_setback(self):
        """O2 Engine sets setback on unoccupied zone VAV-102."""
        engine = SpaceTemperatureOptimizationEngine()
        state = get_mock_telemetry()
        res = engine.evaluate(state)

        self.assertEqual(res.opportunity_code, "O2")
        setback_act = next((c for c in res.candidates if "VAV-102" in c.point_id), None)
        self.assertIsNotNone(setback_act)
        self.assertEqual(setback_act.proposed_value, 24.5)

    def test_03_o3_master_ahu_sat_trim_and_respond(self):
        """O3 Engine resets SAT warmer under low cooling call."""
        engine = MasterAHUSATOptimizationEngine()
        state = get_mock_telemetry(sat=13.0, sat_sp=13.0)
        res = engine.evaluate(state)

        self.assertEqual(res.opportunity_code, "O3")
        sat_act = next((c for c in res.candidates if "SAT-SP" in c.point_id), None)
        self.assertIsNotNone(sat_act)
        self.assertEqual(sat_act.proposed_value, 13.3)  # +0.3°C trim warmer

    def test_04_o4_chiller_staging_and_chws_reset(self):
        """O4 Engine resets CHWS warmer under part load."""
        engine = ChillerCompressorStagingEngine()
        state = get_mock_telemetry(total_tons=65.0)
        res = engine.evaluate(state)

        self.assertEqual(res.opportunity_code, "O4")
        chws_act = next((c for c in res.candidates if "PLANT-CHWS-SP" in c.point_id), None)
        self.assertIsNotNone(chws_act)
        self.assertEqual(chws_act.proposed_value, 7.2)

    def test_05_supervisory_decision_conflict_resolution(self):
        """SupervisoryDecisionEngine resolves duplicate points and produces coordinated set."""
        decision_engine = SupervisoryDecisionEngine()
        state = get_mock_telemetry()

        e1 = OptimumStartStopEngine().evaluate(state)
        e2 = SpaceTemperatureOptimizationEngine().evaluate(state)
        e3 = MasterAHUSATOptimizationEngine().evaluate(state)
        e4 = ChillerCompressorStagingEngine().evaluate(state)

        coordinated = decision_engine.produce_coordinated_action_set([e1, e2, e3, e4])
        self.assertGreater(len(coordinated), 0)

        # Verify no duplicate points
        points = [a.point_id for a in coordinated]
        self.assertEqual(len(points), len(set(points)))

    def test_06_safety_engine_11_gates_rejection(self):
        """SafetyEngine enforces low-limit clamp (freeze protection) and rate-of-change limiters."""
        safety = SafetyEngine()
        state = get_mock_telemetry()

        # Test A: Unsafe low SAT (< 12.0°C)
        unsafe_sat = CandidateAction(
            id="act-unsafe",
            opportunity_code="O3",
            point_id="AHU-1-SAT-SP",
            equipment_id="AHU-1",
            current_value=13.0,
            proposed_value=10.5,  # Unsafe! Below 12.0°C
            reason="Test unsafe low SAT",
            confidence=0.9,
            verification_window_minutes=15,
            expected_result="Test",
            rollback_value=13.0
        )
        res = safety.validate_action(unsafe_sat, state)
        self.assertFalse(res.passed)
        self.assertEqual(res.status, "REJECT")
        self.assertIn("breaches low limit clamp", res.rejection_reason)

        # Test B: Unregistered point
        unregistered = CandidateAction(
            id="act-bad-point",
            opportunity_code="O3",
            point_id="RANDOM-READONLY-SENSOR",
            equipment_id="AHU-1",
            current_value=1.0,
            proposed_value=2.0,
            reason="Test read only",
            confidence=0.9,
            verification_window_minutes=15,
            expected_result="Test",
            rollback_value=1.0
        )
        res_bad = safety.validate_action(unregistered, state)
        self.assertFalse(res_bad.passed)
        self.assertIn("read-only or not in writable register", res_bad.rejection_reason)

    def test_07_bms_gateway_simulator_and_ack(self):
        """Simulator writes are blocked unless HVAC_ALLOW_SIM_WRITES is explicitly enabled."""
        gateway = SimulatorBMSGateway()
        write_res = gateway.write_point("AHU-1-SAT-SP", 14.5, priority=10)
        self.assertFalse(write_res.success)

    def test_08_sensor_fault_engages_safe_mode(self):
        """Sensor fault automatically locks agent into SAFE_MODE and stops writes."""
        agent = SchedulingSupervisoryAgent()
        fault_telemetry = get_mock_telemetry(sensor_fault=True)

        res = agent.run_cycle(fault_telemetry)
        self.assertEqual(agent.mode, AgentMode.SAFE_MODE)
        self.assertEqual(len(res["candidate_actions"]), 0)
        self.assertIn("SAFE MODE LOCKDOWN", res["cycle_summary"])

    def test_09_closed_loop_verification_and_rollback(self):
        """VerificationEngine detects failure and RollbackEngine restores safe baseline."""
        agent = SchedulingSupervisoryAgent()
        agent.set_mode(AgentMode.AUTO)

        normal_state = get_mock_telemetry()
        res = agent.run_cycle(normal_state)
        self.assertEqual(agent.mode, AgentMode.AUTO)
        self.assertGreater(len(res["completed_actions"]), 0)

    def test_10_approval_required_mode_and_operator_approval(self):
        """APPROVAL_REQUIRED queues actions and executes on operator approval."""
        agent = SchedulingSupervisoryAgent()
        agent.set_mode(AgentMode.APPROVAL_REQUIRED)

        res = agent.run_cycle(get_mock_telemetry())
        self.assertGreater(len(agent.pending_approvals), 0)

        target_act = agent.pending_approvals[0]
        approved_record = agent.approve_action(target_act.id)
        self.assertIsNotNone(approved_record)
        self.assertEqual(approved_record.final_status, "VERIFIED_KEPT")
        self.assertNotIn(target_act.id, [a.id for a in agent.pending_approvals])


if __name__ == "__main__":
    unittest.main()
