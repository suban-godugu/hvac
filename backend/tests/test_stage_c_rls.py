"""Stage C: RLS engine converge, persist, source_mode split, APIs, no writes."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
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
os.environ["HVAC_RLS_MIN_UPDATES"] = "5"
os.environ["HVAC_RLS_TICK_SECONDS"] = "5"
os.environ["HVAC_RLS_ERROR_REJECT"] = "500"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("HVAC_ALLOW_CREATE_ALL", "1")
    monkeypatch.setenv("HVAC_BMS_WRITE_ENABLED", "0")
    monkeypatch.setenv("HVAC_RLS_MIN_UPDATES", "5")
    monkeypatch.setenv("HVAC_PLANT_MODE_PERSIST", "0")
    from backend.ai.rls.runner import reset_debounce
    from backend.ai.rls.service import clear_error_rings
    from backend.services.timeseries_buffer import clear as clear_buffer
    from database.session import init_db

    init_db()
    from database.session import SessionLocal
    from database.models_platform import CanonicalTelemetryDB, RlsModelStateDB

    db = SessionLocal()
    try:
        db.query(RlsModelStateDB).delete()
        db.query(CanonicalTelemetryDB).delete()
        db.commit()
    finally:
        db.close()
    clear_buffer()
    clear_error_rings()
    reset_debounce()
    from backend.main import app

    with TestClient(app) as client:
        yield client


def test_rls_engine_converges():
    from backend.ai.rls.engine import RlsEngine

    true = np.array([1.0, 0.5, -0.2, 0.1, 0.0, 0.05, 0.02], dtype=float)
    eng = RlsEngine(7, lam=0.99, delta=100.0, error_reject=100.0)
    rng = np.random.default_rng(7)
    early = []
    late = []
    for i in range(200):
        x = np.concatenate([[1.0], rng.normal(size=6)])
        y = float(true @ x) + float(rng.normal(scale=0.01))
        out = eng.update(x, y)
        assert out["updated"] is True
        err = abs(out["error"])
        if i < 20:
            early.append(err)
        if i >= 180:
            late.append(err)
    assert float(np.mean(late)) < float(np.mean(early))
    assert float(np.linalg.norm(eng.theta - true)) < 0.5


def _seed_normalized_series(*, source: str, n: int = 12):
    from backend.services.canonical_telemetry_service import record_point

    base = _now() - timedelta(minutes=n)
    for i in range(n):
        ts = base + timedelta(minutes=i)
        tin = 22.0 + 0.05 * i
        record_point("ZONE-01.zone_temperature", tin, "degC", source, "GOOD", equipment_id="ZONE-01", timestamp=ts)
        record_point("ZONE-01.cooling_setpoint", 24.0, "degC", source, "GOOD", equipment_id="ZONE-01", timestamp=ts)
        record_point("ZONE-01.occupancy", 0.5, "frac", source, "GOOD", equipment_id="ZONE-01", timestamp=ts)
        record_point("SITE.outdoor_air_temperature", 30.0, "degC", source, "GOOD", equipment_id="SITE", timestamp=ts)
        record_point("AHU-01.fan_speed", 60.0 + i, "pct", source, "GOOD", equipment_id="AHU-01", timestamp=ts)
        record_point("CH-01.power", 100.0 + 0.5 * i, "kW", source, "GOOD", equipment_id="CH-01", timestamp=ts)
        record_point("AHU-01.enable", 1.0, "bool", source, "GOOD", equipment_id="AHU-01", timestamp=ts)
        record_point("CH-01.status", 1.0, "bool", source, "GOOD", equipment_id="CH-01", timestamp=ts)


def test_service_persists_updates(client: TestClient, monkeypatch):
    monkeypatch.setenv("HVAC_BMS_MODE", "production")
    monkeypatch.setenv("HVAC_PLANT_MODE", "LIVE_BMS")
    from backend.ai.rls.runner import tick
    from database.models_platform import RlsModelStateDB
    from database.session import SessionLocal

    _seed_normalized_series(source="LIVE_BMS", n=15)
    out = tick(zone_id="ZONE-01", lookback_minutes=40, step_seconds=60)
    assert out["wrote_setpoints"] is False
    assert out["updated"] >= 1

    db = SessionLocal()
    try:
        rows = db.query(RlsModelStateDB).all()
        assert len(rows) >= 1
        assert all(r.source_mode == "LIVE_BMS" for r in rows)
        assert any(int(r.n_updates or 0) >= 1 for r in rows)
        assert any(int(r.version or 0) >= 1 for r in rows)
    finally:
        db.close()


def test_live_and_sim_separate_rows(client: TestClient, monkeypatch):
    from backend.ai.rls.service import update_from_records
    from database.models_platform import RlsModelStateDB
    from database.session import SessionLocal

    monkeypatch.setenv("HVAC_BMS_MODE", "simulation")
    monkeypatch.setenv("HVAC_PLANT_MODE", "DATASET")
    _seed_normalized_series(source="SIMULATION", n=10)

    from backend.services.ai_normalized_telemetry import build_ai_records

    end = _now()
    start = end - timedelta(minutes=40)
    recs = build_ai_records(zone_id="ZONE-01", t0=start.isoformat(), t1=end.isoformat(), step_seconds=60)["records"]
    # Force source labels for split test
    live_recs = [{**r, "source": "LIVE_BMS"} for r in recs if r.get("Indoor_Temp") is not None]
    sim_recs = [{**r, "source": "SIMULATION"} for r in recs if r.get("Indoor_Temp") is not None]
    assert live_recs and sim_recs
    update_from_records(live_recs[:8], zone_id="ZONE-01")
    update_from_records(sim_recs[:8], zone_id="ZONE-01")

    db = SessionLocal()
    try:
        modes = {r.source_mode for r in db.query(RlsModelStateDB).all()}
        assert "LIVE_BMS" in modes
        assert "SIMULATION" in modes
    finally:
        db.close()


def test_api_status_and_errors(client: TestClient, monkeypatch):
    monkeypatch.setenv("HVAC_BMS_MODE", "production")
    monkeypatch.setenv("HVAC_PLANT_MODE", "LIVE_BMS")
    from backend.ai.rls.runner import tick

    _seed_normalized_series(source="LIVE_BMS", n=12)
    tick(zone_id="ZONE-01", lookback_minutes=40, step_seconds=60)

    st = client.get("/api/platform/ai/rls/status").json()
    assert st["count"] >= 1
    assert any(m["model_key"] in ("zone_thermal", "hvac_power") for m in st["models"])

    mk = next((m["model_key"] for m in st["models"] if int(m.get("n_updates") or 0) > 0), st["models"][0]["model_key"])
    params = client.get("/api/platform/ai/rls/params", params={"model_key": mk, "zone_id": "ZONE-01"}).json()
    assert params.get("found") is True
    assert "theta" in params

    errs = client.get("/api/platform/ai/rls/errors", params={"model_key": mk, "zone_id": "ZONE-01"}).json()
    assert errs["count"] >= 1 or any(int(m.get("n_updates") or 0) > 0 for m in st["models"])


def test_tick_never_enables_writes(client: TestClient, monkeypatch):
    monkeypatch.setenv("HVAC_BMS_MODE", "production")
    monkeypatch.setenv("HVAC_PLANT_MODE", "LIVE_BMS")
    monkeypatch.setenv("HVAC_BMS_WRITE_ENABLED", "0")
    from backend.ai.rls.runner import tick

    _seed_normalized_series(source="LIVE_BMS", n=10)
    out = tick(zone_id="ZONE-01", lookback_minutes=40)
    assert out.get("wrote_setpoints") is False

    we = client.post("/api/platform/bms/write-enable", json={"confirm": True})
    assert we.status_code == 409
    body = client.get("/api/platform/status").json()
    assert body.get("writeEnabled") is False


def test_error_ring_persists_across_memory_unload(client: TestClient, monkeypatch):
    monkeypatch.setenv("HVAC_BMS_MODE", "production")
    monkeypatch.setenv("HVAC_PLANT_MODE", "LIVE_BMS")
    from backend.ai.rls.runner import tick
    from backend.ai.rls.service import clear_error_rings, error_trend, unload_error_rings_memory

    clear_error_rings()
    _seed_normalized_series(source="LIVE_BMS", n=12)
    tick(zone_id="ZONE-01", lookback_minutes=40, step_seconds=60)
    before = error_trend("zone_thermal", zone_id="ZONE-01", source_mode="LIVE_BMS")
    assert before["count"] >= 1
    unload_error_rings_memory()
    after = error_trend("zone_thermal", zone_id="ZONE-01", source_mode="LIVE_BMS")
    assert after["count"] >= 1
    assert after["errors"][-1].get("error") is not None
