import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
os.environ.setdefault("HVAC_START_CONTROL_WORKER", "0")
os.environ.setdefault("HVAC_ALLOW_CREATE_ALL", "1")
# Phase 0: tests never inherit a developer .env that enables the sim feeder or writes.
os.environ["HVAC_USE_SIMULATION"] = "0"
os.environ["HVAC_BMS_WRITE_ENABLED"] = "0"
os.environ["HVAC_ALLOW_SIM_WRITES"] = "0"
os.environ["HVAC_PLANT_MODE_PERSIST"] = "0"
