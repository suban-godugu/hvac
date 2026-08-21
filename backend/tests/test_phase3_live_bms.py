"""Phase 3: Live BMS is a real gateway only. Dataset remains a switch. Writes stay off."""
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


def _fake_gateway():
    from backend.bms.base import (
        BMSGateway,
        BmsHealth,
        DiscoveredDevice,
        DiscoveredPoint,
        PointReading,
        utc_now,
    )
    from backend.bms.command_writer import write_point as reject

    class FakeGw(BMSGateway):
        protocol = "bacnet"

        def __init__(self):
            self._ok = False

        def connect(self, host, port=47808, **kwargs):
            self._ok = True
            return BmsHealth(
                connected=True,
                protocol="bacnet",
                host=host,
                port=port,
                last_connected_at=utc_now().isoformat(),
            )

        def disconnect(self):
            self._ok = False
            return BmsHealth(connected=False, protocol="bacnet")

        def health(self):
            return BmsHealth(
                connected=self._ok,
                protocol="bacnet",
                last_connected_at=utc_now().isoformat() if self._ok else None,
            )

        def discover_devices(self):
            return [DiscoveredDevice(device_identifier="lab-ahu", name="LAB-AHU", device_type="AHU")]

        def discover_points(self, device_id):
            return [
                DiscoveredPoint(
                    point_identifier="sat-1",
                    name="SAT",
                    object_type="analog-input",
                    object_instance="1",
                    unit="degC",
                    writable=False,
                )
            ]

        def read_point(self, point_id):
            return PointReading(
                point_id=point_id,
                value=14.2,
                unit="degC",
                quality="GOOD",
                timestamp=utc_now().isoformat(),
            )

        def read_points(self, point_ids):
            return [self.read_point(p) for p in point_ids]

        def write_point(self, point_id, value, priority=10):
            return reject(point_id, value, priority)

        def write_points(self, writes):
            return [self.write_point(w["point_id"], w["value"]) for w in writes]

    return FakeGw


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("HVAC_PLANT_MODE_PERSIST", "1")
    monkeypatch.setenv("HVAC_BMS_MODE", "simulation")
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

    return TestClient(app)


def test_dataset_blocks_production_connect(client: TestClient):
    res = client.post(
        "/api/platform/bms/connect",
        json={"protocol": "bacnet", "host": "10.0.0.9", "port": 47808},
    )
    body = res.json()
    assert body.get("connected") is False
    assert body.get("code") == "SIMULATION_MODE"


def test_live_never_uses_synthetic_rows(client: TestClient):
    from backend.services.agent_telemetry_service import get_point
    from backend.services.canonical_telemetry_service import latest_points, record_point
    from backend.services.platform_ops_service import set_plant_mode

    record_point(
        "AHU-01.supply_air_temperature",
        13.8,
        "degC",
        "SIMULATION",
        "GOOD",
        equipment_id="AHU-01",
    )
    assert any(p.get("source") == "SIMULATION" for p in latest_points(limit=20))
    set_plant_mode("LIVE_BMS")
    pts = latest_points(limit=20)
    assert all(str(p.get("source") or "").upper() != "SIMULATION" for p in pts)
    assert get_point("AHU-01", "supply_air_temperature") is None
    st = client.get("/api/platform/status").json()
    assert st["plantMode"] == "LIVE_BMS"
    assert st["bms"]["status"] == "DISCONNECTED"
    assert st["telemetry"]["status"] != "LIVE"
    assert st["telemetry"]["status"] != "SIMULATED"


def test_live_handshake_maps_canonical_and_tel_live(client: TestClient):
    from backend.agents.scheduling_supervisory.gateway import (
        ProductionBMSGateway,
        SimulatorBMSGateway,
        get_bms_gateway,
        reset_bms_gateway,
    )
    from backend.bms.connection_manager import register_adapter_factory, reset_connection_manager
    from backend.services.platform_ops_service import set_plant_mode

    set_plant_mode("LIVE_BMS")
    reset_connection_manager()
    reset_bms_gateway()
    register_adapter_factory("bacnet", _fake_gateway())

    gw = get_bms_gateway()
    assert isinstance(gw, ProductionBMSGateway)
    assert not isinstance(gw, SimulatorBMSGateway)

    res = client.post(
        "/api/platform/bms/connect",
        json={"protocol": "bacnet", "host": "10.0.0.9", "port": 47808},
    )
    assert res.json().get("connected") is True

    disc = client.post("/api/platform/bms/discover").json()
    assert disc["devices"] >= 1
    devices = client.get("/api/platform/bms/devices").json()["devices"]
    pts = client.get(f"/api/platform/bms/devices/{devices[0]['id']}/points").json()["points"]
    mapped = client.put(
        "/api/platform/bms/mappings",
        json={
            "equipment_id": "AHU-01",
            "canonical_point": "supply_air_temperature",
            "bms_point_id": pts[0]["id"],
            "direction": "READ",
        },
    )
    assert mapped.status_code == 200
    assert mapped.json()["qualified"] == "AHU-01.supply_air_temperature"

    st = client.get("/api/platform/status").json()
    assert st["plantMode"] == "LIVE_BMS"
    assert st["bms"]["status"] == "CONNECTED"
    assert st["telemetry"]["status"] == "LIVE"
    assert str(st["telemetry"]["source"]).upper() == "LIVE_BMS"
    assert st["controlEnabled"] is False
    assert st["writeEnabled"] is False

    write = client.post("/api/platform/bms/write-enable")
    assert write.status_code == 409

    back = client.post("/api/platform/plant-mode", json={"mode": "DATASET"}).json()
    assert back["plantMode"] == "DATASET"
    st2 = client.get("/api/platform/status").json()
    assert st2["bms"]["status"] == "DISCONNECTED"
    assert st2["telemetry"]["status"] == "SIMULATED"
