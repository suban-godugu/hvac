"""O1 model registry and training. Metrics come from evaluation only; never invent R²."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

from database.session import SessionLocal
from database.models_o1 import O1ModelDB, O1ModelTrainingRunDB

ARTIFACT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend", "models", "o1"))


def get_active_model() -> Optional[Dict[str, Any]]:
    db = SessionLocal()
    try:
        row = db.query(O1ModelDB).filter(O1ModelDB.status == "ACTIVE").order_by(O1ModelDB.activated_at.desc()).first()
        if not row:
            return None
        if row.mae_minutes is None and row.r2_score is None:
            return {
                "status": "MODEL_NOT_READY",
                "version": row.version,
                "reason": "Active model has no evaluation metrics.",
            }
        return {
            "status": "ACTIVE",
            "version": row.version,
            "model_version": row.version,
            "r2_score": row.r2_score,
            "mae_minutes": row.mae_minutes,
            "rmse_minutes": row.rmse_minutes,
            "sample_count": row.sample_count,
            "parameters": row.parameters or {},
            "training_dataset": row.dataset_version,
            "prediction_confidence_pct": None if row.mae_minutes is None else round(max(0.0, 100.0 - float(row.mae_minutes) * 4), 1),
        }
    finally:
        db.close()


def predict_time_to_target(zone_temp: Optional[float], target_temp: float, oat: Optional[float], solar: Optional[float] = None) -> Dict[str, Any]:
    if zone_temp is None or oat is None:
        return {"status": "MODEL_NOT_READY", "reason": "Missing ZONE_TEMP or OAT", "time_to_target_minutes": None, "confidence": None}
    active = get_active_model()
    params = (active or {}).get("parameters") or {}
    alpha = float(params.get("alpha_min_per_deg") or params.get("pull_down_rate") or 14.5)
    beta = float(params.get("beta_min_per_deg") or 1.8)
    margin = float(params.get("base_safety_margin_minutes") or 6.0)
    delta = max(0.0, zone_temp - target_temp)
    minutes = delta * alpha + max(0.0, oat - 22.0) * beta + (0.0 if solar is None else (solar / 100.0) * 0.15)
    minutes = min(150.0, max(0.0, minutes))
    conf = None
    version = None
    status = "PHYSICS_FALLBACK"
    if active and active.get("status") == "ACTIVE":
        version = active.get("version")
        status = "OK"
        if active.get("mae_minutes") is not None:
            conf = max(0.4, min(0.99, 1.0 - float(active["mae_minutes"]) / 20.0))
    return {
        "status": status,
        "time_to_target_minutes": round(minutes, 1),
        "confidence": conf,
        "model_version": version,
        "input_quality": "GOOD",
        "prediction_timestamp": datetime.utcnow().isoformat(),
    }


def train_from_records(records: List[Dict[str, Any]], dataset_version: str = "o1-dev") -> Dict[str, Any]:
    """Fit linear model; persist metrics without flooring R²."""
    if len(records) < 8:
        return {"status": "MODEL_NOT_READY", "reason": "Insufficient samples", "sample_count": len(records)}
    n = len(records)
    split = max(4, int(n * 0.7))
    train, test = records[:split], records[split:]
    def xy(rs):
        X, y = [], []
        for r in rs:
            zt = r.get("zone_temperature")
            tgt = r.get("comfort_target") or r.get("target_temperature")
            oat = r.get("outdoor_air_temperature")
            ttt = r.get("time_to_target_minutes")
            if zt is None or tgt is None or oat is None or ttt is None:
                continue
            X.append([float(zt) - float(tgt), float(oat), 1.0])
            y.append(float(ttt))
        return np.array(X), np.array(y)
    Xtr, ytr = xy(train)
    Xte, yte = xy(test)
    if len(ytr) < 5 or len(yte) < 2:
        return {"status": "MODEL_NOT_READY", "reason": "Insufficient labeled features"}
    params, *_ = np.linalg.lstsq(Xtr, ytr, rcond=None)
    pred = Xte @ params
    err = yte - pred
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err ** 2)))
    ss_res = float(np.sum(err ** 2))
    ss_tot = float(np.sum((yte - np.mean(yte)) ** 2)) or 1.0
    r2 = 1.0 - ss_res / ss_tot
    run_id = str(uuid.uuid4())
    model_id = f"O1-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    artifact = os.path.join(ARTIFACT_DIR, f"{model_id}.json")
    payload = {"alpha": float(params[0]), "beta": float(params[1]), "margin": float(params[2]), "mae": mae, "rmse": rmse, "r2": r2}
    with open(artifact, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    db = SessionLocal()
    try:
        status = "REGISTERED"
        activate = mae <= 12.0
        db.add(O1ModelDB(
            id=model_id,
            version=model_id,
            status="ACTIVE" if activate else status,
            artifact_path=artifact,
            parameters={"alpha_min_per_deg": float(params[0]), "beta_min_per_deg": float(params[1]), "base_safety_margin_minutes": float(params[2])},
            mae_minutes=round(mae, 3),
            rmse_minutes=round(rmse, 3),
            r2_score=round(r2, 4),
            sample_count=len(ytr) + len(yte),
            dataset_version=dataset_version,
            activated_at=datetime.utcnow() if activate else None,
        ))
        db.add(O1ModelTrainingRunDB(
            id=run_id,
            model_id=model_id,
            dataset_version=dataset_version,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            status="COMPLETED",
            feature_count=3,
            sample_count=len(ytr) + len(yte),
            mae_minutes=round(mae, 3),
            rmse_minutes=round(rmse, 3),
            r2_score=round(r2, 4),
            test_score=round(r2, 4),
        ))
        db.commit()
    finally:
        db.close()
    return {"status": "ACTIVE" if activate else "REGISTERED", "model_version": model_id, "mae_minutes": round(mae, 3), "rmse_minutes": round(rmse, 3), "r2_score": round(r2, 4), "sample_count": len(ytr) + len(yte)}
