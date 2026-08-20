"""Validate O11/O13/O15–O20 persist + live quality gate. Run from repo root."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from database.session import init_db
from backend.services.opportunity_persist_service import (
    ensure_catalog,
    persist_ventilation_points,
    persist_co_measurement,
    persist_vs_points,
    persist_optimization,
    persist_execution,
    get_o11_state,
    get_o13_state,
    get_vs_state,
)
from backend.services.om_persist_service import (
    persist_energy_reading,
    persist_training_program,
    persist_training_completion,
    persist_work_order,
    persist_controller,
    get_o17_state,
    get_o18_state,
    get_o19_state,
    get_o20_state,
)


def main():
    init_db()
    ensure_catalog()

    persist_ventilation_points(
        "O11",
        "AHU-01",
        [{"sensor_type": "OA_DAMPER", "value": 80, "unit": "%", "quality": "GOOD", "source": "BACnet_IP"}],
    )
    persist_optimization("O11", {"current_value": 20, "optimized_value": 80, "energy_impact": 2.1, "confidence": 0.9, "reason": "Night purge OA open", "status": "PROPOSED"})
    persist_execution("O11", "O11_AGENT")
    s11 = get_o11_state()
    assert s11["live"] and s11["telemetry"]["OA_DAMPER"]["value"] == 80

    persist_ventilation_points(
        "O11",
        "AHU-01",
        [{"sensor_type": "ZONE_TEMP", "value": 99, "unit": "C", "quality": "STALE", "source": "BACnet_IP"}],
    )
    s11b = get_o11_state()
    assert "ZONE_TEMP" not in s11b["telemetry"]

    persist_co_measurement({"zone_id": "PARK-L1", "co_ppm": 12.5, "quality": "GOOD", "source": "BACnet_IP", "co_trend": "STABLE"})
    persist_optimization("O13", {"current_value": 12.5, "optimized_value": 35, "status": "PROPOSED"})
    s13 = get_o13_state()
    assert s13["live"] and s13["co"]["co_ppm"] == 12.5

    persist_vs_points("O15", "ACC-01", [{"point_name": "HEAD_PRESSURE", "value": 210, "unit": "psig", "quality": "GOOD"}])
    persist_optimization("O15", {"current_value": 210, "optimized_value": 180, "status": "PROPOSED"})
    assert get_vs_state("O15")["live"]

    persist_vs_points("O16", "CH-1", [{"point_name": "CEWT", "value": 29.4, "unit": "C", "quality": "GOOD"}])
    persist_optimization("O16", {"current_value": 29.4, "optimized_value": 27.0, "status": "PROPOSED"})
    assert get_vs_state("O16")["live"]

    persist_energy_reading({"meter_id": "MAIN-ELEC-METER", "power_kw": 312.0, "quality": "GOOD"})
    assert get_o17_state()["live"]
    persist_energy_reading({"meter_id": "MAIN-ELEC-METER", "power_kw": 1.0, "quality": "STALE", "source": "SIMULATION"})
    # live still from GOOD row
    assert get_o17_state()["power_kw"] == 312.0

    pid = persist_training_program({"id": "TRN-O18-1", "topic": "Night purge", "program_name": "O18 awareness", "required": True})
    persist_training_completion({"program_id": pid, "role_label": "OPERATOR", "completion_pct": 100, "status": "COMPLETED"})
    assert get_o18_state()["live"]

    persist_work_order({"equipment_id": "CH-1", "maintenance_type": "COIL_CLEAN", "status": "OPEN", "priority": "HIGH", "efficiency": 0.58})
    assert get_o19_state()["live"]

    persist_controller({"controller_id": "N2-AHU-01", "software_version": "3.2.1", "firmware_version": "1.8", "comm_status": "ONLINE", "health_status": "HEALTHY", "point_quality": "GOOD"})
    assert get_o20_state()["live"]

    _alembic_roundtrip()
    _smoke_existing_apis()

    print("PASS: O11 O13 O15 O16 O17 O18 O19 O20 persist; STALE/SIMULATION excluded from live KPIs")


def _alembic_roundtrip() -> None:
    import shutil
    from alembic import command
    from alembic.config import Config

    src = os.path.join(ROOT, "database", "hvac_supervisory.db")
    copy = os.path.join(ROOT, "database", "_migtest_o11_o20.db")
    shutil.copy2(src, copy)
    try:
        cfg = Config(os.path.join(ROOT, "alembic.ini"))
        cfg.set_main_option("script_location", os.path.join(ROOT, "alembic"))
        url = "sqlite:///" + copy.replace("\\", "/")
        cfg.set_main_option("sqlalchemy.url", url)
        command.downgrade(cfg, "0001_baseline")
        command.upgrade(cfg, "head")
    finally:
        if os.path.exists(copy):
            os.remove(copy)


def _smoke_existing_apis() -> None:
    backend_dir = os.path.join(ROOT, "backend")
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from backend.api.routes import router as api_router
    from backend.api.hvac_ventilation_controller import router as vent
    from backend.api.variable_speed_controller import router as vs
    from backend.api.hvac_operations_maintenance_controller import router as om
    from backend.api.plant_control_controller import router as pc

    app = FastAPI()
    app.include_router(api_router, prefix="/api")
    app.include_router(vent)
    app.include_router(vs)
    app.include_router(om)
    app.include_router(pc)
    client = TestClient(app)
    paths = [
        "/api/status",
        "/api/agents/scheduling/o1/state",
        "/api/agents/scheduling/o2/state",
        "/api/agents/scheduling/o3/state",
        "/api/agents/scheduling/o4/state",
        "/api/agents/plant-control/o5/state",
        "/api/agents/plant-control/o6/state",
        "/api/agents/plant-control/o7/state",
        "/api/agents/plant-control/o8/state",
        "/api/agents/plant-control/o9/state",
        "/api/hvac/ventilation/opportunities",
        "/api/hvac/ventilation/O11",
        "/api/hvac/ventilation/O13",
        "/api/variable-speed/dashboard",
        "/api/variable-speed/chw-pump",
        "/api/hvac/operations-maintenance/dashboard",
        "/api/variable-speed/o15/state",
        "/api/variable-speed/o16/state",
        "/api/hvac/operations-maintenance/O17",
        "/api/hvac/operations-maintenance/O18",
        "/api/hvac/operations-maintenance/O19",
        "/api/hvac/operations-maintenance/O20",
    ]
    for path in paths:
        res = client.get(path)
        assert res.status_code == 200, f"{path} -> {res.status_code} {res.text[:200]}"


if __name__ == "__main__":
    main()
