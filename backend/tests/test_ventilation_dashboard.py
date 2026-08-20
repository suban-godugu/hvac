"""O10–O13 dashboard, formatters, enthalpy, IAQ, aggregation."""
import os
import sys
import unittest
from datetime import datetime, timedelta

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from database.session import init_db, SessionLocal
from database.models_ventilation import HvacTelemetryDB
from backend.services.ventilation_formatters import (
    format_percent,
    format_cfm,
    format_kw,
    format_kwh,
    format_enthalpy,
    as_percent_number,
)
from backend.agents.ventilation_airflow.o10_o13_engines import (
    moist_enthalpy_kjkg,
    enthalpy_advantage,
    evaluate_o10,
    evaluate_o12,
    evaluate_o13,
)
from backend.services.ventilation_opportunity_service import (
    get_dashboard,
    evaluate_opportunity,
    ensure_demo_telemetry,
)


class TestFormatters(unittest.TestCase):
    def test_percent_fraction_and_already_percent(self):
        self.assertEqual(format_percent(0.685), "68.5%")
        self.assertEqual(format_percent(68.5), "68.5%")
        self.assertNotEqual(format_percent(68.5), "6850%")
        self.assertEqual(as_percent_number(68.5), 68.5)
        self.assertIsNone(as_percent_number(6850))
        self.assertEqual(format_percent(None), "—")
        self.assertEqual(format_percent(float("nan")), "—")

    def test_cfm_kw_kwh_enthalpy(self):
        self.assertEqual(format_cfm(8200), "8,200 CFM")
        self.assertEqual(format_cfm(6850), "6,850 CFM")
        self.assertEqual(format_cfm(None), "—")
        self.assertEqual(format_kw(3.31), "3.31 kW")
        self.assertEqual(format_kwh(46.3), "46.3 kWh/day")
        self.assertEqual(format_enthalpy(None), "—")
        self.assertEqual(format_enthalpy(8.4), "8.40 kJ/kg")


class TestEnthalpyAndIaq(unittest.TestCase):
    def test_enthalpy_advantage(self):
        h_oa = moist_enthalpy_kjkg(17.5, 52)
        h_ra = moist_enthalpy_kjkg(24.0, 48)
        self.assertIsNotNone(h_oa)
        self.assertIsNotNone(h_ra)
        adv = enthalpy_advantage(h_ra, h_oa)
        self.assertGreater(adv, 0)
        self.assertIsNone(enthalpy_advantage(None, h_oa))

    def test_o12_co2_compliance(self):
        out = evaluate_o12({"co2_ppm": 560, "supply_airflow_cfm": 7800, "occupancy": 68, "damper_percent": 82})
        self.assertTrue(out["available"])
        self.assertEqual(out["iaq_compliance"], "PASS")
        self.assertIsNotNone(out["optimized_airflow_cfm"])

    def test_o12_missing(self):
        out = evaluate_o12({})
        self.assertFalse(out["available"])

    def test_o13_co_safety(self):
        ok = evaluate_o13({"co_ppm": 12.5, "supply_airflow_cfm": 7350, "return_airflow_cfm": 7350})
        self.assertEqual(ok["iaq_compliance"], "PASS")
        alarm = evaluate_o13({"co_ppm": 62, "supply_airflow_cfm": 7350})
        self.assertEqual(alarm["iaq_compliance"], "FAIL")
        self.assertEqual(alarm["recommendation"], "INCREASE_VENTILATION")

    def test_o10_no_defaults(self):
        self.assertFalse(evaluate_o10({})["available"])
        tel = {
            "outdoor_temp_c": 17.5,
            "outdoor_rh_percent": 52,
            "return_temp_c": 24,
            "return_rh_percent": 48,
            "damper_percent": 82,
            "supply_airflow_cfm": 7800,
            "fan_power_kw": 8.4,
            "chiller_power_kw": 42,
        }
        out = evaluate_o10(tel)
        self.assertTrue(out["available"])
        self.assertEqual(out["current_value"], 82.0)
        self.assertGreater(out["optimized_value"], 82.0)
        self.assertLessEqual(out["optimized_value"], 100.0)
        self.assertNotEqual(out["optimized_value"], 6850)
        self.assertIsNotNone(out["enthalpy_advantage_kj_kg"])
        ids = [c["candidate_id"] for c in out["candidates"]]
        self.assertEqual(ids, ["BASELINE", "MODERATE", "OPTIMAL", "AGGRESSIVE"])
        sel = [c for c in out["candidates"] if c["decision"] == "SELECTED_OPTIMAL"][0]
        self.assertEqual(sel["damper_position_pct"], out["optimized_value"])


class TestDashboardApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        db = SessionLocal()
        try:
            ensure_demo_telemetry(db, force=True)
        finally:
            db.close()
        cls.dash = get_dashboard()

    def test_dashboard_shape(self):
        d = self.dash
        self.assertEqual(d["agent"], "ventilation_airflow")
        self.assertIn(d["telemetry"]["state"], ("LIVE", "DEGRADED", "NO DATA", "API ERROR", "STALE", "UNAVAILABLE", "ERROR"))
        self.assertEqual(d["summary"]["total"], 4)
        self.assertEqual(len(d["opportunities"]), 4)
        self.assertEqual(len(d["cards"]), 4)
        self.assertIn("module", d)
        self.assertEqual(d["module"]["name"], "Ventilation & Air Flow Optimizations")
        self.assertEqual([o["opportunityId"] for o in d["opportunities"]], ["O10", "O11", "O12", "O13"])

    def test_energy_aggregation(self):
        s = self.dash["summary"]
        from backend.services.ventilation_opportunity_service import _saving_kw
        known = [_saving_kw(o["energy"]["instantaneousKw"]) for o in self.dash["opportunities"]]
        known = [v for v in known if v is not None]
        if known:
            self.assertAlmostEqual(s["energySavingsKw"], round(sum(known), 2), places=2)

    def test_dcv_kpis(self):
        m = self.dash["module"]
        o12 = next(o for o in self.dash["opportunities"] if o["opportunityId"] == "O12")
        o13 = next(o for o in self.dash["opportunities"] if o["opportunityId"] == "O13")
        from backend.services.ventilation_opportunity_service import _saving_kw
        parts = [_saving_kw((o12.get("energy") or {}).get("instantaneousKw")), _saving_kw((o13.get("energy") or {}).get("instantaneousKw"))]
        known = [v for v in parts if v is not None]
        self.assertEqual(m["dcvKw"], round(sum(known), 2) if known else None)
        self.assertIn("economyKw", m)

    def test_o11_not_404(self):
        r = evaluate_opportunity("O11", persist=False)
        self.assertEqual(r["opportunityId"], "O11")
        self.assertNotEqual(r.get("status"), None)

    def test_iaq_aggregation(self):
        iaq = self.dash["summary"]["iaqCompliancePercent"]
        self.assertIsNotNone(iaq)
        self.assertGreaterEqual(iaq, 0)
        self.assertLessEqual(iaq, 100)

    def test_o10_o13_contracts(self):
        for oid in ("O10", "O11", "O12", "O13"):
            r = evaluate_opportunity(oid, persist=False)
            self.assertEqual(r["opportunityId"], oid)
            self.assertIn("telemetry", r)
            self.assertIn("current", r)
            self.assertIn("optimized", r)
            self.assertIn("energy", r)
            self.assertIsNotNone(r["telemetry"]["state"])
            if oid == "O10" and r.get("current_value") is not None:
                self.assertGreater(r["current_value"], 0)
                self.assertEqual(r.get("unit"), "%")
            if oid == "O11" and r.get("current_value") is not None:
                self.assertGreater(r["current_value"], 10)
            if oid == "O12":
                self.assertTrue("optimized_airflow_cfm" in r)

    def test_unknown_opportunity(self):
        with self.assertRaises(ValueError):
            evaluate_opportunity("O99")

    def test_stale_telemetry_state(self):
        init_db()
        db = SessionLocal()
        try:
            row = db.query(HvacTelemetryDB).order_by(HvacTelemetryDB.id.desc()).first()
            if row:
                row.timestamp = datetime.utcnow() - timedelta(seconds=90)
                db.commit()
            r = evaluate_opportunity("O11", persist=False, db=db)
            self.assertEqual(r["telemetry"]["state"], "STALE")
            row.timestamp = datetime.utcnow()
            db.commit()
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
