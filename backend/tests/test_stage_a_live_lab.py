"""Stage A: Lab BACnet on LIVE_BMS — discover, map, LIVE telemetry, writes off."""
from __future__ import annotations

import os
import sys

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


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("HVAC_BMS_LAB", "1")
    monkeypatch.setenv("HVAC_BMS_WRITE_ENABLED", "0")
    monkeypatch.setenv("HVAC_PLANT_MODE_PERSIST", "1")
    monkeypatch.setenv("HVAC_USE_SIMULATION", "0")
    from backend.agents.scheduling_supervisory.gateway import reset_bms_gateway
    from backend.bms.connection_manager import reset_connection_manager
    from database.session import init_db

    init_db()
    from database.session import SessionLocal
    from database.models_bms import BmsConnectionDB, BmsDeviceDB, BmsPointDB, EquipmentPointMappingDB
    from database.models_platform import CanonicalTelemetryDB, PlatformSettingDB

    db = SessionLocal()
    try:
        db.query(EquipmentPointMappingDB).delete()
        db.query(BmsPointDB).delete()
        db.query(BmsDeviceDB).delete()
        db.query(BmsConnectionDB).delete()
        db.query(CanonicalTelemetryDB).delete()
        db.query(PlatformSettingDB).filter_by(key="PLANT_MODE").delete()
        db.commit()
    finally:
        db.close()
    reset_connection_manager()
    reset_bms_gateway()
    from backend.services.platform_ops_service import set_plant_mode

    set_plant_mode("DATASET")
    from backend.main import app

    with TestClient(app) as client:
        yield client


def _commission_stage_a(client: TestClient) -> dict:
    from backend.bms.lab_bacnet_gateway import stage_a_mapping_targets
    from backend.services.platform_ops_service import set_plant_mode

    set_plant_mode("LIVE_BMS")
    from backend.bms.connection_manager import reset_connection_manager

    reset_connection_manager()

    res = client.post(
        "/api/platform/bms/connect",
        json={"protocol": "bacnet", "host": "127.0.0.1", "port": 47808},
    )
    assert res.json().get("connected") is True, res.json()

    disc = client.post("/api/platform/bms/discover").json()
    assert disc.get("devices", 0) >= 4
    assert disc.get("points", 0) >= len(stage_a_mapping_targets())

    devices = client.get("/api/platform/bms/devices").json()["devices"]
    by_ident = {}
    for d in devices:
        pts = client.get(f"/api/platform/bms/devices/{d['id']}/points").json()["points"]
        for p in pts:
            by_ident[p["point_identifier"]] = p["id"]

    for target in stage_a_mapping_targets():
        bms_id = by_ident.get(target["point_identifier"])
        assert bms_id, f"missing discovered point {target['point_identifier']}"
        mapped = client.put(
            "/api/platform/bms/mappings",
            json={
                "equipment_id": target["equipment_id"],
                "canonical_point": target["canonical_point"],
                "bms_point_id": bms_id,
                "direction": "READ",
            },
        )
        assert mapped.status_code == 200, mapped.text

    from backend.bms.telemetry_reader import poll_once

    rows = poll_once(include_unmapped=False)
    assert len(rows) >= len(stage_a_mapping_targets())
    return client.get("/api/platform/status").json()


def test_dataset_never_uses_lab_gateway(client: TestClient):
    from backend.services.platform_ops_service import set_plant_mode

    set_plant_mode("DATASET")
    res = client.post(
        "/api/platform/bms/connect",
        json={"protocol": "bacnet", "host": "127.0.0.1", "port": 47808},
    )
    body = res.json()
    assert body.get("connected") is False
    assert body.get("code") == "SIMULATION_MODE"


def test_stage_a_lab_discover_map_live_writes_off(client: TestClient):
    st = _commission_stage_a(client)
    assert st["plantMode"] == "LIVE_BMS"
    assert st["bms"]["status"] == "CONNECTED"
    assert st["telemetry"]["status"] == "LIVE"
    assert str(st["telemetry"]["source"]).upper() == "LIVE_BMS"
    assert str(st["telemetry"].get("quality") or "").upper() == "GOOD"
    assert st.get("labMode") is True
    assert st["writeEnabled"] is False
    assert st["controlEnabled"] is False

    write = client.post("/api/platform/bms/write-enable", json={"confirm": True})
    # Still blocked without HVAC_BMS_WRITE_ENABLED=1 and/or other gates
    assert write.status_code == 409

    status = client.get("/api/platform/bms/status").json()
    assert status.get("labMode") is True
    assert status.get("write_enabled") is False


def test_stage_a_mapping_set_complete(client: TestClient):
    from backend.bms.lab_bacnet_gateway import stage_a_mapping_targets

    _commission_stage_a(client)
    mappings = client.get("/api/platform/bms/mappings").json()["mappings"]
    qualified = {m["qualified"] for m in mappings}
    expected = {f"{t['equipment_id']}.{t['canonical_point']}" for t in stage_a_mapping_targets()}
    assert expected.issubset(qualified)
