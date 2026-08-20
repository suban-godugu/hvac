"""Shared HVAC ML HTTP API. Training datasets are never LIVE_BMS."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.ml.prediction.service import list_models, model_status, predict
from backend.ml.registry.service import list_datasets, list_maps, opportunity_health, register_datasets
from backend.ml.training.pipeline import train_all

router = APIRouter(prefix="/api/ml", tags=["ml"])


class PredictBody(BaseModel):
    opportunity_id: str
    agent_id: Optional[str] = None
    building_id: Optional[str] = None
    features: Dict[str, Any] = Field(default_factory=dict)


@router.get("/datasets")
def get_datasets():
    return {"datasets": list_datasets(), "source": "TRAINING_DATASET"}


@router.post("/datasets/register")
def post_register():
    return {"datasets": register_datasets(), "source": "TRAINING_DATASET"}


@router.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: str):
    for row in list_datasets():
        if row["id"] == dataset_id:
            return row
    return {"status": "NOT_FOUND", "id": dataset_id}


@router.post("/datasets/{dataset_id}/validate")
def post_validate(dataset_id: str):
    rows = {r["id"]: r for r in list_datasets()}
    row = rows.get(dataset_id)
    if not row:
        return {"status": "NOT_FOUND", "id": dataset_id}
    return {"status": row["status"], "source": "TRAINING_DATASET", "dataset": row}


@router.get("/maps")
def get_maps(opportunity_id: Optional[str] = None):
    return {"maps": list_maps(opportunity_id)}


@router.get("/health")
def get_health():
    return opportunity_health()


@router.get("/models")
def get_models():
    return {"models": list_models(), "source": "TRAINING_DATASET"}


@router.get("/models/{opportunity_id}")
def get_model(opportunity_id: str):
    return model_status(opportunity_id)


@router.post("/train")
def post_train():
    from backend.ml.features.maps import trainable_maps

    return {"runs": train_all(), "trainable_maps": len(trainable_maps())}


@router.post("/predict")
def post_predict(body: PredictBody):
    return predict(body.opportunity_id, features=body.features, agent_id=body.agent_id, building_id=body.building_id)


@router.post("/batch-predict")
def post_batch(body: Dict[str, Any]):
    items = body.get("items") or []
    return {"results": [predict(it.get("opportunity_id"), features=it.get("features") or {}, persist=False) for it in items]}


@router.get("/predictions/{opportunity_id}")
def get_predictions(opportunity_id: str):
    from database.models_ml import MLPredictionDB
    from database.session import SessionLocal

    db = SessionLocal()
    try:
        rows = (
            db.query(MLPredictionDB)
            .filter_by(opportunity_id=opportunity_id.upper())
            .order_by(MLPredictionDB.created_at.desc())
            .limit(50)
            .all()
        )
        return {
            "predictions": [
                {
                    "id": r.id,
                    "status": r.status,
                    "provenance": r.provenance,
                    "source": r.source,
                    "prediction": r.prediction_json,
                    "confidence": r.confidence,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
        }
    finally:
        db.close()
