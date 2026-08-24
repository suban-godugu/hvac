"""Seed ML registry labels for demo/simulation when archives are not on the host.

Agent Centre reads model_type from ml_model_registry. Vercel has no Kaggle
archives under /tmp, so train_all never runs — this fills trainable O's only.
Never invents models for O10 / O13 / O18 / O20 (MODEL_NOT_TRAINABLE).
"""
from __future__ import annotations

import os
from backend.ml.features.maps import AGENT_FOR, trainable_maps
from database.models_ml import MLModelRegistryDB
from database.session import SessionLocal

_DEMO_ALGO = "RandomForest"


def _sim_on() -> bool:
    if os.getenv("HVAC_USE_SIMULATION", "0").strip() not in ("1", "true", "TRUE"):
        return False
    try:
        from backend.bms.connection_manager import is_simulation_mode

        return is_simulation_mode()
    except Exception:
        return False


def ensure_demo_ml_models(db=None, force: bool = False) -> int:
    """Insert MODEL_READY registry rows for trainable maps when missing.

    Skips opportunities that already have a ready/registered model (keeps
    real train_all artifacts). Returns number of rows inserted.
    """
    if not force and not _sim_on():
        return 0
    own = db is None
    session = db or SessionLocal()
    inserted = 0
    try:
        existing = {
            r.opportunity_id
            for r in session.query(MLModelRegistryDB)
            .filter(MLModelRegistryDB.status.in_(("MODEL_READY", "REGISTERED")))
            .all()
        }
        for mapping in trainable_maps():
            oid = mapping["opportunity_id"]
            if oid in existing:
                continue
            mid = f"mdl-{oid.lower()}-demo"
            if session.query(MLModelRegistryDB).filter_by(id=mid).first():
                continue
            names = list((mapping.get("feature_map") or {}).keys())
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
                    artifact_path=None,
                    training_dataset_id=mapping.get("dataset_id"),
                    status="MODEL_READY",
                )
            )
            inserted += 1
            existing.add(oid)
        if inserted:
            session.commit()
        return inserted
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
