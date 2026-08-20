from backend.agents.opportunities.base_opportunity_agent import AGENT_CLASSES, opportunity_agent_registry
from backend.agents.registry import opportunity_agent
from backend.knowledge.hvac_guide_catalog import CONTROL_KIND, GUIDE_PAGES, catalog_all, catalog_record, is_advisory
from backend.services.hvac_safety_contract import evaluate_dispatch
from backend.services.oeh_guide_catalog import catalog_item


def test_catalog_has_o1_to_o20_with_guide_pages():
    rows = catalog_all()
    assert [r["id"] for r in rows] == [f"O{i}" for i in range(1, 21)]
    assert rows[9]["id"] == "O10"
    assert rows[9]["title"] == "Economy Cycle"
    for row in rows:
        assert row["guide_page"] == GUIDE_PAGES[row["id"]]
        assert row["source_reference"]["document"] == "150317hvacguide.pdf"
        assert row["energy_impact_class"] == "GUIDE_POTENTIAL"
        assert "measured" not in (row["guide_savings_potential"] or "").lower() or "not measured" in (row["guide_savings_potential"] or "").lower()
        assert row["required_inputs"]
        assert row["recommended_control_logic"]
        assert row["risks"]
        assert row["benefits"]


def test_o14_valve_target_and_o15_approach_are_guide_sourced():
    o14 = catalog_record("O14")
    assert "95%" in o14["recommended_control_logic"]
    assert o14["guide_page"] == 67
    o15 = catalog_record("O15")
    assert "8–12°C" in o15["recommended_control_logic"] or "8-12" in o15["recommended_control_logic"]
    o10 = catalog_record("O10")
    assert "enthalpy" in o10["recommended_control_logic"].lower()


def test_oeh_catalog_item_includes_source_reference():
    item = catalog_item("O10")
    assert item["source_reference"]["page"] == 49
    assert item["control_kind"] == "control"
    assert catalog_item("O17")["control_kind"] == "advisory"


def test_registry_class_names_and_advisory_dispatch_block():
    assert set(AGENT_CLASSES) == {f"O{i}" for i in range(1, 21)}
    assert opportunity_agent("O1").class_name == "OptimumStartStopAgent"
    assert opportunity_agent("O10").class_name == "EconomyCycleAgent"
    assert opportunity_agent("O15").class_name == "AirCooledHeadPressureAgent"
    assert is_advisory("O17") and CONTROL_KIND["O9"] == "advisory"
    blocked = opportunity_agent_registry.get("O20").prepare_dispatch({"opportunity_id": "O20"})
    assert blocked["allowed"] is False
    assert blocked["code"] == "ADVISORY_ONLY"


def test_control_agent_prepare_dispatch_uses_safety_contract():
    ctx = {
        "opportunity_id": "O14",
        "source": "SIMULATION",
        "telemetry": {"source": "SIMULATION", "quality": "GOOD", "age_seconds": 1},
        "supervisory": {"decision": "OPTIMIZE", "confidence": 0.99},
        "safety": {"status": "PASS"},
        "current_value": 1,
        "target_value": 2,
    }
    ok, _, classified = evaluate_dispatch(ctx)
    assert ok is False
    gate = opportunity_agent("O14").prepare_dispatch(ctx)
    assert gate["allowed"] is False
    assert gate["code"] != "PASS"


def test_explain_does_not_invent_engineering_step():
    explained = opportunity_agent_registry.get("O10").explain(
        {
            "decision": "WAIT_FOR_TELEMETRY",
            "current": None,
            "recommended": None,
            "engine": {"current": None},
        }
    )
    step4 = next(s for s in explained["steps"] if s["step"] == 4)
    assert step4["invented"] is False
    assert step4["detail"] is None
    from fastapi.testclient import TestClient
    from backend.main import app

    client = TestClient(app)
    listing = client.get("/api/v1/guide-catalog")
    assert listing.status_code == 200
    ids = [row["opportunity_id"] for row in listing.json()["opportunities"]]
    assert ids == [f"O{i}" for i in range(1, 21)]
    o10 = client.get("/api/v1/guide-catalog/O10")
    assert o10.status_code == 200
    body = o10.json()
    assert body["title"] == "Economy Cycle"
    assert body["guide_page"] == 49
    assert body["energy_impact_class"] == "GUIDE_POTENTIAL"
