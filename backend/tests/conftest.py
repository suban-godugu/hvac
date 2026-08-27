import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
os.environ.setdefault("HVAC_START_CONTROL_WORKER", "0")
os.environ.setdefault("HVAC_ALLOW_CREATE_ALL", "1")
# Phase 0: tests never inherit a developer .env that enables the sim feeder or writes.
os.environ["HVAC_USE_SIMULATION"] = "0"
os.environ["HVAC_BMS_WRITE_ENABLED"] = "0"
os.environ["HVAC_ALLOW_SIM_WRITES"] = "0"
os.environ["HVAC_PLANT_MODE_PERSIST"] = "0"


@pytest.fixture(autouse=True)
def _stop_background_feeders():
    """Lifespan starts reader/sim threads; stop them so suites do not leak into later tests."""
    os.environ["HVAC_PLANT_MODE_PERSIST"] = "0"
    os.environ["HVAC_USE_SIMULATION"] = "0"
    os.environ["HVAC_ALLOW_SIM_WRITES"] = "0"
    os.environ["HVAC_BMS_WRITE_ENABLED"] = "0"
    yield
    try:
        from backend.bms.telemetry_reader import stop_reader

        stop_reader()
    except Exception:
        pass
    try:
        from backend.bms.simulation_telemetry import stop_simulation_telemetry

        stop_simulation_telemetry()
    except Exception:
        pass
