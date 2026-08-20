"""Inference. Provenance is MODEL PREDICTION or MODEL NOT TRAINABLE — never LIVE_BMS."""
from __future__ import annotations

import pickle
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.ml.features.maps import AGENT_FOR
from database.models_ml import MLAgentPredictionDB, MLModelRegistryDB, MLPredictionDB, MLPredictionFeatureDB
from database.session import SessionLocal

_CACHE: Dict[str, Any] = {}

NO_O10 = "O10 has no ML model."


def _load_artifact(path: str):
    if path in _CACHE:
        return _CACHE[path]
    with open(path, "rb") as fh:
        payload = pickle.load(fh)
    _CACHE[path] = payload
    return payload


def model_status(opportunity_id: str, db=None) -> Dict[str, Any]:
    oid = (opportunity_id or "").strip().upper()
    if oid == "O10":
        return {"opportunity_id": oid, "status": "MODEL_NOT_TRAINABLE", "message": NO_O10, "model": None}
    own = db is None
    session = db or SessionLocal()
    try:
        row = (
            session.query(MLModelRegistryDB)
            .filter(MLModelRegistryDB.opportunity_id == oid, MLModelRegistryDB.status.in_(("MODEL_READY", "REGISTERED")))
            .order_by(MLModelRegistryDB.created_at.desc())
            .first()
        )
        if not row:
            return {"opportunity_id": oid, "status": "MODEL_NOT_AVAILABLE", "model": None}
        return {
            "opportunity_id": oid,
            "status": "MODEL_READY",
            "model": {
                "model_id": row.id,
                "model_version": row.model_version,
                "model_type": row.model_type,
                "features": row.features_json,
                "target": row.target_json,
                "training_dataset_id": row.training_dataset_id,
                "artifact_path": row.artifact_path,
            },
        }
    finally:
        if own:
            session.close()


def list_models(db=None) -> list:
    own = db is None
    session = db or SessionLocal()
    try:
        rows = session.query(MLModelRegistryDB).all()
        by_oid = {r.opportunity_id: r for r in rows if r.status in ("MODEL_READY", "REGISTERED")}
        out = []
        from backend.ml.features.maps import maps_for_opportunity

        official = [f"O{i}" for i in range(1, 21)]
        for oid in official:
            if oid == "O10":
                out.append({"opportunity_id": "O10", "agent_id": "ventilation", "status": "MODEL_NOT_TRAINABLE", "model_id": None, "model_version": None})
                continue
            row = by_oid.get(oid)
            maps = maps_for_opportunity(oid)
            trainable = any(m.get("training_allowed") for m in maps)
            if row:
                out.append(
                    {
                        "opportunity_id": oid,
                        "agent_id": row.agent_id,
                        "status": "MODEL_READY",
                        "model_id": row.id,
                        "model_version": row.model_version,
                        "training_dataset_id": row.training_dataset_id,
                    }
                )
            elif not trainable:
                out.append(
                    {
                        "opportunity_id": oid,
                        "agent_id": AGENT_FOR.get(oid),
                        "status": "MODEL_NOT_TRAINABLE",
                        "model_id": None,
                        "model_version": None,
                    }
                )
            else:
                out.append(
                    {
                        "opportunity_id": oid,
                        "agent_id": AGENT_FOR.get(oid),
                        "status": "MODEL_NOT_AVAILABLE",
                        "model_id": None,
                        "model_version": None,
                    }
                )
        return out
    finally:
        if own:
            session.close()


def predict(opportunity_id: str, features: Optional[Dict[str, Any]] = None, agent_id: Optional[str] = None, building_id: Optional[str] = None, persist: bool = True) -> Dict[str, Any]:
    oid = (opportunity_id or "").strip().upper()
    feats = features or {}
    if oid == "O10":
        return {
            "status": "MODEL_NOT_TRAINABLE",
            "opportunity_id": "O10",
            "model_id": None,
            "prediction": None,
            "confidence": None,
            "provenance": "NO DATA",
            "training_dataset": None,
            "engineering_validation": NO_O10,
            "source": "ML_MODEL",
        }
    info = model_status(oid)
    if info["status"] != "MODEL_READY":
        return {
            "status": "MODEL_NOT_AVAILABLE" if info["status"] == "MODEL NOT AVAILABLE" else info["status"],
            "opportunity_id": oid,
            "model_id": None,
            "prediction": None,
            "confidence": None,
            "provenance": "NO DATA",
            "training_dataset": None,
            "engineering_validation": "No registered model with validation metrics.",
            "source": "ML_MODEL",
        }
    model_row = info["model"]
    try:
        artifact = _load_artifact(model_row["artifact_path"])
    except OSError:
        return {
            "status": "MODEL_NOT_AVAILABLE",
            "opportunity_id": oid,
            "model_id": model_row["model_id"],
            "prediction": None,
            "confidence": None,
            "provenance": "NO DATA",
            "training_dataset": model_row.get("training_dataset_id"),
            "engineering_validation": "Artifact missing.",
            "source": "ML_MODEL",
        }
    names = artifact["features"]
    vec = []
    missing = []
    used = []
    for name in names:
        raw = feats.get(name)
        if raw is None:
            missing.append(name)
            continue
        try:
            vec.append(float(raw))
            used.append({"feature": name, "value": float(raw)})
        except (TypeError, ValueError):
            missing.append(name)
    if missing:
        return {
            "status": "INSUFFICIENT_FEATURES",
            "opportunity_id": oid,
            "model_id": model_row["model_id"],
            "prediction": None,
            "confidence": None,
            "provenance": "NO DATA",
            "training_dataset": model_row.get("training_dataset_id"),
            "engineering_validation": f"Missing features: {missing}",
            "source": "ML_MODEL",
            "missing_features": missing,
        }
    import numpy as np

    raw_pred = artifact["model"].predict(np.array([vec], dtype=float))[0]
    task = artifact.get("task_type") or "regression"
    if task == "classification":
        value = int(round(float(raw_pred)))
        proba = None
        if hasattr(artifact["model"], "predict_proba"):
            proba = float(max(artifact["model"].predict_proba(np.array([vec], dtype=float))[0]))
        confidence = proba
        prediction = {"label": value, "value": value}
    else:
        value = float(raw_pred)
        prediction = {"value": value}
        confidence = None
    importance = []
    if hasattr(artifact["model"], "feature_importances_"):
        imps = [float(x) for x in artifact["model"].feature_importances_]
        importance = [{"feature": n, "value": used[i]["value"], "importance": round(imps[i], 4)} for i, n in enumerate(names)]
        importance.sort(key=lambda r: r["importance"], reverse=True)
        # map impurity importance to a bounded confidence proxy only when present
        top = importance[0]["importance"] if importance else 0
        confidence = round(min(0.95, max(0.5, 0.55 + 0.4 * top)), 3) if confidence is None else confidence

    body = {
        "status": "OK",
        "opportunity_id": oid,
        "model_id": model_row["model_id"],
        "model_version": model_row["model_version"],
        "prediction": prediction,
        "confidence": confidence,
        "provenance": "MODEL PREDICTION",
        "training_dataset": model_row.get("training_dataset_id"),
        "engineering_validation": "ML output is a plant-response or classification estimate. Guide/engineering limits still apply. Not LIVE BMS.",
        "source": "ML_MODEL",
        "top_features": importance[:8],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "agent_id": agent_id or AGENT_FOR.get(oid),
        "building_id": building_id,
    }
    if persist:
        session = SessionLocal()
        try:
            pid = f"pred_{uuid.uuid4().hex[:12]}"
            session.add(
                MLPredictionDB(
                    id=pid,
                    opportunity_id=oid,
                    building_id=building_id,
                    model_id=model_row["model_id"],
                    input_json=feats,
                    prediction_json=prediction,
                    confidence=confidence,
                    source="ML_MODEL",
                    provenance="MODEL PREDICTION",
                    status="OK",
                )
            )
            for item in importance[:12]:
                session.add(
                    MLPredictionFeatureDB(
                        id=f"pf_{uuid.uuid4().hex[:10]}",
                        prediction_id=pid,
                        feature=item["feature"],
                        value=item.get("value"),
                        importance=item.get("importance"),
                    )
                )
            session.add(
                MLAgentPredictionDB(
                    id=f"ap_{uuid.uuid4().hex[:10]}",
                    opportunity_id=oid,
                    agent_id=body["agent_id"] or "unknown",
                    prediction_id=pid,
                    recommendation_json=prediction,
                )
            )
            session.commit()
            body["prediction_id"] = pid
        finally:
            session.close()
    return body
