"""End-to-end O17–O20 module: dashboard → agent → decision → action → audit."""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from backend.services.hvac_operations_maintenance_module import get_opportunities, get_opportunity, canonical_oid
from backend.services.operations_maintenance_opportunity_service import record_action, list_audit, ensure_om_demo
from database.session import init_db, SessionLocal


class TestOmIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        db = SessionLocal()
        try:
            ensure_om_demo(db, force=True)
        finally:
            db.close()

    def test_module_excludes_other_ids(self):
        self.assertIsNone(canonical_oid("O10"))
        self.assertIsNone(canonical_oid("O11"))
        dash = get_opportunities()
        self.assertEqual([o["id"] for o in dash["opportunities"]], ["O17", "O18", "O19", "O20"])

    def test_each_opportunity_pipeline(self):
        for oid in ("O17", "O18", "O19", "O20"):
            body = get_opportunity(oid)
            self.assertEqual(body["id"], oid)
            self.assertIn(body["supervisory"]["decision"], (
                "OPTIMIZE", "MONITOR", "REVIEW_REQUIRED", "SAFE_HOLD", "WAIT_FOR_TELEMETRY", "BLOCK", "HOLD",
                "MAINTENANCE_REQUIRED", "URGENT_MAINTENANCE",
            ))
            self.assertIsNotNone(body["recommendation"])
            record_action(oid, body["dispatch"]["actionType"] or "NOTE", {"test": True})
            audit = list_audit(oid, 5)
            self.assertGreaterEqual(len(audit), 1)


if __name__ == "__main__":
    unittest.main()
