"""Phase 0 freeze: sim ≠ LIVE_BMS, missing ≠ 0, writes off, production never falls back to sim."""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

os.environ.setdefault("HVAC_ENV", "development")
os.environ.setdefault("HVAC_START_CONTROL_WORKER", "0")
os.environ.setdefault("HVAC_BMS_MODE", "simulation")
os.environ.setdefault("HVAC_BMS_WRITE_ENABLED", "0")
os.environ.setdefault("HVAC_ALLOW_SIM_WRITES", "0")


def test_simulation_source_never_live_bms(monkeypatch):
    monkeypatch.setenv("HVAC_BMS_MODE", "simulation")
    from backend.services.hvac_safety_contract import classify_telemetry, normalize_telemetry_source

    assert normalize_telemetry_source("LIVE_BMS") == "SIMULATION"
    assert normalize_telemetry_source("BMS") == "SIMULATION"
    assert normalize_telemetry_source(None) == "SIMULATION"
    classified = classify_telemetry(
        {"quality": "GOOD", "age_seconds": 1, "source": "SIMULATION"},
        "SIMULATION",
    )
    assert classified["status"] == "SIMULATED"
    assert classified["status"] != "LIVE"
    assert classified.get("source") != "LIVE_BMS"


def test_missing_sensor_is_null_not_zero():
    from backend.services.hvac_safety_contract import ingest_quality, _num

    assert _num(None) is None
    assert _num("") is None
    assert ingest_quality(None, "GOOD") == "MISSING"
    from backend.services.canonical_telemetry_service import record_point

    row = record_point("PHASE0.missing", None, "degC", "SIMULATION", "GOOD")
    assert row["value"] is None
    assert row["value"] != 0
    assert row["quality"] == "MISSING"
    assert row["source"] != "LIVE_BMS"


def test_writes_disabled_until_explicit(monkeypatch):
    monkeypatch.setenv("HVAC_BMS_WRITE_ENABLED", "0")
    from backend.bms.command_writer import physical_writes_allowed, write_enabled_flag, write_point
    from backend.services.hvac_safety_contract import evaluate_dispatch

    assert write_enabled_flag() is False
    assert physical_writes_allowed() is False
    outcome = write_point("AHU.SAT", 22.0)
    assert outcome.success is False
    ok, _, classified = evaluate_dispatch(
        {
            "telemetry": {"quality": "GOOD", "age_seconds": 1, "source": "LIVE_BMS", "raw": "LIVE"},
            "source": "LIVE_BMS",
            "supervisory": {"decision": "OPTIMIZE", "confidence": 0.99},
            "safety": {"status": "PASS"},
            "current_value": 22,
            "target_value": 23,
            "approval_status": "APPROVED",
        }
    )
    assert ok is False
    assert classified.get("code") in ("WRITE_DISABLED", "BMS_OFFLINE", "NOT_LIVE", "SIMULATION_BLOCKED")


def test_production_gateway_never_falls_back_to_simulator(monkeypatch):
    monkeypatch.setenv("HVAC_BMS_MODE", "production")
    monkeypatch.setenv("HVAC_BMS_PROTOCOL", "bacnet")
    from backend.agents.scheduling_supervisory.gateway import (
        ProductionBMSGateway,
        SimulatorBMSGateway,
        get_bms_gateway,
        reset_bms_gateway,
    )
    from backend.agents.scheduling_supervisory.agent import SchedulingSupervisoryAgent

    reset_bms_gateway()
    gw = get_bms_gateway()
    assert not isinstance(gw, SimulatorBMSGateway)
    assert isinstance(gw, ProductionBMSGateway)
    agent = SchedulingSupervisoryAgent()
    assert not isinstance(agent.gateway, SimulatorBMSGateway)
    reset_bms_gateway()


def test_sim_feed_stays_off_without_explicit_flag(monkeypatch):
    monkeypatch.setenv("HVAC_BMS_MODE", "simulation")
    monkeypatch.setenv("HVAC_USE_SIMULATION", "0")
    from backend.bms import simulation_telemetry as sim

    sim._THREAD = None
    sim.start_simulation_telemetry()
    assert sim._THREAD is None


def test_simulation_connect_does_not_open_production(monkeypatch):
    monkeypatch.setenv("HVAC_BMS_MODE", "simulation")
    from backend.bms.connection_manager import get_connection_manager

    out = get_connection_manager().connect("bacnet", "10.0.0.1", 47808)
    assert out.get("connected") is False
    assert out.get("code") == "SIMULATION_MODE"
    assert get_connection_manager().is_production_connected() is False
