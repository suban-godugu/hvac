"""Stage B: ring buffer, t0–t1 window API, normalized AI records, retention purge."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

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
os.environ["HVAC_TS_BUFFER_SECONDS"] = "7200"
os.environ["HVAC_TS_BUFFER_MAX"] = "720"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("HVAC_ALLOW_CREATE_ALL", "1")
    monkeypatch.setenv("HVAC_TELEMETRY_PURGE", "0")
    monkeypatch.setenv("HVAC_PLANT_MODE_PERSIST", "0")
    monkeypatch.setenv("HVAC_PLANT_MODE", "DATASET")
    monkeypatch.setenv("HVAC_BMS_MODE", "simulation")
    from backend.agents.scheduling_supervisory.gateway import reset_bms_gateway
    from backend.bms.connection_manager import reset_connection_manager
    from backend.services.timeseries_buffer import clear as clear_buffer
    from database.session import init_db

    init_db()
    from database.session import SessionLocal
    from database.models_platform import CanonicalTelemetryDB

    db = SessionLocal()
    try:
        db.query(CanonicalTelemetryDB).delete()
        db.commit()
    finally:
        db.close()
    clear_buffer()
    reset_connection_manager()
    reset_bms_gateway()
    from backend.main import app

    with TestClient(app) as client:
        yield client


def test_buffer_push_and_window():
    from backend.services.timeseries_buffer import clear, push, window

    clear()
    t0 = _now() - timedelta(minutes=10)
    t1 = _now()
    push(
        "ZONE-01.zone_temperature",
        {
            "point_id": "ZONE-01.zone_temperature",
            "timestamp": (t0 + timedelta(minutes=1)).isoformat(),
            "value": 24.0,
            "quality": "GOOD",
            "source": "LIVE_BMS",
        },
    )
    push(
        "ZONE-01.zone_temperature",
        {
            "point_id": "ZONE-01.zone_temperature",
            "timestamp": (t0 + timedelta(minutes=5)).isoformat(),
            "value": 24.5,
            "quality": "GOOD",
            "source": "LIVE_BMS",
        },
    )
    rows = window("ZONE-01.zone_temperature", t0, t1)
    assert len(rows) == 2
    assert rows[0]["value"] == 24.0
    assert rows[1]["value"] == 24.5


def test_db_window_ordered_via_api(client: TestClient):
    from backend.services.canonical_telemetry_service import record_point
    from backend.services.timeseries_buffer import clear

    clear()
    base = _now() - timedelta(minutes=30)
    for i, val in enumerate([13.0, 13.5, 14.0]):
        record_point(
            "AHU-01.supply_air_temperature",
            val,
            "degC",
            "LIVE_BMS",
            "GOOD",
            equipment_id="AHU-01",
            timestamp=base + timedelta(minutes=i * 5),
        )
    t0 = (base - timedelta(minutes=1)).isoformat()
    t1 = (base + timedelta(minutes=20)).isoformat()
    res = client.get(
        "/api/platform/timeseries/window",
        params={"point_id": "AHU-01.supply_air_temperature", "t0": t0, "t1": t1, "limit": 100},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["count"] >= 3
    values = [p["value"] for p in body["points"]]
    assert values == sorted(values)
    assert 13.0 in values and 14.0 in values


def test_normalized_ai_records_null_humidity_not_zero(client: TestClient, monkeypatch):
    from backend.services.canonical_telemetry_service import record_point
    from backend.services.timeseries_buffer import clear

    clear()
    monkeypatch.setenv("HVAC_BMS_MODE", "production")
    monkeypatch.setenv("HVAC_PLANT_MODE", "LIVE_BMS")

    class _Wx:
        def snapshot(self, refresh_seconds: int = 600):
            return {"oat": 31.0, "humidity": None, "condition": None, "source": "NONE"}

    monkeypatch.setattr("backend.services.weather_service.weather_service", _Wx())

    base = _now() - timedelta(minutes=5)
    record_point("ZONE-01.zone_temperature", 24.2, "degC", "LIVE_BMS", "GOOD", equipment_id="ZONE-01", timestamp=base)
    record_point("ZONE-01.cooling_setpoint", 24.0, "degC", "LIVE_BMS", "GOOD", equipment_id="ZONE-01", timestamp=base)
    record_point("ZONE-01.occupancy", 0.6, "frac", "LIVE_BMS", "GOOD", equipment_id="ZONE-01", timestamp=base)
    record_point("SITE.outdoor_air_temperature", 32.0, "degC", "LIVE_BMS", "GOOD", equipment_id="SITE", timestamp=base)
    record_point("AHU-01.fan_speed", 70.0, "pct", "LIVE_BMS", "GOOD", equipment_id="AHU-01", timestamp=base)
    record_point("CH-01.power", 110.0, "kW", "LIVE_BMS", "GOOD", equipment_id="CH-01", timestamp=base)
    record_point("AHU-01.enable", 1.0, "bool", "LIVE_BMS", "GOOD", equipment_id="AHU-01", timestamp=base)
    record_point("CH-01.status", 1.0, "bool", "LIVE_BMS", "GOOD", equipment_id="CH-01", timestamp=base)

    t0 = (base - timedelta(minutes=1)).isoformat()
    t1 = (base + timedelta(minutes=3)).isoformat()
    res = client.get(
        "/api/platform/ai/normalized",
        params={"zone_id": "ZONE-01", "t0": t0, "t1": t1, "step_seconds": 60},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["count"] >= 1
    row = next((r for r in body["records"] if r.get("Indoor_Temp") is not None), body["records"][0])
    for key in (
        "Timestamp",
        "Zone_ID",
        "Outdoor_Temp",
        "Indoor_Temp",
        "Humidity",
        "Occupancy",
        "Setpoint",
        "Fan_Speed",
        "HVAC_Power",
        "Equipment_Status",
        "quality",
        "source",
    ):
        assert key in row
    assert row["Humidity"] is None
    assert row["Humidity"] != 0
    assert row["Indoor_Temp"] == 24.2
    assert str(row["source"]).upper() == "LIVE_BMS"


def test_normalized_sim_source_not_live(client: TestClient, monkeypatch):
    from backend.services.ai_normalized_telemetry import build_ai_records
    from backend.services.canonical_telemetry_service import record_point
    from backend.services.timeseries_buffer import clear

    clear()
    monkeypatch.setenv("HVAC_BMS_MODE", "simulation")
    monkeypatch.setenv("HVAC_PLANT_MODE", "DATASET")

    class _Wx:
        def snapshot(self, refresh_seconds: int = 600):
            return {"oat": None, "humidity": None, "source": "NONE"}

    monkeypatch.setattr("backend.services.weather_service.weather_service", _Wx())

    base = _now() - timedelta(minutes=2)
    record_point("ZONE-01.zone_temperature", 22.0, "degC", "SIMULATION", "GOOD", equipment_id="ZONE-01", timestamp=base)
    record_point("AHU-01.fan_speed", 50.0, "pct", "SIMULATION", "GOOD", equipment_id="AHU-01", timestamp=base)
    record_point("CH-01.power", 80.0, "kW", "SIMULATION", "GOOD", equipment_id="CH-01", timestamp=base)
    record_point("ZONE-01.cooling_setpoint", 23.0, "degC", "SIMULATION", "GOOD", equipment_id="ZONE-01", timestamp=base)
    record_point("ZONE-01.occupancy", 0.2, "frac", "SIMULATION", "GOOD", equipment_id="ZONE-01", timestamp=base)
    record_point("SITE.outdoor_air_temperature", 30.0, "degC", "SIMULATION", "GOOD", equipment_id="SITE", timestamp=base)
    record_point("AHU-01.enable", 1.0, "bool", "SIMULATION", "GOOD", equipment_id="AHU-01", timestamp=base)
    record_point("CH-01.status", 1.0, "bool", "SIMULATION", "GOOD", equipment_id="CH-01", timestamp=base)

    body = build_ai_records(
        zone_id="ZONE-01",
        t0=(base - timedelta(minutes=1)).isoformat(),
        t1=(base + timedelta(minutes=2)).isoformat(),
        step_seconds=60,
    )
    assert body["count"] >= 1
    row = next((r for r in body["records"] if r.get("Indoor_Temp") is not None), body["records"][0])
    src = str(row["source"]).upper()
    assert src != "LIVE_BMS"
    assert "SIM" in src or src in ("DEMO", "SIMULATION")
    # HTTP path also available
    http = client.get(
        "/api/platform/ai/normalized",
        params={
            "zone_id": "ZONE-01",
            "t0": (base - timedelta(minutes=1)).isoformat(),
            "t1": (base + timedelta(minutes=2)).isoformat(),
            "step_seconds": 60,
        },
    )
    assert http.status_code == 200
    assert http.json()["count"] >= 1


def test_retention_purge_deletes_old_rows(client: TestClient, monkeypatch):
    from backend.services.canonical_telemetry_service import record_point
    from backend.workers.retention_worker import archive_old_telemetry
    from database.models_platform import CanonicalTelemetryDB
    from database.session import SessionLocal

    monkeypatch.setenv("HVAC_TELEMETRY_PURGE", "1")
    monkeypatch.setenv("HVAC_TELEMETRY_RETAIN_DAYS", "1")

    old = _now() - timedelta(days=10)
    record_point("ZONE-01.zone_temperature", 20.0, "degC", "LIVE_BMS", "GOOD", timestamp=old)
    record_point("ZONE-01.zone_temperature", 21.0, "degC", "LIVE_BMS", "GOOD", timestamp=_now())

    n = archive_old_telemetry(retain_days=1)
    assert n >= 1
    db = SessionLocal()
    try:
        left = db.query(CanonicalTelemetryDB).filter(CanonicalTelemetryDB.timestamp < _now() - timedelta(days=2)).count()
        assert left == 0
        assert db.query(CanonicalTelemetryDB).count() >= 1
    finally:
        db.close()
