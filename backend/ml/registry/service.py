"""Persist scanned archives and explicit opportunity maps. source is always TRAINING_DATASET."""
from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.ml.features.maps import OPPORTUNITY_MAPS
from backend.ml.ingestion.scanner import scan_archives
from database.models_ml import (
    MLDatasetFileDB,
    MLDatasetOpportunityMapDB,
    MLDatasetQualityDB,
    MLDatasetRegistryDB,
    MLFeatureDefinitionDB,
)
from database.session import SessionLocal


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def register_datasets(root: Optional[Path] = None, db=None) -> List[Dict[str, Any]]:
    own = db is None
    session = db or SessionLocal()
    scanned = scan_archives(root)
    out = []
    try:
        for rec in scanned:
            row = session.query(MLDatasetRegistryDB).filter_by(id=rec["id"]).first()
            if not row:
                row = MLDatasetRegistryDB(id=rec["id"])
                session.add(row)
            row.name = rec["name"]
            row.source = "TRAINING_DATASET"
            row.path = rec["path"]
            row.status = rec["status"]
            row.alias_of = rec.get("alias_of")
            row.notes = rec.get("notes")
            row.updated_at = datetime.utcnow()
            session.query(MLDatasetFileDB).filter_by(dataset_id=rec["id"]).delete()
            session.query(MLDatasetQualityDB).filter_by(dataset_id=rec["id"]).delete()
            for f in rec.get("files") or []:
                fid = _id("file")
                session.add(
                    MLDatasetFileDB(
                        id=fid,
                        dataset_id=rec["id"],
                        file_path=f.get("file_path") or "",
                        file_name=f.get("file_name") or "",
                        format=f.get("format"),
                        size_bytes=f.get("size_bytes"),
                        row_count=f.get("row_count"),
                        columns_json=f.get("columns"),
                        schema_json=f.get("schema"),
                    )
                )
                session.add(
                    MLDatasetQualityDB(
                        id=_id("q"),
                        dataset_id=rec["id"],
                        file_id=fid,
                        missing_pct=f.get("missing_pct"),
                        duplicate_rows=f.get("duplicate_rows"),
                        timestamp_valid=f.get("timestamp_valid"),
                        numeric_valid_pct=f.get("numeric_valid_pct"),
                        outlier_rate=f.get("outlier_rate"),
                        sampling_interval_seconds=f.get("sampling_interval_seconds"),
                        sample_rows=f.get("sample_rows"),
                        details_json={"notes": f.get("notes"), "ranges": f.get("ranges")},
                    )
                )
            out.append({"id": rec["id"], "status": rec["status"], "source": "TRAINING_DATASET", "alias_of": rec.get("alias_of")})
        session.commit()
        persist_maps(session)
        persist_feature_defs(session)
        session.commit()
    finally:
        if own:
            session.close()
    return out


def persist_maps(session) -> None:
    session.query(MLDatasetOpportunityMapDB).delete()
    for m in OPPORTUNITY_MAPS:
        if m.get("training_allowed") and not m.get("target_column"):
            continue
        session.add(
            MLDatasetOpportunityMapDB(
                id=_id("map"),
                dataset_id=m["dataset_id"],
                opportunity_id=m["opportunity_id"],
                agent_id=m["agent_id"],
                file_name=m.get("file_name"),
                feature_map=m["feature_map"],
                target_column=m.get("target_column"),
                task_type=m["task_type"],
                training_allowed=bool(m["training_allowed"]),
                status=m["status"],
                notes=m.get("notes"),
            )
        )


def persist_feature_defs(session) -> None:
    session.query(MLFeatureDefinitionDB).delete()
    for m in OPPORTUNITY_MAPS:
        for feat, src in (m.get("feature_map") or {}).items():
            session.add(
                MLFeatureDefinitionDB(
                    id=_id("feat"),
                    opportunity_id=m["opportunity_id"],
                    feature_name=feat,
                    source_column=src,
                    required=True,
                )
            )


def list_datasets(db=None) -> List[Dict[str, Any]]:
    own = db is None
    session = db or SessionLocal()
    try:
        rows = session.query(MLDatasetRegistryDB).all()
        return [
            {
                "id": r.id,
                "name": r.name,
                "source": r.source,
                "path": r.path,
                "status": r.status,
                "alias_of": r.alias_of,
                "notes": r.notes,
                "quality": _dataset_quality(session, r.id),
            }
            for r in rows
        ]
    finally:
        if own:
            session.close()


def _dataset_quality(session, dataset_id: str) -> Dict[str, Any]:
    rows = session.query(MLDatasetQualityDB).filter_by(dataset_id=dataset_id).all()
    if not rows:
        return {"files": 0, "missing_pct": None, "sample_rows": 0}
    miss = [r.missing_pct for r in rows if r.missing_pct is not None]
    return {
        "files": len(rows),
        "missing_pct": round(sum(miss) / len(miss), 3) if miss else None,
        "sample_rows": sum(r.sample_rows or 0 for r in rows),
        "duplicate_rows": sum(r.duplicate_rows or 0 for r in rows),
    }


def opportunity_health(db=None) -> Dict[str, Any]:
    """O1–O20 matrix from registry + maps + models. Provenance is never LIVE_BMS."""
    from backend.ml.features.maps import AGENT_FOR, missing_dataset_for
    from backend.ml.prediction.service import list_models
    from database.models_ml import MLModelMetricsDB, MLPredictionDB, MLTrainingRunDB

    own = db is None
    session = db or SessionLocal()
    try:
        datasets = {r.id: r for r in session.query(MLDatasetRegistryDB).all()}
        models = {m["opportunity_id"]: m for m in list_models(session) if m.get("opportunity_id")}
        # list_models opens its own session if db passed - I passed session, list_models treats as db
        maps = session.query(MLDatasetOpportunityMapDB).all()
        maps_by_oid: Dict[str, list] = {}
        for m in maps:
            maps_by_oid.setdefault(m.opportunity_id, []).append(m)
        runs = session.query(MLTrainingRunDB).all()
        latest_run = {}
        for r in sorted(runs, key=lambda x: x.created_at or datetime.min, reverse=True):
            latest_run.setdefault(r.opportunity_id, r)
        preds = session.query(MLPredictionDB).all()
        latest_pred = {}
        for p in sorted(preds, key=lambda x: x.created_at or datetime.min, reverse=True):
            latest_pred.setdefault(p.opportunity_id, p)
        metrics_by_model = {}
        for met in session.query(MLModelMetricsDB).all():
            metrics_by_model.setdefault(met.model_id, {})[met.split] = met.metrics_json

        rows = []
        for i in range(1, 21):
            oid = f"O{i}"
            model = models.get(oid) or {}
            mmap = maps_by_oid.get(oid) or []
            primary = next((m for m in mmap if m.training_allowed), mmap[0] if mmap else None)
            ds = datasets.get(primary.dataset_id) if primary else None
            run = latest_run.get(oid)
            if oid == "O10":
                status = "MODEL_NOT_TRAINABLE"
            elif model.get("status") == "MODEL_READY":
                status = "MODEL_READY"
            elif run and run.status == "TRAINING_FAILED":
                status = "TRAINING_FAILED"
            elif ds and ds.status in ("SKIPPED_EMPTY", "MISSING_PATH"):
                status = "DATASET_INVALID"
            else:
                status = model.get("status") or "MODEL_NOT_TRAINABLE"
            pred = latest_pred.get(oid)
            mid = model.get("model_id")
            val = metrics_by_model.get(mid or "", {}).get("validation")
            test = metrics_by_model.get(mid or "", {}).get("test")
            pred_avail = "AVAILABLE" if status == "MODEL_READY" else "UNAVAILABLE"
            if status == "MODEL_READY" and not mid:
                pred_avail = "UNAVAILABLE"
            rows.append(
                {
                    "opportunity_id": oid,
                    "agent_id": (primary.agent_id if primary else AGENT_FOR.get(oid)) or model.get("agent_id"),
                    "dataset_id": primary.dataset_id if primary else None,
                    "dataset_name": ds.name if ds else None,
                    "dataset_status": ds.status if ds else None,
                    "dataset_quality": _dataset_quality(session, ds.id) if ds else None,
                    "feature_map": primary.feature_map if primary else {},
                    "target": primary.target_column if primary else None,
                    "task_type": primary.task_type if primary else None,
                    "training_allowed": bool(primary.training_allowed) if primary else False,
                    "notes": primary.notes if primary else ("O10 has no ML model." if oid == "O10" else "No legitimate mapping."),
                    "missing_dataset": missing_dataset_for(oid),
                    "model_id": mid,
                    "model_version": model.get("model_version"),
                    "status": status,
                    "validation_status": "PASSED" if status == "MODEL_READY" else ("FAILED" if run and run.status == "TRAINING_FAILED" else "N/A"),
                    "metrics": {"validation": val, "test": test} if val or test else None,
                    "last_trained": run.created_at.isoformat() if run and run.created_at else None,
                    "prediction_availability": pred_avail,
                    "provenance": "TRAINING DATA",
                    "last_prediction": {
                        "id": pred.id,
                        "provenance": pred.provenance,
                        "source": pred.source,
                        "status": pred.status,
                        "created_at": pred.created_at.isoformat() if pred.created_at else None,
                    }
                    if pred
                    else None,
                    "training_run": {
                        "id": run.id,
                        "status": run.status,
                        "reason": run.reason,
                        "algorithm": run.algorithm,
                        "metrics": run.metrics_json,
                    }
                    if run
                    else None,
                }
            )
        return {
            "opportunities": rows,
            "source": "TRAINING_DATASET",
            "datasets": list_datasets(session),
        }
    finally:
        if own:
            session.close()


def list_maps(opportunity_id: Optional[str] = None, db=None) -> List[Dict[str, Any]]:
    own = db is None
    session = db or SessionLocal()
    try:
        q = session.query(MLDatasetOpportunityMapDB)
        if opportunity_id:
            q = q.filter_by(opportunity_id=opportunity_id.upper())
        return [
            {
                "id": r.id,
                "dataset_id": r.dataset_id,
                "opportunity_id": r.opportunity_id,
                "agent_id": r.agent_id,
                "file_name": r.file_name,
                "feature_map": r.feature_map,
                "target_column": r.target_column,
                "task_type": r.task_type,
                "training_allowed": r.training_allowed,
                "status": r.status,
                "notes": r.notes,
            }
            for r in q.all()
        ]
    finally:
        if own:
            session.close()
