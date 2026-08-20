"""Generate SIMULATED O1 thermal-response datasets. Never labeled as live BMS."""
from __future__ import annotations

import argparse
import json
import os
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "data", "o1")

SCENARIOS = (
    "hot_morning",
    "mild_morning",
    "cool_morning",
    "high_mass",
    "low_mass",
    "occupied_early",
    "stale_sensor",
    "missing_sensor",
    "weekend",
    "holiday",
    "hvac_unavailable",
)


def _ttt(zone: float, target: float, oat: float, mass: float) -> float:
    delta = max(0.0, zone - target)
    return round(delta * (12.0 + mass * 4.0) + max(0.0, oat - 22.0) * 1.6 + 6.0, 1)


def _row(rng: random.Random, scenario: str, i: int) -> Dict[str, Any]:
    base = datetime(2026, 6, 1, 5, 0) + timedelta(days=i)
    oat = 28.0
    zone = 25.5
    mass = 0.5
    missing = None
    quality = "GOOD"
    avail = 1.0
    occ_start = "08:00"
    if scenario == "hot_morning":
        oat, zone = 34.0 + rng.uniform(-1, 1), 27.0 + rng.uniform(-0.4, 0.4)
    elif scenario == "mild_morning":
        oat, zone = 24.0 + rng.uniform(-1, 1), 24.2 + rng.uniform(-0.3, 0.3)
    elif scenario == "cool_morning":
        oat, zone = 16.0 + rng.uniform(-1, 1), 22.8 + rng.uniform(-0.3, 0.3)
    elif scenario == "high_mass":
        mass = 1.0
        oat, zone = 30.0, 26.0
    elif scenario == "low_mass":
        mass = 0.15
        oat, zone = 30.0, 25.5
    elif scenario == "occupied_early":
        occ_start = "07:00"
    elif scenario == "stale_sensor":
        quality = "STALE"
    elif scenario == "missing_sensor":
        missing = "ZONE_TEMP"
    elif scenario == "weekend":
        base = base + timedelta(days=(5 - base.weekday()) % 7)
    elif scenario == "holiday":
        occ_start = "00:00"
    elif scenario == "hvac_unavailable":
        avail = 0.0
    target = 22.5
    ttt = None if missing == "ZONE_TEMP" else _ttt(zone, target, oat, mass) + rng.uniform(-2, 2)
    if ttt is not None:
        ttt = max(0.0, ttt)
    return {
        "sample_id": f"o1-{scenario}-{i:04d}",
        "timestamp": base.isoformat(),
        "source": "SIMULATED",
        "environment": "development",
        "scenario": scenario,
        "building_id": "bldg-corp-hq-01",
        "zone_id": "ZONE-AVG",
        "scheduled_start": "06:00",
        "occupancy_start": occ_start,
        "occupancy_end": "18:00",
        "zone_temperature": None if missing == "ZONE_TEMP" else round(zone, 2),
        "comfort_target": target,
        "outdoor_air_temperature": round(oat, 2),
        "solar_w_m2": round(max(0.0, 180 + rng.uniform(-40, 80)), 1),
        "quality": quality,
        "equip_avail": avail,
        "time_to_target_minutes": None if ttt is None else round(ttt, 1),
        "mass_factor": mass,
    }


def generate(seed: int = 42, n_per: int = 40) -> Dict[str, List[Dict[str, Any]]]:
    rng = random.Random(seed)
    all_rows: List[Dict[str, Any]] = []
    for sc in SCENARIOS:
        for i in range(n_per):
            all_rows.append(_row(rng, sc, i))
    rng.shuffle(all_rows)
    n = len(all_rows)
    n_train = int(n * 0.7)
    n_val = int(n * 0.15)
    return {
        "train": all_rows[:n_train],
        "validation": all_rows[n_train : n_train + n_val],
        "test": all_rows[n_train + n_val :],
        "simulated": all_rows,
    }


def write_split(name: str, rows: List[Dict[str, Any]], seed: int) -> None:
    d = os.path.join(OUT, name)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "samples.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    meta = {
        "source": "SIMULATED",
        "environment": "development",
        "seed": seed,
        "split": name,
        "row_count": len(rows),
        "target": "time_to_target_minutes",
        "building_id": "bldg-corp-hq-01",
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
    with open(os.path.join(d, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-per-scenario", type=int, default=40)
    args = p.parse_args()
    splits = generate(args.seed, args.n_per_scenario)
    for name, rows in splits.items():
        write_split(name, rows, args.seed)
    print(f"Wrote SIMULATED O1 datasets under {OUT}")


if __name__ == "__main__":
    main()
