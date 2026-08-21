"""Operations & Maintenance O17–O20 public API. O10 excluded."""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.agents.operations_maintenance.o17_energy_planning_engine import evaluate_o17
from backend.agents.operations_maintenance.o18_training_engine import evaluate_o18
from backend.agents.operations_maintenance.o19_maintenance_engine import evaluate_o19
from backend.agents.operations_maintenance.o20_control_software_engine import evaluate_o20
from backend.api.hvac_operations_maintenance_controller import router as om_router
from backend.services.hvac_operations_maintenance_module import (
    canonical_oid,
    get_opportunities,
    get_opportunity,
    get_dashboard,
    dispatch_gate,
    dispatch_conflict,
)
from backend.services.operations_maintenance_opportunity_service import (
    ensure_om_demo,
    record_action,
    record_verify,
    record_rollback,
)
from database.session import init_db, SessionLocal


class TestCanonical(unittest.TestCase):
    def test_aliases_and_o10(self):
        self.assertEqual(canonical_oid("017"), "O17")
        self.assertEqual(canonical_oid("o18"), "O18")
        self.assertEqual(canonical_oid("019"), "O19")
        self.assertEqual(canonical_oid("20"), "O20")
        self.assertIsNone(canonical_oid("O10"))
        self.assertIsNone(canonical_oid("O11"))
        self.assertIsNone(canonical_oid("O13"))


class TestAgents(unittest.TestCase):
    def test_o17_missing(self):
        self.assertFalse(evaluate_o17({})["available"])

    def test_o17_insufficient_data(self):
        out = evaluate_o17({"hvac_power_kw": 128.4})
        self.assertTrue(out["available"])
        self.assertEqual(out["supervisory_decision"], "WAIT_FOR_TELEMETRY")

    def test_o17_valid(self):
        out = evaluate_o17({"hvac_power_kw": 428.5, "baseline_kw": 462.0, "occupancy": 68, "outdoor_temp_c": 28.1})
        self.assertTrue(out["available"])
        self.assertEqual(out["current_kw"], 428.5)
        self.assertIsNotNone(out["confidence"])
        self.assertIn(out["supervisory_decision"], ("OPTIMIZE", "MONITOR", "HOLD"))

    def test_o17_high_energy_deviation(self):
        out = evaluate_o17({"hvac_power_kw": 158.0, "baseline_kw": 145.0, "occupancy": 70})
        self.assertEqual(out["supervisory_decision"], "OPTIMIZE")
        self.assertGreater(out["deviation_pct"], 8)
        self.assertEqual(out["priority"], "HIGH")

    def test_o17_invalid_values(self):
        out = evaluate_o17({"hvac_power_kw": "nan"})
        self.assertFalse(out["available"])

    def test_o17_safety_hold_occupancy(self):
        out = evaluate_o17({"hvac_power_kw": 120, "baseline_kw": 140, "occupancy": -1})
        self.assertEqual(out["supervisory_decision"], "BLOCK")
        self.assertEqual(out["safety_status"], "FAIL")

    def test_o18_missing(self):
        self.assertFalse(evaluate_o18({})["available"])

    def test_o18_training_recommendation(self):
        out = evaluate_o18(
            {
                "programs": [{"program_name": "SAT reset", "required": True, "status": "OPEN"}],
                "completions": [{"completion_pct": 62, "status": "IN_PROGRESS", "role_label": "OPERATOR"}],
                "energy_impact_kwh_day": 8.4,
                "affected_users": 14,
            }
        )
        self.assertTrue(out["available"])
        self.assertEqual(out["recommendation"], "ASSIGN_TRAINING")
        self.assertEqual(out["affected_users"], 14)
        self.assertGreater(out["training_items"], 0)
        self.assertIn(out["priority"], ("HIGH", "MEDIUM"))

    def test_o18_repeated_operator_override(self):
        out = evaluate_o18(
            {
                "programs": [{"program_name": "SAT reset", "required": True, "status": "COMPLETED"}],
                "completions": [{"completion_pct": 90, "status": "COMPLETED"}],
                "manual_override_count": 4,
            }
        )
        self.assertGreater(out["knowledge_gap_count"], 0)
        self.assertEqual(out["priority"], "HIGH")
        self.assertFalse(out["dispatch_eligible"])

    def test_o18_missing_behavioral_data(self):
        self.assertFalse(evaluate_o18({})["available"])

    def test_o19_missing(self):
        self.assertFalse(evaluate_o19({})["available"])

    def test_o19_healthy_equipment(self):
        out = evaluate_o19({"equipment_health_pct": 96.0})
        self.assertEqual(out["status"], "NORMAL")
        self.assertEqual(out["issues_detected"], 0)
        self.assertEqual(out["assets_at_risk"], 0)

    def test_o19_degraded_filter(self):
        out = evaluate_o19({"filter_dp_rise_pct": 34, "fan_power_kw": 14.1, "equipment_health_pct": 87, "equipment_id": "AHU-02"})
        self.assertTrue(out["available"])
        self.assertGreater(out["issues_detected"], 0)
        self.assertAlmostEqual(out["estimated_energy_impact_kw"], 4.79, places=1)
        self.assertEqual(out["supervisory_decision"], "MAINTENANCE_REQUIRED")
        self.assertFalse(out["dispatch_eligible"])

    def test_o19_abnormal_pressure(self):
        out = evaluate_o19({"filter_dp_rise_pct": 55, "fan_power_kw": 16.0, "equipment_id": "AHU-01"})
        self.assertEqual(out["status"], "URGENT_MAINTENANCE")

    def test_o19_sensor_drift(self):
        out = evaluate_o19({"sensor_drift_pct": 7.5, "equipment_health_pct": 88, "equipment_id": "AHU-03"})
        self.assertTrue(any(i["issue_type"] == "SENSOR_DRIFT" for i in out["detected_issues"]))
        self.assertEqual(out["supervisory_decision"], "MAINTENANCE_REQUIRED")

    def test_o19_critical_condition(self):
        out = evaluate_o19({"filter_dp_rise_pct": 62, "fan_power_kw": 18.0, "equipment_id": "AHU-01"})
        self.assertEqual(out["priority"], "CRITICAL")

    def test_o20_missing(self):
        self.assertFalse(evaluate_o20({})["available"])

    def test_o20_healthy_controller(self):
        out = evaluate_o20({"controller": {"controller_id": "NCE-01", "software_version": "v4.8.2", "comm_status": "ONLINE", "config_drift_pct": 1.1}})
        self.assertEqual(out["supervisory_decision"], "MONITOR")
        self.assertFalse(out["dispatch_eligible"])

    def test_o20_stale_points(self):
        out = evaluate_o20({"controller": {"controller_id": "NCE-01", "comm_status": "ONLINE", "stale_points": 12}})
        self.assertEqual(out["recommendation"], "INVESTIGATE_STALE_POINTS")

    def test_o20_manual_override(self):
        out = evaluate_o20({"controller": {"controller_id": "NCE-01", "comm_status": "ONLINE", "override_count": 8}})
        self.assertEqual(out["recommendation"], "REVIEW_MANUAL_OVERRIDES")

    def test_o20_configuration_drift(self):
        out = evaluate_o20({"controller": {"controller_id": "NCE-01", "software_version": "v4.8.2", "comm_status": "ONLINE", "config_drift_pct": 6.2}})
        self.assertEqual(out["supervisory_decision"], "REVIEW_REQUIRED")
        self.assertFalse(out["dispatch_eligible"])

    def test_o20_critical_control_issue(self):
        out = evaluate_o20({"controller": {"controller_id": "NCE-01", "comm_status": "ONLINE", "critical_issues": 2}})
        self.assertEqual(out["safety_status"], "FAIL")

    def test_o20_offline_blocks(self):
        out = evaluate_o20({"controller": {"controller_id": "NCE-01", "comm_status": "OFFLINE"}})
        self.assertEqual(out["supervisory_decision"], "BLOCK")


class TestModule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        db = SessionLocal()
        try:
            ensure_om_demo(db, force=True)
        finally:
            db.close()

    def test_dashboard_ids(self):
        dash = get_dashboard()
        ids = [o["id"] for o in dash["opportunities"]]
        self.assertEqual(ids, ["O17", "O18", "O19", "O20"])
        self.assertNotIn("O10", ids)
        self.assertNotIn("O11", ids)
        blob = str(dash)
        self.assertNotIn("Economy Cycle", blob)
        self.assertEqual(dash["module"]["bms"]["status"], "OFFLINE")
        self.assertEqual(dash["module"]["telemetry"]["state"], "SIMULATED")
        self.assertNotEqual(dash["module"]["telemetry"]["state"], "LIVE")
        self.assertEqual(dash["module"]["kpis"]["opportunities"], 4)
        self.assertEqual(dash["module"]["kpis"]["liveCount"], 0)
        self.assertFalse(dash["module"].get("bmsConnected"))
        self.assertIn("charts", dash)

    def test_detail_contract(self):
        for oid in ("O17", "O18", "O19", "O20"):
            r = get_opportunity(oid)
            for key in ("telemetry", "current", "optimized", "delta", "energy", "safety", "recommendation", "supervisory", "dispatch", "failSafe", "metadata"):
                self.assertIn(key, r)
            self.assertFalse(r["dispatch"]["eligible"])
            self.assertNotEqual(r["telemetry"]["state"], "LIVE")
            self.assertFalse(r["live"])
            self.assertIn("bmsConnected", r)
            self.assertTrue(r["dispatch"].get("blockCode"))

    def test_dispatch_gate_demo(self):
        body = get_opportunity("O17")
        ok, reason = dispatch_gate(body)
        self.assertFalse(ok)
        self.assertTrue("Demo" in reason or "BMS" in reason)
        conflict = dispatch_conflict(body)
        self.assertFalse(conflict["dispatchable"])
        self.assertIn("telemetryStatus", conflict)
        self.assertTrue(conflict.get("code"))
        self.assertTrue(conflict.get("message"))

    def test_o20_uses_payload_when_controller_row_missing(self):
        from backend.agents.operations_maintenance.o20_control_software_engine import evaluate_o20
        from backend.services.operations_maintenance_opportunity_service import _snapshot
        from database.models_opportunities import ControllerSoftwareStatusDB

        db = SessionLocal()
        try:
            db.query(ControllerSoftwareStatusDB).delete()
            db.commit()
            snap = _snapshot(
                db,
                "O20",
                {
                    "controller_id": "NCE-01",
                    "software_version": "v4.8.2",
                    "comm_status": "ONLINE",
                    "point_count": 100,
                    "healthy_points": 97,
                    "override_count": 8,
                    "drift_count": 3,
                },
            )
            self.assertEqual(snap["controller"]["controller_id"], "NCE-01")
            out = evaluate_o20(snap)
            self.assertTrue(out["available"])
            self.assertNotEqual(out.get("status"), "UNAVAILABLE")
            self.assertEqual(out.get("override_count"), 8)
        finally:
            ensure_om_demo(db, force=False)
            db.close()

    def test_o18_never_equipment_dispatch(self):
        body = get_opportunity("O18")
        ok, reason = dispatch_gate(body)
        self.assertFalse(ok)
        self.assertIn("advisory", reason.lower())

    def test_actions_persist(self):
        rec = record_action("O18", "TRAINING_ACTION", {"topic": "SAT reset"})
        self.assertEqual(rec["status"], "RECORDED")
        ver = record_verify("O19")
        self.assertEqual(ver["status"], "VERIFIED")
        rb = record_rollback("O17")
        self.assertEqual(rb["status"], "ROLLED_BACK")


class TestOmHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        db = SessionLocal()
        try:
            ensure_om_demo(db, force=True)
        finally:
            db.close()
        app = FastAPI()
        app.include_router(om_router)
        cls.client = TestClient(app)

    def test_list(self):
        r = self.client.get("/api/hvac/operations-maintenance/opportunities")
        self.assertEqual(r.status_code, 200)
        self.assertEqual([o["id"] for o in r.json()["opportunities"]], ["O17", "O18", "O19", "O20"])

    def test_dashboard_alias(self):
        r = self.client.get("/api/hvac/operations-maintenance/dashboard")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["module"]["kpis"]["opportunities"], 4)

    def test_detail_and_aliases(self):
        for path in ("O17", "017", "O18", "018", "O19", "019", "O20", "020"):
            r = self.client.get(f"/api/hvac/operations-maintenance/{path}")
            self.assertEqual(r.status_code, 200, path)

    def test_missing_opportunity(self):
        r = self.client.get("/api/hvac/operations-maintenance/O10")
        self.assertEqual(r.status_code, 404)
        r2 = self.client.get("/api/hvac/operations-maintenance/O11")
        self.assertEqual(r2.status_code, 404)

    def test_dispatch_safety(self):
        r = self.client.post("/api/hvac/operations-maintenance/O17/dispatch", json={})
        self.assertEqual(r.status_code, 409)
        detail = r.json()["detail"]
        self.assertFalse(detail["dispatchable"])
        self.assertIn("reason", detail)
        self.assertTrue(detail.get("code"))
        self.assertTrue(detail.get("message"))
        r18 = self.client.post("/api/hvac/operations-maintenance/O18/dispatch", json={})
        self.assertEqual(r18.status_code, 409)
        d18 = r18.json()["detail"]
        self.assertTrue(d18.get("code"))
        self.assertTrue(d18.get("message"))
        r19 = self.client.post("/api/hvac/operations-maintenance/O19/dispatch", json={})
        self.assertEqual(r19.status_code, 409)
        self.assertTrue(r19.json()["detail"].get("code"))
        r20 = self.client.post("/api/hvac/operations-maintenance/O20/dispatch", json={})
        self.assertEqual(r20.status_code, 409)
        self.assertTrue(r20.json()["detail"].get("code"))

    def test_rollback_verify(self):
        self.assertEqual(self.client.post("/api/hvac/operations-maintenance/O17/rollback").status_code, 200)
        self.assertEqual(self.client.post("/api/hvac/operations-maintenance/O19/verify").status_code, 200)


if __name__ == "__main__":
    unittest.main()
