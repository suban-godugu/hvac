"""Register archives, train legitimate maps, dump an honest validation report."""
from __future__ import annotations

import json
import os
from pathlib import Path

os.environ["HVAC_START_CONTROL_WORKER"] = "0"

from database.session import init_db
from backend.ml.features.maps import OPPORTUNITY_MAPS, trainable_maps
from backend.ml.prediction.service import predict, list_models
from backend.ml.registry.service import list_datasets, opportunity_health, register_datasets
from backend.ml.training.pipeline import train_all

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "scratch" / "ml_validation_report.json"


def main() -> None:
    init_db()
    registered = register_datasets()
    runs = train_all()
    health = opportunity_health()
    models = list_models()
    ready = [m["opportunity_id"] for m in models if m.get("status") == "MODEL_READY"]
    predict_tests = []
    for oid in ready:
        row = next(r for r in health["opportunities"] if r["opportunity_id"] == oid)
        fmap = row.get("feature_map") or {}
        features = {k: 1.0 for k in fmap}
        body = predict(oid, features=features, persist=True)
        predict_tests.append(
            {
                "opportunity_id": oid,
                "status": body.get("status"),
                "provenance": body.get("provenance"),
                "source": body.get("source"),
                "has_prediction": body.get("prediction") is not None,
            }
        )
        miss = predict(oid, features={}, persist=False)
        predict_tests.append(
            {
                "opportunity_id": oid,
                "case": "missing_features",
                "status": miss.get("status"),
                "prediction": miss.get("prediction"),
            }
        )
    not_train = predict("O10", features={}, persist=False)
    report = {
        "datasets_registered": registered,
        "datasets_skipped_or_duplicate": [r for r in registered if r["status"] in ("SKIPPED_EMPTY", "DUPLICATE", "MISSING_PATH")],
        "trainable_maps": [
            {"opportunity_id": m["opportunity_id"], "dataset_id": m["dataset_id"], "target": m["target_column"]}
            for m in trainable_maps()
        ],
        "mapping_matrix": [
            {
                "opportunity_id": f"O{i}",
                "maps": [
                    {
                        "dataset_id": m["dataset_id"],
                        "target": m.get("target_column"),
                        "training_allowed": m["training_allowed"],
                        "status": m["status"],
                    }
                    for m in OPPORTUNITY_MAPS
                    if m["opportunity_id"] == f"O{i}"
                ],
            }
            for i in range(1, 21)
        ],
        "training_runs": runs,
        "health": health,
        "predict_tests": predict_tests,
        "o10_predict": {"status": not_train.get("status"), "prediction": not_train.get("prediction"), "provenance": not_train.get("provenance")},
    }
    OUT.write_text(json.dumps(report, default=str, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
