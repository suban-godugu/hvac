"""Shared runtime command contract tests."""
from backend.agents.runtime.contracts import CommandContract
from backend.agents.runtime.coordinator import resolve
from backend.services.hvac_safety_contract import evaluate_dispatch


def test_command_contract_fields():
    c = CommandContract(
        opportunity="O1",
        building="bldg-corp-hq-01",
        equipment="AHU-1",
        point="AHU-1-SAT-SP",
        old_value=14.0,
        new_value=13.5,
        reason="test",
        command_id="cmd_test",
        requested_by="engineer",
    )
    d = c.as_dict()
    assert d["opportunity"] == "O1"
    assert d["command_id"] == "cmd_test"


def test_coordinator_allows_empty_point():
    assert resolve({}).get("action") == "ALLOW"


def test_o18_never_dispatches():
    ok, _, classified = evaluate_dispatch(
        {
            "telemetry": {"quality": "GOOD", "age_seconds": 1, "source": "LIVE_BMS", "raw": "LIVE"},
            "source": "LIVE_BMS",
            "supervisory": {"decision": "OPTIMIZE", "confidence": 0.99},
            "safety": {"status": "PASS"},
            "current_value": 1,
            "target_value": 2,
            "user": {"role": "engineer"},
            "approval_status": "APPROVED",
            "opportunity_id": "O18",
        }
    )
    assert ok is False
    assert classified.get("code") == "ADVISORY"
