"""Offline LSTM training + versioned registry bump. Advisory only."""
from __future__ import annotations

import os
import pickle
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from backend.ai.lstm.model import LstmForecastNet, standardize_fit, torch_available, torch_gate_message, torch_required_strict
from backend.ai.lstm.sequences import HORIZONS_MIN, MODEL_IDS, TARGET_FIELD, build_dataset, clamp_lookback
from backend.ml.paths import ARTIFACT_DIR

_MAE_DEFAULTS = {
    "zone_temp": float(os.getenv("HVAC_LSTM_MAE_READY_TEMP", "1.5") or "1.5"),
    "hvac_power": float(os.getenv("HVAC_LSTM_MAE_READY_POWER", "25") or "25"),
    "energy": float(os.getenv("HVAC_LSTM_MAE_READY_POWER", "25") or "25"),
    "occupancy": float(os.getenv("HVAC_LSTM_MAE_READY_OCC", "0.25") or "0.25"),
}

_LAST_RETRAIN = 0.0


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _artifact_dir(model_key: str) -> Path:
    d = ARTIFACT_DIR / "lstm" / model_key
    d.mkdir(parents=True, exist_ok=True)
    return d


def train_one(
    target: str,
    zone_id: str = "ZONE-01",
    *,
    t0: Optional[str] = None,
    t1: Optional[str] = None,
    lookback_min: Optional[int] = None,
    epochs: Optional[int] = None,
) -> Dict[str, Any]:
    if not torch_available():
        out = torch_gate_message()
        out["target"] = target
        return out
    if torch_required_strict() and not torch_available():
        out = torch_gate_message()
        out["target"] = target
        return out
    if target not in TARGET_FIELD:
        return {"code": "UNKNOWN_TARGET", "target": target, "wrote_setpoints": False}

    lookback_min = clamp_lookback(lookback_min)
    end = t1 or _now().isoformat()
    start = t0
    if start is None:
        hours = int(os.getenv("HVAC_LSTM_TRAIN_HOURS", "48") or "48")
        start = (_now() - timedelta(hours=max(6, hours))).isoformat()

    ds = build_dataset(
        zone_id,
        t0=start,
        t1=end,
        lookback_min=lookback_min,
        horizons_min=HORIZONS_MIN,
        target=target,
    )
    if ds.get("code") != "OK":
        return {**ds, "status": "MODEL_NOT_READY", "wrote_setpoints": False}

    X, y = ds["X"], ds["y"]
    Xs, mean, std = standardize_fit(X)
    tcol = ds["target_col"]
    y_mean = float(ds["matrix"][:, tcol].mean())
    y_std = float(ds["matrix"][:, tcol].std()) or 1.0
    ys = (y - y_mean) / y_std

    epochs = int(epochs if epochs is not None else (os.getenv("HVAC_LSTM_EPOCHS", "40") or "40"))
    net = LstmForecastNet(n_features=Xs.shape[-1], horizon=ys.shape[-1], hidden=32)
    metrics = net.fit(Xs, ys, epochs=epochs)
    mae = float(metrics["val_mae"]) * y_std
    rmse = float(metrics["val_rmse"]) * y_std
    gate = _MAE_DEFAULTS.get(target, 1.5)
    ready = mae <= gate
    status = "MODEL_READY" if ready else "MODEL_NOT_READY"

    model_key = MODEL_IDS[target]
    version = f"v{int(_now().timestamp())}"
    model_id = f"{model_key}__{version}"
    artifact = _artifact_dir(model_key) / f"{version}.pkl"
    blob = {
        "state_dict": net.state_dict(),
        "mean": mean,
        "std": std,
        "y_mean": y_mean,
        "y_std": y_std,
        "n_features": int(Xs.shape[-1]),
        "horizon": int(ys.shape[-1]),
        "lookback": int(ds["L"]),
        "target": target,
        "target_field": TARGET_FIELD[target],
        "feature_cols": ds["feature_cols"],
        "horizons_min": list(HORIZONS_MIN),
        "zone_id": zone_id,
        "model_key": model_key,
        "model_version": version,
        "metrics": {"val_mae": mae, "val_rmse": rmse, "gate_mae": gate},
    }
    with artifact.open("wb") as fh:
        pickle.dump(blob, fh)

    promoted = _register_version(
        model_id=model_id,
        model_key=model_key,
        target=target,
        version=version,
        status=status,
        artifact_path=str(artifact),
        features={
            "model_key": model_key,
            "lookback": ds["L"],
            "horizon": ds["H"],
            "feature_cols": ds["feature_cols"],
            "horizons_min": list(HORIZONS_MIN),
        },
        metrics={"val_mae": mae, "val_rmse": rmse, "gate_mae": gate, "n_windows": ds["n_windows"]},
    )

    return {
        "code": "OK",
        "target": target,
        "model_id": model_id if promoted else model_key,
        "model_key": model_key,
        "model_version": version if promoted else None,
        "status": status if promoted else "MODEL_READY",
        "promoted": promoted,
        "val_mae": mae,
        "val_rmse": rmse,
        "gate_mae": gate,
        "n_windows": ds["n_windows"],
        "artifact_path": str(artifact) if promoted else None,
        "wrote_setpoints": False,
    }


def train_targets(
    zone_id: str = "ZONE-01",
    *,
    targets: Optional[Sequence[str]] = None,
    t0: Optional[str] = None,
    t1: Optional[str] = None,
    lookback_min: Optional[int] = None,
) -> Dict[str, Any]:
    keys = list(targets) if targets else list(TARGET_FIELD.keys())
    results = [train_one(t, zone_id, t0=t0, t1=t1, lookback_min=lookback_min) for t in keys]
    try:
        from backend.workers.watchdog import beat

        beat(note="retrain", service="lstm")
    except Exception:
        pass
    return {
        "zone_id": zone_id,
        "results": results,
        "wrote_setpoints": False,
        "torch": torch_available(),
    }


def maybe_retrain_lstm(zone_id: str = "ZONE-01") -> Optional[Dict[str, Any]]:
    """Periodic historian retrain for job_worker (daily by default)."""
    global _LAST_RETRAIN
    try:
        interval = float(os.getenv("HVAC_LSTM_RETRAIN_SECONDS", "86400") or "86400")
    except (TypeError, ValueError):
        interval = 86400.0
    now = time.monotonic()
    if interval > 0 and (now - _LAST_RETRAIN) < interval and _LAST_RETRAIN > 0:
        return None
    if not torch_available():
        return {"skipped": True, "code": "TORCH_REQUIRED", "wrote_setpoints": False}
    try:
        hours = int(os.getenv("HVAC_LSTM_RETRAIN_HOURS", "168") or "168")
    except (TypeError, ValueError):
        hours = 168
    end = _now()
    start = end - timedelta(hours=max(24, hours))
    _LAST_RETRAIN = now
    from backend.services.logging_service import log_event

    log_event("INFO", "job-worker", "LSTM_RETRAIN_START", extra={"hours": hours, "zone_id": zone_id})
    out = train_targets(zone_id, t0=start.isoformat(), t1=end.isoformat())
    log_event(
        "INFO",
        "job-worker",
        "LSTM_RETRAIN_DONE",
        extra={"results": [{k: r.get(k) for k in ("target", "status", "promoted", "code")} for r in out.get("results") or []]},
    )
    return out


def _register_version(
    *,
    model_id: str,
    model_key: str,
    target: str,
    version: str,
    status: str,
    artifact_path: str,
    features: Dict[str, Any],
    metrics: Dict[str, Any],
) -> bool:
    """Insert new version row. Promote only if MODEL_READY; else keep prior ACTIVE."""
    from database.session import SessionLocal
    from database.models_ml import MLModelMetricsDB, MLModelRegistryDB, MLTrainingRunDB

    now = _now()
    db = SessionLocal()
    try:
        if status != "MODEL_READY":
            db.add(
                MLTrainingRunDB(
                    id=f"run_lstm_{uuid.uuid4().hex[:10]}",
                    opportunity_id="LSTM",
                    dataset_id=None,
                    map_id=None,
                    status="TRAINING_FAILED",
                    algorithm="LSTM",
                    metrics_json=metrics,
                    reason=f"MAE gate not met for {target}; kept prior READY",
                    created_at=now,
                )
            )
            # Optional failed row for audit trail
            db.add(
                MLModelRegistryDB(
                    id=model_id,
                    opportunity_id="LSTM",
                    agent_id="forecast",
                    model_type="LSTM",
                    model_version=version,
                    features_json={**features, "model_key": model_key},
                    target_json={"target": target, "field": TARGET_FIELD[target], "model_key": model_key},
                    artifact_path=artifact_path,
                    training_dataset_id=None,
                    status="MODEL_NOT_READY",
                    created_at=now,
                )
            )
            db.commit()
            return False

        # Supersede prior READY for this model_key / legacy id
        priors = (
            db.query(MLModelRegistryDB)
            .filter(
                MLModelRegistryDB.opportunity_id == "LSTM",
                MLModelRegistryDB.model_type == "LSTM",
                MLModelRegistryDB.status == "MODEL_READY",
            )
            .all()
        )
        for row in priors:
            tj = row.target_json if isinstance(row.target_json, dict) else {}
            fj = row.features_json if isinstance(row.features_json, dict) else {}
            same = (
                row.id == model_key
                or row.id.startswith(model_key + "__")
                or tj.get("target") == target
                or fj.get("model_key") == model_key
                or tj.get("model_key") == model_key
            )
            if same:
                row.status = "SUPERSEDED"

        db.add(
            MLModelRegistryDB(
                id=model_id,
                opportunity_id="LSTM",
                agent_id="forecast",
                model_type="LSTM",
                model_version=version,
                features_json={**features, "model_key": model_key},
                target_json={"target": target, "field": TARGET_FIELD[target], "model_key": model_key},
                artifact_path=artifact_path,
                training_dataset_id=None,
                status="MODEL_READY",
                created_at=now,
            )
        )
        db.add(
            MLModelMetricsDB(
                id=f"{model_id}-val",
                model_id=model_id,
                split="validation",
                metrics_json=metrics,
            )
        )
        db.add(
            MLTrainingRunDB(
                id=f"run_lstm_{uuid.uuid4().hex[:10]}",
                opportunity_id="LSTM",
                dataset_id=None,
                map_id=None,
                status="COMPLETED",
                algorithm="LSTM",
                metrics_json=metrics,
                reason=None,
                created_at=now,
            )
        )
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
