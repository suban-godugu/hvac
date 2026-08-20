"""Development-only O1 seed. source=SIMULATED, environment=development. Not production telemetry."""
from __future__ import annotations

import os
import random
import sys
from datetime import datetime, timedelta

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from database.session import init_db, SessionLocal
from backend.services.o1_telemetry_service import ensure_point_map_and_config, ingest_samples
from backend.services.o1_pipeline import run_daily
from backend.services.o1_model_service import train_from_records
try:
    from scripts.o1.generate_dataset import generate
except ImportError:
    from generate_dataset import generate


SCENARIO_SAMPLES = {
    "NORMAL": {"ZONE_TEMP": 25.4, "OAT": 29.0, "OA_RH": 55, "SOLAR": 420, "ALARM": 0, "EQUIP_AVAIL": 1, "AHU_STATUS": 1},
    "HOT_DAY": {"ZONE_TEMP": 27.8, "OAT": 34.5, "OA_RH": 40, "SOLAR": 780, "ALARM": 0, "EQUIP_AVAIL": 1, "AHU_STATUS": 1},
    "STALE_TELEMETRY": {"ZONE_TEMP": 25.0, "OAT": 28.0, "OA_RH": 50, "SOLAR": 300, "ALARM": 0, "EQUIP_AVAIL": 1, "AHU_STATUS": 1},
    "SAFETY_BLOCK": {"ZONE_TEMP": 25.2, "OAT": 30.0, "OA_RH": 60, "SOLAR": 400, "ALARM": 1, "EQUIP_AVAIL": 0, "AHU_STATUS": 0},
}


def _ingest(scenario: str, values: dict) -> None:
    ts = datetime.utcnow()
    if scenario == "STALE_TELEMETRY":
        ts = datetime.utcnow() - timedelta(hours=2)
    samples = []
    for sig, val in values.items():
        samples.append({
            "signal": sig,
            "value": val,
            "quality": "GOOD",
            "source": "SIMULATED",
            "timestamp": ts,
        })
    ingest_samples(samples, source="SIMULATED")


def seed_o1_dev(scenario: str = "NORMAL") -> dict:
    random.seed(42)
    init_db()
    ensure_point_map_and_config()
    splits = generate(42, 24)
    labeled = [r for r in splits["train"] if r.get("time_to_target_minutes") is not None]
    train_from_records(labeled, dataset_version="o1-dev-simulated")
    values = SCENARIO_SAMPLES.get(scenario, SCENARIO_SAMPLES["NORMAL"])
    _ingest(scenario, values)
    sim_state = {
        "weather": {"oat": values["OAT"], "humidity": values.get("OA_RH"), "solar_irradiance": values.get("SOLAR")},
        "zones": [{"temperature": values["ZONE_TEMP"]}],
    }
    result = run_daily(sim_state, persist_sim=True, verify=False)
    result["environment"] = "development"
    result["source"] = "SIMULATED"
    result["scenario"] = scenario
    return result


if __name__ == "__main__":
    sc = sys.argv[1] if len(sys.argv) > 1 else "NORMAL"
    out = seed_o1_dev(sc)
    print(out.get("status"), out.get("run_id"), out.get("savings"))
