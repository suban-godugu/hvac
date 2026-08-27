"""Stage F: Rule Engine checklist, write choke, Safe RL gate, audit."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

os.environ["HVAC_ENV"] = "development"
os.environ["HVAC_START_CONTROL_WORKER"] = "0"
os.environ["HVAC_ALLOW_CREATE_ALL"] = "1"
os.environ["HVAC_SAFE_MODE"] = "0"
os.environ["HVAC_BMS_WRITE_ENABLED"] = "0"
os.environ["HVAC_USE_SIMULATION"] = "0"
os.environ["HVAC_PLANT_MODE_PERSIST"] = "0"
os.environ["HVAC_EMERGENCY_STOP"] = "0"
os.environ["HVAC_MANUAL_OVERRIDE"] = "0"
os.environ["HVAC_RULE_ENGINE_STRICT"] = "0"
os.environ["HVAC_SCHEDULE_START_HOUR"] = "0"
os.environ["HVAC_SCHEDULE_END_HOUR"] = "24"


def _base_ctx(**kwargs):
    ctx = {
        "action": "EVALUATE",
        "point_id": "ZONE-01.cooling_setpoint",
        "old_value": 24.0,
        "new_value": 24.0,
        "opportunity_id": "O2",
        "zone_id": "ZONE-01",
        "normalized": {"Indoor_Temp": 22.5, "Occupancy": 0.5, "quality": "GOOD"},
        "decision": "OPTIMIZE",
        "safety": {"status": "PASS", "passed": True},
        "confidence": 0.9,
        "strict": False,
        "skip_audit": True,
        "schedule_hour": 12,
    }
    ctx.update(kwargs)
    return ctx


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("HVAC_ALLOW_CREATE_ALL", "1")
    monkeypatch.setenv("HVAC_BMS_WRITE_ENABLED", "0")
    monkeypatch.setenv("HVAC_SAFE_MODE", "0")
    monkeypatch.setenv("HVAC_EMERGENCY_STOP", "0")
    monkeypatch.setenv("HVAC_RULE_ENGINE_STRICT", "0")
    monkeypatch.setenv("HVAC_SCHEDULE_START_HOUR", "0")
    monkeypatch.setenv("HVAC_SCHEDULE_END_HOUR", "24")
    from backend.services.timeseries_buffer import clear as clear_buffer
    from database.session import init_db

    init_db()
    from database.session import SessionLocal
    from database.models_platform import ControlAuditLogDB, ControlCommandDB, SafeRlDecisionDB
    from backend.services.platform_ops_service import set_safe_mode

    db = SessionLocal()
    try:
        db.query(ControlAuditLogDB).filter(
            ControlAuditLogDB.action.in_(["RULE_ENGINE_APPROVED", "RULE_ENGINE_REJECTED"])
        ).delete(synchronize_session=False)
        db.query(SafeRlDecisionDB).delete()
        db.query(ControlCommandDB).delete()
        db.commit()
    finally:
        db.close()
    clear_buffer()
    set_safe_mode(False)
    from backend.main import app

    return TestClient(app)


def test_safe_mode_rejects(monkeypatch):
    monkeypatch.setattr("backend.rules.checks.is_safe_mode", lambda: True)
    from backend.rules.engine import evaluate

    r = evaluate(_base_ctx(skip_audit=True), audit=False)
    assert r["verdict"] == "REJECTED"
    assert r["code"] == "R01_SAFE_MODE"


def test_rate_limit_rejects():
    from backend.rules.engine import evaluate

    r = evaluate(
        _base_ctx(old_value=24.0, new_value=25.5, point_id="ZONE-01.cooling_setpoint", skip_audit=True),
        audit=False,
    )
    assert r["verdict"] == "REJECTED"
    assert r["code"] == "R09_RATE_LIMIT"


def test_equipment_limits_sat_rejects():
    from backend.rules.engine import evaluate

    r = evaluate(
        _base_ctx(
            point_id="AHU-01-SAT-SP",
            old_value=18.0,
            new_value=18.7,
            opportunity_id="O3",
            skip_audit=True,
        ),
        audit=False,
    )
    assert r["verdict"] == "REJECTED"
    assert r["code"] == "R06_EQUIPMENT_LIMITS"


def test_schedule_outside_hours_rejects(monkeypatch):
    monkeypatch.setenv("HVAC_SCHEDULE_START_HOUR", "8")
    monkeypatch.setenv("HVAC_SCHEDULE_END_HOUR", "18")
    from backend.rules.engine import evaluate

    r = evaluate(
        _base_ctx(
            schedule_hour=3,
            old_value=24.0,
            new_value=24.3,
            normalized={"Indoor_Temp": 22.5, "Occupancy": 0.0, "quality": "GOOD"},
            skip_audit=True,
        ),
        audit=False,
    )
    assert r["verdict"] == "REJECTED"
    assert r["code"] == "R07_SCHEDULE"


def test_approve_hold_delta():
    from backend.rules.engine import evaluate

    r = evaluate(_base_ctx(old_value=24.0, new_value=24.0, skip_audit=True), audit=False)
    assert r["verdict"] == "APPROVED"
    assert len(r["checks"]) == 10
    assert all(c["result"] == "PASS" for c in r["checks"])


def test_api_evaluate_and_audit(client: TestClient):
    r = client.post(
        "/api/platform/rules/evaluate",
        json={
            "point_id": "ZONE-01.cooling_setpoint",
            "old_value": 24.0,
            "new_value": 24.0,
            "opportunity_id": "O2",
            "zone_id": "ZONE-01",
            "action": "EVALUATE",
            "schedule_hour": 12,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] in ("APPROVED", "REJECTED")
    assert "checks" in body
    assert len(body["checks"]) == 10

    audit = client.get("/api/platform/rules/audit?limit=5")
    assert audit.status_code == 200
    assert audit.json()["count"] >= 1


def test_write_point_blocks_without_approved(monkeypatch):
    from backend.bms import command_writer as cw

    executed = []

    class FakeAdapter:
        def execute_write(self, *a, **k):
            executed.append(True)
            return MagicMock(success=True, code="OK", message="ok")

    monkeypatch.setattr("backend.bms.connection_manager.is_simulation_mode", lambda: False)
    monkeypatch.setattr(cw, "physical_writes_allowed", lambda: True)
    monkeypatch.setattr("backend.services.hvac_safety_contract.is_safe_mode", lambda: False)
    monkeypatch.setattr(
        "backend.bms.connection_manager.get_connection_manager",
        lambda: MagicMock(adapter=lambda: FakeAdapter()),
    )
    monkeypatch.setattr(cw, "resolve_write_target", lambda pid: (pid, None, "WRITE"))

    monkeypatch.setattr(
        "backend.rules.engine.evaluate",
        lambda *a, **k: {
            "verdict": "REJECTED",
            "code": "R09_RATE_LIMIT",
            "reason": "delta too large",
            "checks": [],
        },
    )

    out = cw.write_point("ZONE-01.cooling_setpoint", 25.5)
    assert out.success is False
    assert out.code == "R09_RATE_LIMIT"
    assert executed == []


def test_write_point_allows_when_approved(monkeypatch):
    from backend.bms import command_writer as cw
    from backend.bms.base import WriteOutcome, utc_now

    executed = []

    class FakeAdapter:
        def execute_write(self, ident, value, priority):
            executed.append((ident, value))
            return WriteOutcome(
                success=True,
                code="OK",
                message="written",
                point_id=ident,
                value=value,
                timestamp=utc_now().isoformat(),
            )

    monkeypatch.setattr("backend.bms.connection_manager.is_simulation_mode", lambda: False)
    monkeypatch.setattr(cw, "physical_writes_allowed", lambda: True)
    monkeypatch.setattr("backend.services.hvac_safety_contract.is_safe_mode", lambda: False)
    monkeypatch.setattr(
        "backend.bms.connection_manager.get_connection_manager",
        lambda: MagicMock(adapter=lambda: FakeAdapter()),
    )
    monkeypatch.setattr(cw, "resolve_write_target", lambda pid: (pid, None, "WRITE"))
    monkeypatch.setattr(
        "backend.rules.engine.evaluate",
        lambda *a, **k: {"verdict": "APPROVED", "code": "APPROVED", "reason": "ok", "checks": []},
    )

    out = cw.write_point("ZONE-01.cooling_setpoint", 24.2)
    assert out.success is True
    assert executed == [("ZONE-01.cooling_setpoint", 24.2)]


def test_safe_rl_rejected_no_commands(client: TestClient, monkeypatch):
    from backend.ai.safe_rl import service as svc

    def fake_state(*_a, **_k):
        return {
            "zone_id": "ZONE-01",
            "building_id": "bldg-corp-hq-01",
            "telemetry_ok": True,
            "safe_mode": False,
            "normalized": {"Indoor_Temp": 22.5, "Occupancy": 0.5},
            "candidates": [],
            "rls": {},
            "lstm": {},
            "comfort_band": {"min_c": 21, "max_c": 24},
            "tariff_usd_kwh": 0.14,
            "engineering_limits": {},
        }

    winner = {
        "action_id": "zone_sp_up_0.5",
        "mapped_opportunity": "O2",
        "point_id": "ZONE-01.cooling_setpoint",
        "old_value": 24.0,
        "new_value": 24.5,
        "score": 1.0,
        "feasible": True,
    }

    def fake_rank(_state):
        return {
            "winner": winner,
            "rejected_actions": [],
            "all_rejected": False,
            "constraints": [],
            "confidence": 0.8,
        }

    monkeypatch.setattr(svc, "build_decision_state", fake_state)
    monkeypatch.setattr(svc, "rank_candidates", fake_rank)
    monkeypatch.setattr("backend.ai.safe_rl.service.is_safe_mode", lambda: False)
    monkeypatch.setattr(
        "backend.rules.engine.evaluate",
        lambda *a, **k: {
            "verdict": "REJECTED",
            "code": "R06_EQUIPMENT_LIMITS",
            "reason": "blocked",
            "checks": [],
        },
    )

    r = client.post("/api/platform/ai/safe-rl/recommend", json={"zone_id": "ZONE-01"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "BLOCKED"
    assert body["mapped_command_ids"] == []
    assert body["wrote_setpoints"] is False

    from database.session import SessionLocal
    from database.models_platform import ControlCommandDB

    db = SessionLocal()
    try:
        assert db.query(ControlCommandDB).count() == 0
    finally:
        db.close()
