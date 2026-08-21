from backend.services.oeh_guide_catalog import catalog_item, catalog_list, normalize_oid
from backend.services.oeh_guide_service import evaluate_guide
from backend.services.hvac_safety_contract import classify_ui_state, evaluate_dispatch


def test_catalog_is_o1_to_o20_separate_o6_o7_o8():
    ids = [row["opportunity_id"] for row in catalog_list()]
    assert ids == [f"O{i}" for i in range(1, 21)]
    assert "O6-O8" not in ids
    assert normalize_oid("O6-O8") is None
    assert normalize_oid("o7") == "O7"


def test_evaluate_stamps_official_id_and_never_live():
    for oid in ("O1", "O6", "O7", "O8", "O10", "O14", "O18"):
        out = evaluate_guide(oid, {})
        assert out["opportunity_id"] == oid
        assert out["agent"]["opportunity_id"] == oid
        assert out["live"] is False
        assert out["provenance"] != "LIVE"
        assert out["dispatch_allowed"] is False
        assert out["series"]
        assert out["source"] == "SIMULATION"


def test_o2_copy_and_metric_labels():
    item = catalog_item("O2")
    assert item["pct"] == 20
    assert "dead band" in item["summary"].lower()
    out = evaluate_guide("O2", {})
    labels = {m["label"] for m in out["metrics"]}
    assert "Est. HVAC energy cut" in labels
    o1 = {m["label"] for m in evaluate_guide("O1", {})["metrics"]}
    assert "Operating hours cut" in o1


def test_guide_evaluate_cannot_pass_dispatch_gate():
    out = evaluate_guide("O10", {"oatMean": 16, "dewPoint": 8})
    ok, _, classified = evaluate_dispatch(
        {
            "opportunity_id": "O10",
            "source": out["source"],
            "telemetry": {"source": "SIMULATION", "quality": "GOOD", "age_seconds": 1, "raw": "SIMULATION"},
            "supervisory": {"decision": "OPTIMIZE", "confidence": 0.99},
            "safety": {"status": "PASS"},
            "current_value": 1,
            "target_value": 2,
        }
    )
    assert ok is False
    assert classified.get("status") != "LIVE"


def test_ui_state_not_live_when_bms_offline(monkeypatch):
    monkeypatch.setattr("backend.services.hvac_safety_contract.production_bms_connected", lambda: False)
    assert classify_ui_state(live=True, source="LIVE_BMS", classified_status="LIVE") == "NO_DATA"
    assert classify_ui_state(live=True, source="SIMULATION", classified_status="LIVE") == "SIMULATION"
    assert classify_ui_state(live=False, source=None, classified_status=None) == "NO_DATA"


def test_guide_http_o15_o16_and_list():
    from fastapi.testclient import TestClient
    from backend.main import app

    client = TestClient(app)
    listing = client.get("/api/v1/oeh-guide")
    assert listing.status_code == 200
    ids = [row["opportunity_id"] for row in listing.json()["opportunities"]]
    assert ids == [f"O{i}" for i in range(1, 21)]
    for oid in ("O1", "O15", "O16", "O20"):
        cat = client.get(f"/api/v1/oeh-guide/{oid}")
        assert cat.status_code == 200, oid
        ev = client.post(f"/api/v1/oeh-guide/{oid}/evaluate", json={"sliders": {}})
        assert ev.status_code == 200, oid
        body = ev.json()
        assert body["opportunity_id"] == oid
        assert body["live"] is False
        assert body["series"]
