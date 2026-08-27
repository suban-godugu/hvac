"""Stage H: closed loop — RLS feedback, LSTM version bump, Safe RL reward, edge, watchdogs."""
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
os.environ["HVAC_PLANT_MODE_PERSIST"] = "0"
os.environ["HVAC_EMERGENCY_STOP"] = "0"
os.environ["HVAC_MANUAL_OVERRIDE"] = "0"
os.environ["HVAC_RULE_ENGINE_STRICT"] = "0"
os.environ["HVAC_SCHEDULE_START_HOUR"] = "0"
os.environ["HVAC_SCHEDULE_END_HOUR"] = "24"
os.environ["HVAC_STAGE_G_ENFORCE"] = "1"
os.environ["HVAC_STAGE_G_WRITABLE_POINTS"] = "ZONE-01.cooling_setpoint"
os.environ["HVAC_STAGE_G_AUTO_ROLLBACK"] = "0"
os.environ["HVAC_RLS_POST_WRITE_LAG_SECONDS"] = "0"
os.environ["HVAC_RLS_POST_WRITE_LOOKBACK"] = "30"
os.environ["HVAC_EDGE_MODE"] = "1"
os.environ["HVAC_CLOUD_URL"] = "http://127.0.0.1:9/unreachable"
os.environ["HVAC_REQUIRE_APPROVAL"] = "1"

POINT = "ZONE-01.cooling_setpoint"


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("HVAC_ALLOW_CREATE_ALL", "1")
    monkeypatch.setenv("HVAC_BMS_LAB", "1")
    monkeypatch.setenv("HVAC_PLANT_MODE_PERSIST", "1")
    monkeypatch.setenv("HVAC_BMS_WRITE_ENABLED", "0")
    monkeypatch.setenv("HVAC_SAFE_MODE", "0")
    monkeypatch.setenv("HVAC_RLS_POST_WRITE_LAG_SECONDS", "0")
    monkeypatch.setenv("HVAC_STAGE_G_AUTO_ROLLBACK", "0")
    monkeypatch.setenv("HVAC_EDGE_MODE", "1")
    monkeypatch.setenv("HVAC_CLOUD_URL", "http://127.0.0.1:9/unreachable")
    monkeypatch.setenv("HVAC_RULE_ENGINE_STRICT", "0")
    monkeypatch.setenv("HVAC_SCHEDULE_START_HOUR", "0")
    monkeypatch.setenv("HVAC_SCHEDULE_END_HOUR", "24")

    from backend.agents.scheduling_supervisory.gateway import reset_bms_gateway
    from backend.bms.connection_manager import reset_connection_manager
    from backend.services.timeseries_buffer import clear as clear_buffer
    from backend.workers.watchdog import reset_beats_for_tests
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
    from database.models_ml import MLModelRegistryDB, MLModelMetricsDB, MLTrainingRunDB
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
        db.query(MLModelMetricsDB).delete()
        db.query(MLTrainingRunDB).delete()
        db.query(MLModelRegistryDB).delete()
        db.query(PlatformSettingDB).filter(
            PlatformSettingDB.key.in_(["PLANT_MODE", "SAFE_RL_OFFLINE_WEIGHTS"])
        ).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()
    clear_buffer()
    reset_connection_manager()
    reset_bms_gateway()
    reset_beats_for_tests()
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
    assert client.post(
        "/api/platform/bms/connect",
        json={"protocol": "bacnet", "host": "127.0.0.1", "port": 47808},
    ).json().get("connected") is True
    client.post("/api/platform/bms/discover")
    devices = client.get("/api/platform/bms/devices").json()["devices"]
    by_ident = {}
    for d in devices:
        pts = client.get(f"/api/platform/bms/devices/{d['id']}/points").json()["points"]
        for p in pts:
            by_ident[p["point_identifier"]] = p["id"]
    for target in stage_a_mapping_targets():
        bms_id = by_ident[target["point_identifier"]]
        writable = target["canonical_point"] in ("cooling_setpoint", "sat_setpoint")
        assert (
            client.put(
                "/api/platform/bms/mappings",
                json={
                    "equipment_id": target["equipment_id"],
                    "canonical_point": target["canonical_point"],
                    "bms_point_id": bms_id,
                    "direction": "READ_WRITE" if writable else "READ",
                },
            ).status_code
            == 200
        )
    from backend.bms.telemetry_reader import poll_once

    poll_once(include_unmapped=False)


def _propose_cmd(old_v: float = 24.0, new_v: float = 24.5) -> str:
    from backend.agents.runtime.command import propose
    from backend.agents.runtime.contracts import CommandContract

    row = propose(
        CommandContract(
            opportunity="O2",
            building="bldg-corp-hq-01",
            equipment="ZONE-01",
            point=POINT,
            old_value=old_v,
            new_value=new_v,
            reason="STAGE_H_TEST",
            requested_by="pytest",
        )
    )
    return row["command_id"]


def test_h1_verify_triggers_rls_feedback(client: TestClient, monkeypatch):
    monkeypatch.setenv("HVAC_BMS_WRITE_ENABLED", "1")
    monkeypatch.setenv("HVAC_RLS_POST_WRITE_LAG_SECONDS", "0")
    called = []

    def fake_feedback(command_id, *, zone_id, building_id=None):
        called.append({"command_id": command_id, "zone_id": zone_id, "building_id": building_id})
        return {"ok": True, "updated": 1, "wrote_setpoints": False}

    monkeypatch.setattr("backend.ai.rls.feedback.run_feedback", fake_feedback)
    monkeypatch.setattr("backend.ai.safe_rl.outcome.measure_after_verify", lambda *_a, **_k: {"ok": True})

    _commission_writable(client)
    assert client.post("/api/platform/bms/write-enable", json={"confirm": True}).status_code == 200
    cid = _propose_cmd()
    assert client.post(f"/api/platform/commands/{cid}/approve").status_code == 200
    assert client.post(f"/api/platform/commands/{cid}/apply").status_code == 200
    assert client.post(f"/api/platform/commands/{cid}/verify").status_code == 200
    assert len(called) >= 1
    assert called[0].get("zone_id") == "ZONE-01"


def test_h1_verify_fail_no_rls(client: TestClient, monkeypatch):
    monkeypatch.setenv("HVAC_BMS_WRITE_ENABLED", "1")
    monkeypatch.setenv("HVAC_RLS_POST_WRITE_LAG_SECONDS", "0")
    called = []
    monkeypatch.setattr(
        "backend.ai.rls.feedback.run_feedback",
        lambda *a, **k: called.append({"args": a, **k}) or {"ok": True},
    )
    _commission_writable(client)
    assert client.post("/api/platform/bms/write-enable", json={"confirm": True}).status_code == 200
    cid = _propose_cmd(old_v=24.0, new_v=24.5)
    assert client.post(f"/api/platform/commands/{cid}/approve").status_code == 200
    assert client.post(f"/api/platform/commands/{cid}/apply").status_code == 200
    called.clear()

    from backend.bms.connection_manager import get_connection_manager
    from backend.bms.base import PointReading, utc_now

    adapter = get_connection_manager().adapter()
    orig = adapter.read_point

    def bad_read(pid):
        return PointReading(pid, 99.0, "degC", "GOOD", utc_now().isoformat(), "LIVE_BMS")

    adapter.read_point = bad_read  # type: ignore
    try:
        assert client.post(f"/api/platform/commands/{cid}/verify").status_code == 409
        assert called == []
    finally:
        adapter.read_point = orig  # type: ignore


def test_h2_version_bump_and_mae_keeps_prior(monkeypatch):
    from database.session import init_db, SessionLocal
    from database.models_ml import MLModelRegistryDB

    init_db()
    db = SessionLocal()
    try:
        db.query(MLModelRegistryDB).delete()
        db.add(
            MLModelRegistryDB(
                id="mdl-lstm-zone-temp-v1__v1",
                opportunity_id="LSTM",
                agent_id="forecast",
                model_type="LSTM",
                model_version="v1",
                features_json={"model_key": "mdl-lstm-zone-temp-v1"},
                target_json={"target": "zone_temp", "model_key": "mdl-lstm-zone-temp-v1"},
                artifact_path="/tmp/old.pkl",
                status="MODEL_READY",
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )
        db.commit()
    finally:
        db.close()

    from backend.ai.lstm import train as train_mod

    # Failed gate — must not promote
    promoted = train_mod._register_version(
        model_id="mdl-lstm-zone-temp-v1__v_fail",
        model_key="mdl-lstm-zone-temp-v1",
        target="zone_temp",
        version="v_fail",
        status="MODEL_NOT_READY",
        artifact_path="/tmp/fail.pkl",
        features={"model_key": "mdl-lstm-zone-temp-v1"},
        metrics={"val_mae": 99.0, "gate_mae": 1.5},
    )
    assert promoted is False

    db = SessionLocal()
    try:
        ready = (
            db.query(MLModelRegistryDB)
            .filter_by(status="MODEL_READY")
            .order_by(MLModelRegistryDB.created_at.desc())
            .all()
        )
        assert any(r.id == "mdl-lstm-zone-temp-v1__v1" for r in ready)
    finally:
        db.close()

    # Success — supersede prior
    ok = train_mod._register_version(
        model_id="mdl-lstm-zone-temp-v1__v2",
        model_key="mdl-lstm-zone-temp-v1",
        target="zone_temp",
        version="v2",
        status="MODEL_READY",
        artifact_path="/tmp/new.pkl",
        features={"model_key": "mdl-lstm-zone-temp-v1"},
        metrics={"val_mae": 0.5, "gate_mae": 1.5},
    )
    assert ok is True
    from backend.ai.lstm.status import latest_ready_row, list_versions

    row = latest_ready_row("zone_temp")
    assert row is not None
    assert row.id == "mdl-lstm-zone-temp-v1__v2"
    versions = list_versions(10)
    assert versions["count"] >= 2


def test_h3_reward_and_offline_weights(client: TestClient, monkeypatch):
    from database.session import SessionLocal
    from database.models_platform import SafeRlDecisionDB
    from backend.ai.safe_rl.persist import save_decision
    from backend.ai.safe_rl.outcome import measure_after_verify
    from backend.ai.safe_rl.offline import load_offline_blob, save_offline_blob, update_weights_from_log

    save_offline_blob(
        {
            "weights": {"energy": 1.0, "comfort": 2.0, "limit": 0.5, "forecast": 0.3},
            "action_priors": {},
            "n_updates": 0,
        }
    )
    cid = _propose_cmd()
    from backend.agents.runtime.command import set_status

    set_status(cid, "VERIFIED")
    dec = save_decision(
        zone_id="ZONE-01",
        building_id="bldg-corp-hq-01",
        status="PROPOSED",
        winner={"action_id": "zone_sp_up_0.5", "score": 1.0},
        rejected_actions=[],
        constraints=[],
        state_snapshot={"normalized": {"Indoor_Temp": 22.5, "HVAC_Power": 100.0}},
        mapped_commands=[{"command_id": cid}],
        confidence=0.8,
    )
    out = measure_after_verify(cid)
    assert out.get("ok") is True
    assert out.get("realized_reward") is not None

    db = SessionLocal()
    try:
        row = db.query(SafeRlDecisionDB).filter_by(id=dec["decision_id"]).first()
        assert row is not None
        assert row.realized_reward is not None
        assert row.command_id == cid
    finally:
        db.close()

    upd = update_weights_from_log(limit=10)
    assert upd.get("updated") is True
    blob = load_offline_blob()
    assert blob["n_updates"] >= 1
    assert "zone_sp_up_0.5" in (blob.get("action_priors") or {})


def test_h3_recommend_never_writes(client: TestClient, monkeypatch):
    from backend.ai.safe_rl import service as svc

    executed = []

    class FakeAdapter:
        def execute_write(self, *a, **k):
            executed.append(a)
            raise AssertionError("must not write")

    monkeypatch.setattr(
        "backend.bms.connection_manager.get_connection_manager",
        lambda: MagicMock(adapter=lambda: FakeAdapter(), is_production_connected=lambda: True),
    )
    monkeypatch.setattr(
        svc,
        "build_decision_state",
        lambda *_a, **_k: {
            "zone_id": "ZONE-01",
            "building_id": "bldg",
            "telemetry_ok": True,
            "safe_mode": False,
            "normalized": {"Indoor_Temp": 22.5, "Occupancy": 0.5},
            "candidates": [],
            "rls": {},
            "lstm": {},
            "comfort_band": {"min_c": 21, "max_c": 24},
            "tariff_usd_kwh": 0.14,
            "engineering_limits": {},
        },
    )
    monkeypatch.setattr(
        svc,
        "rank_candidates",
        lambda _s: {
            "winner": {
                "action_id": "hold",
                "mapped_opportunity": "O2",
                "point_id": POINT,
                "old_value": 24.0,
                "new_value": 24.0,
                "score": 0.0,
                "feasible": True,
            },
            "rejected_actions": [],
            "all_rejected": False,
            "constraints": [],
            "confidence": 0.9,
        },
    )
    monkeypatch.setattr("backend.ai.safe_rl.service.is_safe_mode", lambda: False)
    monkeypatch.setattr(
        "backend.rules.engine.evaluate",
        lambda *a, **k: {"verdict": "APPROVED", "code": "APPROVED", "reason": "ok", "checks": []},
    )
    r = client.post("/api/platform/ai/safe-rl/recommend", json={"zone_id": "ZONE-01"})
    assert r.status_code == 200
    assert r.json()["wrote_setpoints"] is False
    assert executed == []


def test_h4_cloud_down_local_loop(client: TestClient, monkeypatch):
    monkeypatch.setenv("HVAC_EDGE_MODE", "1")
    monkeypatch.setenv("HVAC_CLOUD_URL", "http://127.0.0.1:9/unreachable")
    monkeypatch.setenv("HVAC_BMS_WRITE_ENABLED", "1")

    edge = client.get("/api/platform/edge/status").json()
    assert edge["edge_mode"] is True
    assert edge["cloud_reachable"] is False
    assert edge["local_loop_ok"] is True

    # Local recommend still works when cloud down
    from backend.ai.safe_rl import service as svc

    monkeypatch.setattr(
        svc,
        "build_decision_state",
        lambda *_a, **_k: {
            "zone_id": "ZONE-01",
            "building_id": "bldg",
            "telemetry_ok": True,
            "safe_mode": False,
            "normalized": {"Indoor_Temp": 22.5, "Occupancy": 0.5},
            "candidates": [],
            "rls": {},
            "lstm": {},
            "comfort_band": {"min_c": 21, "max_c": 24},
            "tariff_usd_kwh": 0.14,
            "engineering_limits": {},
        },
    )
    monkeypatch.setattr(
        svc,
        "rank_candidates",
        lambda _s: {
            "winner": {
                "action_id": "zone_sp_up_0.5",
                "mapped_opportunity": "O2",
                "point_id": POINT,
                "old_value": 24.0,
                "new_value": 24.5,
                "score": 1.0,
                "feasible": True,
            },
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
    rec = client.post("/api/platform/ai/safe-rl/recommend", json={"zone_id": "ZONE-01"})
    assert rec.status_code == 200
    assert rec.json()["wrote_setpoints"] is False

    _commission_writable(client)
    assert client.post("/api/platform/bms/write-enable", json={"confirm": True}).status_code == 200
    cid = _propose_cmd()
    assert client.post(f"/api/platform/commands/{cid}/approve").status_code == 200
    assert client.post(f"/api/platform/commands/{cid}/apply").status_code == 200
    assert client.post(f"/api/platform/commands/{cid}/verify").status_code == 200


def test_h5_ai_watchdog_and_rule_reject(client: TestClient):
    from backend.workers.watchdog import beat, ai_watchdog_status, reset_beats_for_tests

    reset_beats_for_tests()
    st = ai_watchdog_status()
    assert st["rls"]["status"] in ("NEVER", "STALE")
    beat(note="ok", service="rls")
    beat(note="ok", service="rules")
    st2 = ai_watchdog_status()
    assert st2["rls"]["ok"] is True
    assert st2["rules"]["ok"] is True

    ready = client.get("/api/readyz").json()
    assert "ai_watchdogs" in ready
    assert "edge" in ready

    # Rule reject regression
    from backend.rules.engine import evaluate

    out = evaluate(
        {
            "action": "APPLY",
            "point_id": POINT,
            "old_value": 24.0,
            "new_value": 30.0,
            "opportunity_id": "O2",
            "safe_mode": True,
            "skip_audit": True,
            "strict": False,
        }
    )
    assert out["verdict"] == "REJECTED"

    # Write gate still blocks non-allowlisted point when enforce on
    from backend.bms import command_writer as cw

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("HVAC_STAGE_G_ENFORCE", "1")
    monkeypatch.setattr("backend.bms.connection_manager.is_simulation_mode", lambda: False)
    monkeypatch.setattr(cw, "physical_writes_allowed", lambda: True)
    monkeypatch.setattr("backend.services.hvac_safety_contract.is_safe_mode", lambda: False)
    monkeypatch.setattr(
        "backend.rules.engine.evaluate",
        lambda *a, **k: {"verdict": "APPROVED", "code": "APPROVED", "reason": "ok", "checks": []},
    )
    monkeypatch.setattr(cw, "resolve_write_target", lambda pid: (pid, None, "WRITE"))
    monkeypatch.setattr(
        "backend.bms.connection_manager.get_connection_manager",
        lambda: MagicMock(adapter=lambda: MagicMock()),
    )
    try:
        denied = cw.write_point("AHU-01.sat_setpoint", 13.0)
        assert denied.success is False
        assert denied.code == "STAGE_G_POINT_NOT_ALLOWED"
    finally:
        monkeypatch.undo()
