"""Seed ML registry + demo pickle artifacts for simulation hosts.

Agent Centre reads model_type from ml_model_registry. Hosted demos have no Kaggle
archives, so train_all never runs — this fills trainable O's with a tiny
pickled predictor so /predict does not return "Artifact missing".
Never invents models for O10 / O13 / O18 / O20 (MODEL_NOT_TRAINABLE).
"""
from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import List

from backend.ml.features.maps import AGENT_FOR, trainable_maps
from backend.ml.paths import ARTIFACT_DIR
from database.models_ml import MLModelRegistryDB
from database.session import SessionLocal

_DEMO_ALGO = "RandomForest"


class _DemoPredictModel:
    """Minimal sklearn-free stand-in. Predicts from feature means only."""

    def __init__(self, task_type: str = "regression"):
        self.task_type = task_type
        self.feature_importances_ = None

    def predict(self, X):
        rows = X.tolist() if hasattr(X, "tolist") else list(X)
        out: List[float] = []
        for row in rows:
            vals = [float(x) for x in row]
            mean = sum(vals) / max(len(vals), 1)
            if self.task_type == "classification":
                out.append(1.0 if mean >= 0 else 0.0)
            else:
                out.append(round(mean * 0.08, 4))
        return out

    def predict_proba(self, X):
        preds = self.predict(X)
        return [[1.0 - p, p] if p <= 1.0 else [0.0, 1.0] for p in preds]


def _sim_on() -> bool:
    if os.getenv("HVAC_USE_SIMULATION", "0").strip() not in ("1", "true", "TRUE"):
        return False
    try:
        from backend.bms.connection_manager import is_simulation_mode

        return is_simulation_mode()
    except Exception:
        return False


def _write_demo_artifact(oid: str, features: List[str], task_type: str) -> str:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTIFACT_DIR / f"mdl-{oid.lower()}-demo.pkl"
    model = _DemoPredictModel(task_type=task_type or "regression")
    n = max(len(features), 1)
    model.feature_importances_ = [round(1.0 / n, 4)] * n
    payload = {
        "model": model,
        "features": list(features),
        "target": None,
        "task_type": task_type or "regression",
        "feature_map": {},
        "demo": True,
    }
    with path.open("wb") as fh:
        pickle.dump(payload, fh)
    return str(path)


def _artifact_ok(path: Optional[str]) -> bool:
    if not path:
        return False
    try:
        return Path(path).is_file()
    except OSError:
        return False


def ensure_demo_ml_models(db=None, force: bool = False) -> int:
    """Insert/repair MODEL_READY demo rows with on-disk pickle artifacts.

    Skips opportunities that already have a ready model with a real artifact
    (keeps train_all outputs). Returns number of rows inserted or repaired.
    """
    if not force and not _sim_on():
        return 0
    own = db is None
    session = db or SessionLocal()
    touched = 0
    try:
        for mapping in trainable_maps():
            oid = mapping["opportunity_id"]
            mid = f"mdl-{oid.lower()}-demo"
            names = list((mapping.get("feature_map") or {}).keys())
            task = str(mapping.get("task_type") or "regression")
            path = _write_demo_artifact(oid, names, task)

            row = session.query(MLModelRegistryDB).filter_by(id=mid).first()
            if row:
                if not _artifact_ok(row.artifact_path):
                    row.artifact_path = path
                    row.status = "MODEL_READY"
                    row.model_type = _DEMO_ALGO
                    row.features_json = names
                    touched += 1
                continue

            other = (
                session.query(MLModelRegistryDB)
                .filter(
                    MLModelRegistryDB.opportunity_id == oid,
                    MLModelRegistryDB.status.in_(("MODEL_READY", "REGISTERED")),
                )
                .order_by(MLModelRegistryDB.created_at.desc())
                .first()
            )
            if other and _artifact_ok(other.artifact_path) and other.id != mid:
                continue

            session.add(
                MLModelRegistryDB(
                    id=mid,
                    opportunity_id=oid,
                    agent_id=AGENT_FOR.get(oid) or mapping.get("agent_id") or "unknown",
                    model_type=_DEMO_ALGO,
                    model_version=f"{oid}-demo-v1",
                    features_json=names,
                    target_json={
                        "column": mapping.get("target_column"),
                        "task": mapping.get("task_type"),
                    },
                    artifact_path=path,
                    training_dataset_id=mapping.get("dataset_id"),
                    status="MODEL_READY",
                )
            )
            touched += 1
        if touched:
            session.commit()
        return touched
    except Exception:
        if own:
            try:
                session.rollback()
            except Exception:
                pass
        raise
    finally:
        if own:
            session.close()
