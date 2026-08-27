"""Dashboard home BFF: DATASET never LIVE; verified KPI is not guide %; O13 N/A without CO."""
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
os.environ["HVAC_BMS_MODE"] = "simulation"
os.environ["HVAC_BMS_CONNECTED"] = "1"
os.environ["HVAC_BMS_WRITE_ENABLED"] = "0"
os.environ["HVAC_DEPLOYMENT_MODE"] = "local"


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("HVAC_PLANT_MODE", "DATASET")
    monkeypatch.setenv("HVAC_PLANT_MODE_PERSIST", "0")
    from backend.agents.scheduling_supervisory.gateway import reset_bms_gateway
    from backend.bms.connection_manager import reset_connection_manager
    from database.session import init_db

    init_db()
    reset_connection_manager()
    reset_bms_gateway()
    from backend.main import app

    return TestClient(app)


def _o13(body: dict) -> dict:
    for ch in body.get("chapters") or []:
        for o in ch.get("opportunities") or []:
            if o.get("id") == "O13":
                return o
    return {}


def test_dashboard_home_dataset_never_live(client: TestClient):
    res = client.get("/api/platform/dashboard/home")
    assert res.status_code == 200
    body = res.json()
    assert body["plantMode"] == "DATASET"
    assert str(body["telemetry"]["status"]).upper() != "LIVE"
    assert body["telemetry"]["status"] == "SIMULATED"
    assert "LIVE" not in str(body.get("bms", {}).get("status") or "")


def test_dashboard_home_verified_not_guide_percent(client: TestClient):
    res = client.get("/api/platform/dashboard/home")
    assert res.status_code == 200
    body = res.json()
    kpis = body.get("kpis") or {}
    verified = kpis.get("verifiedKw")
    for ch in body.get("chapters") or []:
        for o in ch.get("opportunities") or []:
            pot = o.get("guide_savings_potential") or ""
            assert o.get("energy_impact_class") == "GUIDE_POTENTIAL"
            if verified is not None:
                assert str(verified) not in pot
                assert not str(pot).startswith(str(verified))


def test_dashboard_home_o13_na_without_co():
    from backend.services.dashboard_home_service import _applicability

    empty = {
        "chillers": [],
        "ahus": [],
        "pumps": [],
        "vfds": [],
        "condenser_water": [],
        "hot_water": [],
        "zones": [],
        "vavs": [],
    }
    assert _applicability("O13", ["co_ppm"], empty, False) == "N/A"
    assert _applicability("O13", [], empty, False) == "N/A"


def test_dashboard_home_o13_catalog_reachable(client: TestClient):
    res = client.get("/api/platform/dashboard/home")
    assert res.status_code == 200
    body = res.json()
    o13 = _o13(body)
    assert o13
    assert o13.get("href")
    if not body.get("hasCoPoints"):
        assert o13["applicability"] == "N/A"
    else:
        assert o13["applicability"] in ("Y", "Limited", "Unmapped", "N/A")


def test_dashboard_home_empty_plant_not_y(client: TestClient):
    res = client.get("/api/platform/dashboard/home")
    assert res.status_code == 200
    body = res.json()
    layers = body.get("layers") or {}
    empty = all(not (layers.get(k) or []) for k in layers)
    if empty:
        for ch in body.get("chapters") or []:
            for o in ch.get("opportunities") or []:
                if o.get("id") == "O13":
                    continue
                assert o.get("applicability") in ("Unmapped", "Limited", "N/A")
                assert o.get("applicability") != "Y"


def test_dashboard_home_chapters_o1_o20(client: TestClient):
    res = client.get("/api/platform/dashboard/home")
    body = res.json()
    ids = [o["id"] for ch in body["chapters"] for o in ch["opportunities"]]
    assert ids == [f"O{i}" for i in range(1, 21)]
    assert body["guide"]["document"] == "150317hvacguide.pdf"
    assert "GUIDE_POTENTIAL" in body["guide"]["note"]
