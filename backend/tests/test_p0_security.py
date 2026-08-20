"""P0 write gates and safety — no application authentication."""
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
os.environ["HVAC_BMS_CONNECTED"] = "0"
os.environ["HVAC_DEPLOYMENT_MODE"] = "local"


@pytest.fixture()
def client():
    from backend.main import app

    return TestClient(app)


def test_healthz(client: TestClient):
    res = client.get("/healthz")
    assert res.status_code == 200
    assert "X-Request-ID" in res.headers


def test_readyz(client: TestClient):
    res = client.get("/readyz")
    assert res.status_code == 200
    body = res.json()
    assert body.get("database") == "OK"
    assert "request_id" in body


def test_no_login_route(client: TestClient):
    res = client.post("/api/auth/login", json={"username": "x", "password": "y"})
    assert res.status_code == 404


def test_writes_have_no_auth_gate(client: TestClient):
    res = client.post("/api/mode", json={"mode": "ADVISORY"})
    assert res.status_code != 401
    assert res.status_code != 403


def test_platform_status_unauthenticated(client: TestClient):
    res = client.get("/api/platform/status")
    assert res.status_code == 200
    body = res.json()
    assert "bms" in body
    assert "telemetry" in body
    assert "safety" in body
    assert "building" in body


def test_simulation_never_writes_bms():
    from backend.services.hvac_safety_contract import evaluate_dispatch

    ok, reason, classified = evaluate_dispatch(
        {
            "telemetry": {"quality": "GOOD", "age_seconds": 1, "source": "SIMULATION"},
            "source": "SIMULATION",
            "supervisory": {"decision": "OPTIMIZE", "confidence": 0.9},
            "safety": {"status": "PASS"},
            "current_value": 22,
            "target_value": 23,
            "approval_status": "APPROVED",
        }
    )
    assert ok is False
    assert classified.get("code") in ("SIMULATION_BLOCKED", "NOT_LIVE")


def test_stale_blocks_write():
    from backend.services.hvac_safety_contract import evaluate_dispatch

    ok, reason, classified = evaluate_dispatch(
        {
            "telemetry": {"quality": "GOOD", "age_seconds": 9999, "source": "LIVE_BMS", "raw": "LIVE"},
            "source": "LIVE_BMS",
            "supervisory": {"decision": "OPTIMIZE", "confidence": 0.9},
            "safety": {"status": "PASS"},
            "current_value": 22,
            "target_value": 23,
            "approval_status": "APPROVED",
        }
    )
    assert ok is False
    assert classified.get("code") in ("STALE", "NOT_LIVE", "BMS_OFFLINE")


def test_classify_not_dispatchable_when_bms_offline():
    from backend.services.hvac_safety_contract import classify_telemetry

    classified = classify_telemetry(
        {"quality": "GOOD", "age_seconds": 1, "source": "LIVE_BMS", "raw": "LIVE"},
        "LIVE_BMS",
    )
    assert classified["usable"] is False
    assert classified.get("bms_connected") is False


def test_o18_dispatch_code_is_advisory():
    from backend.services.hvac_safety_contract import evaluate_dispatch

    ok, _, classified = evaluate_dispatch(
        {
            "telemetry": {"quality": "GOOD", "age_seconds": 1, "source": "SIMULATION"},
            "source": "SIMULATION",
            "supervisory": {"decision": "OPTIMIZE", "confidence": 0.9},
            "safety": {"status": "PASS"},
            "current_value": 1,
            "target_value": 2,
            "opportunity_id": "O18",
        }
    )
    assert ok is False
    assert classified.get("code") == "ADVISORY"


def test_activity_not_hardcoded(client: TestClient):
    res = client.get("/api/agents/scheduling/activity")
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body, list)
    fake = "66 BMS points ingested"
    assert not any(fake in str(item.get("detail") or "") for item in body)


def test_create_all_off_in_production():
    os.environ["HVAC_ENV"] = "production"
    os.environ.pop("HVAC_ALLOW_CREATE_ALL", None)
    from importlib import reload
    import database.session as sess

    reload(sess)
    assert sess._allow_create_all() is False
    os.environ["HVAC_ENV"] = "development"
    reload(sess)
