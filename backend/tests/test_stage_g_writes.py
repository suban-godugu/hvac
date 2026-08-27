"""Stage G: controlled one-point writes — prereqs, allowlist, approve→apply→verify→rollback."""
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
os.environ["HVAC_BMS_LAB"] = "1"
os.environ["HVAC_BMS_PROTOCOL"] = "bacnet"
os.environ["HVAC_PLANT_MODE_PERSIST"] = "0"
os.environ["HVAC_EMERGENCY_STOP"] = "0"
os.environ["HVAC_MANUAL_OVERRIDE"] = "0"
os.environ["HVAC_RULE_ENGINE_STRICT"] = "0"
os.environ["HVAC_SCHEDULE_START_HOUR"] = "0"
os.environ["HVAC_SCHEDULE_END_HOUR"] = "24"
os.environ["HVAC_STAGE_G_ENFORCE"] = "1"
os.environ["HVAC_STAGE_G_WRITABLE_POINTS"] = "ZONE-01.cooling_setpoint"
os.environ["HVAC_STAGE_G_AUTO_ROLLBACK"] = "1"
os.environ["HVAC_REQUIRE_APPROVAL"] = "1"


POINT = "ZONE-01.cooling_setpoint"


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("HVAC_BMS_LAB", "1")
    monkeypatch.setenv("HVAC_BMS_WRITE_ENABLED", "0")
    monkeypatch.setenv("HVAC_PLANT_MODE_PERSIST", "1")
    monkeypatch.setenv("HVAC_USE_SIMULATION", "0")
    monkeypatch.setenv("HVAC_SAFE_MODE", "0")
    monkeypatch.setenv("HVAC_STAGE_G_ENFORCE", "1")
    monkeypatch.setenv("HVAC_STAGE_G_WRITABLE_POINTS", POINT)
    monkeypatch.setenv("HVAC_STAGE_G_AUTO_ROLLBACK", "1")
    monkeypatch.setenv("HVAC_RULE_ENGINE_STRICT", "0")
    monkeypatch.setenv("HVAC_SCHEDULE_START_HOUR", "0")
    monkeypatch.setenv("HVAC_SCHEDULE_END_HOUR", "24")
    monkeypatch.setenv("HVAC_EMERGENCY_STOP", "0")
    monkeypatch.setenv("HVAC_MANUAL_OVERRIDE", "0")

    from backend.agents.scheduling_supervisory.gateway import reset_bms_gateway
    from backend.bms.connection_manager import reset_connection_manager
    from backend.services.timeseries_buffer import clear as clear_buffer
    from database.session import init_db

    init_db()
    from database.session import SessionLocal
    from database.models_bms import BmsConnectionDB, BmsDeviceDB, BmsPointDB, EquipmentPointMappingDB
    from database.models_platform import (
        CanonicalTelemetryDB,
        ControlCommandDB,
        HvacApprovalDB,
        PlatformSettingDB,
        SafeRlDecisionDB,
    )
    from backend.services.platform_ops_service import set_plant_mode, set_safe_mode

    db = SessionLocal()
    try:
        db.query(EquipmentPointMappingDB).delete()
        db.query(BmsPointDB).delete()
        db.query(BmsDeviceDB).delete()
        db.query(BmsConnectionDB).delete()
        db.query(CanonicalTelemetryDB).delete()
        db.query(ControlCommandDB).delete()
        db.query(HvacApprovalDB).delete()
        db.query(SafeRlDecisionDB).delete()
        db.query(PlatformSettingDB).filter_by(key="PLANT_MODE").delete()
        db.commit()
    finally:
        db.close()
    clear_buffer()
    reset_connection_manager()
    reset_bms_gateway()
    set_safe_mode(False)
    set_plant_mode("DATASET")
    from backend.main import app

    with TestClient(app) as client:
        from backend.bms.telemetry_reader import stop_reader
        from backend.bms.simulation_telemetry import stop_simulation_telemetry

        stop_reader()
        stop_simulation_telemetry()
        yield client


def _commission_writable(client: TestClient) -> None:
    from backend.bms.lab_bacnet_gateway import stage_a_mapping_targets
    from backend.bms.connection_manager import reset_connection_manager
    from backend.services.platform_ops_service import set_plant_mode

    set_plant_mode("LIVE_BMS")
    reset_connection_manager()

    res = client.post(
        "/api/platform/bms/connect",
        json={"protocol": "bacnet", "host": "127.0.0.1", "port": 47808},
    )
    assert res.json().get("connected") is True, res.json()
    client.post("/api/platform/bms/discover")

    devices = client.get("/api/platform/bms/devices").json()["devices"]
    by_ident = {}
    for d in devices:
        pts = client.get(f"/api/platform/bms/devices/{d['id']}/points").json()["points"]
        for p in pts:
            by_ident[p["point_identifier"]] = p["id"]

    for target in stage_a_mapping_targets():
        bms_id = by_ident.get(target["point_identifier"])
        assert bms_id, target["point_identifier"]
        writable = target["canonical_point"] in ("cooling_setpoint", "sat_setpoint")
        mapped = client.put(
            "/api/platform/bms/mappings",
            json={
                "equipment_id": target["equipment_id"],
                "canonical_point": target["canonical_point"],
                "bms_point_id": bms_id,
                "direction": "READ_WRITE" if writable else "READ",
            },
        )
        assert mapped.status_code == 200, mapped.text

    from backend.bms.telemetry_reader import poll_once

    poll_once(include_unmapped=False)


def _propose_cmd(point_id: str = POINT, old_v: float = 24.0, new_v: float = 24.5) -> str:
    from backend.agents.runtime.command import propose
    from backend.agents.runtime.contracts import CommandContract

    row = propose(
        CommandContract(
            opportunity="O2",
            building="bldg-corp-hq-01",
            equipment="ZONE-01",
            point=point_id,
            old_value=old_v,
            new_value=new_v,
            reason="STAGE_G_TEST",
            engine_version="test",
            config_version="test",
            safety_gates=[],
            requested_by="pytest",
        )
    )
    return row["command_id"]


def test_prereqs_fail_safe_mode(client: TestClient, monkeypatch):
    from backend.services.platform_ops_service import set_safe_mode

    _commission_writable(client)
    set_safe_mode(True)
    body = client.get(f"/api/platform/bms/stage-g/status?point_id={POINT}").json()
    assert body["ok"] is False
    names = {c["name"]: c["ok"] for c in body["checks"]}
    assert names["NOT_SAFE_MODE"] is False
    set_safe_mode(False)


def test_prereqs_fail_no_writable_mapping(client: TestClient):
    from backend.services.platform_ops_service import set_plant_mode
    from backend.services.canonical_telemetry_service import record_point

    set_plant_mode("LIVE_BMS")
    record_point(POINT, 24.0, "degC", "LIVE_BMS", "GOOD", equipment_id="ZONE-01")
    body = client.get(f"/api/platform/bms/stage-g/status?point_id={POINT}").json()
    assert body["ok"] is False
    names = {c["name"]: c["ok"] for c in body["checks"]}
    assert names["MAPPING_WRITABLE"] is False


def test_prereqs_fail_not_armed(client: TestClient, monkeypatch):
    monkeypatch.setenv("HVAC_BMS_WRITE_ENABLED", "1")
    _commission_writable(client)
    body = client.get(f"/api/platform/bms/stage-g/status?point_id={POINT}").json()
    names = {c["name"]: c["ok"] for c in body["checks"]}
    assert names["CONNECTION_WRITE_ARMED"] is False
    assert body.get("ok_to_enable") is True
    assert body["ok"] is False


def test_allowlist_reject(monkeypatch):
    from backend.bms import command_writer as cw
    from backend.bms.base import WriteOutcome, utc_now

    monkeypatch.setenv("HVAC_STAGE_G_ENFORCE", "1")
    monkeypatch.setenv("HVAC_STAGE_G_WRITABLE_POINTS", POINT)
    monkeypatch.setattr("backend.bms.connection_manager.is_simulation_mode", lambda: False)
    monkeypatch.setattr(cw, "physical_writes_allowed", lambda: True)
    monkeypatch.setattr("backend.services.hvac_safety_contract.is_safe_mode", lambda: False)
    monkeypatch.setattr(
        "backend.bms.connection_manager.get_connection_manager",
        lambda: MagicMock(adapter=lambda: MagicMock(execute_write=lambda *a, **k: WriteOutcome(True, "OK", "ok", a[0], a[1], utc_now().isoformat()))),
    )
    monkeypatch.setattr(cw, "resolve_write_target", lambda pid: (pid, None, "WRITE"))
    monkeypatch.setattr(
        "backend.rules.engine.evaluate",
        lambda *a, **k: {"verdict": "APPROVED", "code": "APPROVED", "reason": "ok", "checks": []},
    )

    out = cw.write_point("AHU-01.sat_setpoint", 13.0)
    assert out.success is False
    assert out.code == "STAGE_G_POINT_NOT_ALLOWED"


def test_single_point_batch_reject(monkeypatch):
    from backend.bms import command_writer as cw

    monkeypatch.setenv("HVAC_STAGE_G_ENFORCE", "1")
    outs = cw.write_points(
        [
            {"point_id": POINT, "value": 24.5},
            {"point_id": "AHU-01.sat_setpoint", "value": 13.0},
        ]
    )
    assert len(outs) == 2
    assert all(o.code == "STAGE_G_SINGLE_POINT_ONLY" for o in outs)


def test_approve_apply_verify_rollback_lab(client: TestClient, monkeypatch):
    monkeypatch.setenv("HVAC_BMS_WRITE_ENABLED", "1")
    monkeypatch.setenv("HVAC_STAGE_G_AUTO_ROLLBACK", "0")
    _commission_writable(client)

    enable = client.post("/api/platform/bms/write-enable", json={"confirm": True})
    assert enable.status_code == 200, enable.text

    gate = client.get(f"/api/platform/bms/stage-g/status?point_id={POINT}").json()
    assert gate["ok"] is True, gate

    cid = _propose_cmd(old_v=24.0, new_v=24.5)
    ap = client.post(f"/api/platform/commands/{cid}/approve")
    assert ap.status_code == 200, ap.text
    assert ap.json()["command"]["status"] == "APPROVED"

    applied = client.post(f"/api/platform/commands/{cid}/apply")
    assert applied.status_code == 200, applied.text
    assert applied.json()["status"] == "APPLIED"

    verified = client.post(f"/api/platform/commands/{cid}/verify")
    assert verified.status_code == 200, verified.text
    assert verified.json()["status"] == "VERIFIED"

    from backend.agents.runtime.command import get_command

    cmd = get_command(cid)
    assert cmd and (cmd.get("payload_json") or {}).get("verify", {}).get("ok") is True

    rolled = client.post(f"/api/platform/commands/{cid}/rollback")
    assert rolled.status_code == 200, rolled.text
    assert rolled.json()["status"] == "ROLLED_BACK"


def test_safe_rl_recommend_never_writes(client: TestClient, monkeypatch):
    from backend.ai.safe_rl import service as svc

    executed = []

    class FakeAdapter:
        def execute_write(self, ident, value, priority):
            executed.append((ident, value))
            raise AssertionError("recommend must not write")

    monkeypatch.setattr(
        "backend.bms.connection_manager.get_connection_manager",
        lambda: MagicMock(adapter=lambda: FakeAdapter(), is_production_connected=lambda: True),
    )

    def fake_state(*_a, **_k):
        return {
            "zone_id": "ZONE-01",
            "building_id": "bldg-corp-hq-01",
            "telemetry_ok": True,
            "safe_mode": False,
            "normalized": {"Indoor_Temp": 22.5, "Occupancy": 0.5, "quality": "GOOD"},
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
        "point_id": POINT,
        "old_value": 24.0,
        "new_value": 24.5,
        "score": 1.0,
        "feasible": True,
    }

    monkeypatch.setattr(svc, "build_decision_state", fake_state)
    monkeypatch.setattr(
        svc,
        "rank_candidates",
        lambda _s: {
            "winner": winner,
            "rejected_actions": [],
            "all_rejected": False,
            "constraints": [],
            "confidence": 0.8,
        },
    )
    monkeypatch.setattr("backend.ai.safe_rl.service.is_safe_mode", lambda: False)
    monkeypatch.setattr(
        "backend.rules.engine.evaluate",
        lambda *a, **k: {"verdict": "APPROVED", "code": "APPROVED", "reason": "ok", "checks": []},
    )

    r = client.post("/api/platform/ai/safe-rl/recommend", json={"zone_id": "ZONE-01"})
    assert r.status_code == 200
    body = r.json()
    assert body["wrote_setpoints"] is False
    assert executed == []


def test_auto_rollback_on_verify_fail(client: TestClient, monkeypatch):
    monkeypatch.setenv("HVAC_BMS_WRITE_ENABLED", "1")
    monkeypatch.setenv("HVAC_STAGE_G_AUTO_ROLLBACK", "1")
    _commission_writable(client)
    assert client.post("/api/platform/bms/write-enable", json={"confirm": True}).status_code == 200

    cid = _propose_cmd(old_v=24.0, new_v=24.5)
    assert client.post(f"/api/platform/commands/{cid}/approve").status_code == 200
    assert client.post(f"/api/platform/commands/{cid}/apply").status_code == 200

    # Force verify to read a wrong value
    from backend.bms.connection_manager import get_connection_manager
    from backend.bms.base import PointReading, utc_now

    adapter = get_connection_manager().adapter()
    assert adapter is not None
    orig = adapter.read_point

    def bad_read(pid):
        return PointReading(
            point_id=pid,
            value=99.0,
            unit="degC",
            quality="GOOD",
            timestamp=utc_now().isoformat(),
            source="LIVE_BMS",
        )

    adapter.read_point = bad_read  # type: ignore[method-assign]
    try:
        res = client.post(f"/api/platform/commands/{cid}/verify")
        assert res.status_code == 409
        from backend.agents.runtime.command import get_command

        cmd = get_command(cid)
        assert cmd is not None
        assert cmd["status"] == "ROLLED_BACK"
    finally:
        adapter.read_point = orig  # type: ignore[method-assign]
