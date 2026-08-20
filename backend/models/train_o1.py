"""
Training Pipeline for Opportunity 1: O1ThermalResponseModel
Metrics are computed from held-out evaluation only. Never floor or invent R².
"""
import os
import json
from backend.models.registry import model_registry
from backend.services.o1_model_service import train_from_records

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
TRAIN_FILE = os.path.join(DATA_DIR, "training", "o1_training.jsonl")
EVAL_FILE = os.path.join(DATA_DIR, "evaluation", "o1_evaluation.jsonl")
O1_TRAIN = os.path.join(DATA_DIR, "o1", "train", "samples.jsonl")


def load_dataset(filepath: str):
    if not os.path.exists(filepath):
        return []
    records = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def _normalize(r: dict) -> dict:
    zt = r.get("zone_temperature", r.get("initial_zone_temp", r.get("initial_temp")))
    tgt = r.get("comfort_target", r.get("target_temp", r.get("target_temperature")))
    oat = r.get("outdoor_air_temperature", r.get("oat"))
    ttt = r.get("time_to_target_minutes", r.get("actual_warmup_duration_min", r.get("pulldown_duration_min")))
    return {
        "zone_temperature": zt,
        "comfort_target": tgt,
        "outdoor_air_temperature": oat,
        "time_to_target_minutes": ttt,
        "source": r.get("source", "SIMULATED"),
    }


def train_o1_model() -> dict:
    print("[Training O1] Loading datasets (labeled SIMULATED unless metadata says otherwise)...")
    raw = load_dataset(O1_TRAIN) or (load_dataset(TRAIN_FILE) + load_dataset(EVAL_FILE))
    records = [_normalize(r) for r in raw]
    result = train_from_records(records, dataset_version="o1-simulated-jsonl")
    if result.get("status") == "MODEL_NOT_READY":
        print(f"[Training O1] MODEL_NOT_READY: {result.get('reason')}")
        return result
    model_registry.register_model(
        opp_code="O1",
        version=result.get("model_version") or "unversioned",
        dataset_version="o1-simulated-jsonl",
        metrics={
            "mae_warmup_minutes": result.get("mae_minutes"),
            "r2_score": result.get("r2_score"),
            "rmse_minutes": result.get("rmse_minutes"),
            "training_samples": result.get("sample_count"),
        },
        parameters={},
        is_active=result.get("status") == "ACTIVE",
    )
    return result


if __name__ == "__main__":
    train_o1_model()
