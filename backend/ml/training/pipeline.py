"""Train opportunity-specific models only when an explicit target exists."""
from __future__ import annotations

import csv
import pickle
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from datetime import datetime

from backend.ml.features.maps import AGENT_FOR, trainable_maps
from backend.ml.paths import ARTIFACT_DIR, DOWNLOADS, ARCHIVE_SPECS
from database.models_ml import MLModelMetricsDB, MLModelRegistryDB, MLTrainingRunDB
from database.session import SessionLocal

MIN_ROWS = 50
MIN_R2 = 0.15
MIN_ACC = 0.55
MAX_TRAIN_ROWS = 8000


def _to_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        n = float(str(v).strip())
    except (TypeError, ValueError):
        return None
    if n != n or n in (float("inf"), float("-inf")):
        return None
    return n


def _archive_folder(dataset_id: str) -> Optional[Path]:
    for spec in ARCHIVE_SPECS:
        if spec["id"] == dataset_id:
            return DOWNLOADS / spec["folder"]
    return None


def _find_file(folder: Path, file_name: str) -> Optional[Path]:
    if not folder or not folder.exists():
        return None
    direct = folder / file_name
    if direct.exists():
        return direct
    for p in folder.rglob(file_name):
        return p
    return None


def _parse_ts(raw: Any) -> Optional[datetime]:
    s = str(raw or "").strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1]
    if "." in s:
        s = s.split(".")[0]
    s = s.replace("T", " ")
    m = re.match(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})[ T](\d{1,2}):(\d{2})", s)
    if m:
        y, mo, d, h, mi = (int(x) for x in m.groups())
        try:
            return datetime(y, mo, d, h, mi)
        except ValueError:
            return None
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4}) (\d{1,2}):(\d{2})", s)
    if m:
        a, b, y, h, mi = (int(x) for x in m.groups())
        try:
            return datetime(y, a, b, h, mi)
        except ValueError:
            return None
    return None


def _ts_key(raw: Any, floor_min: int = 5) -> Optional[str]:
    dt = _parse_ts(raw)
    if not dt:
        return None
    minute = (dt.minute // floor_min) * floor_min
    dt = dt.replace(minute=minute, second=0, microsecond=0)
    return dt.strftime("%Y-%m-%d %H:%M")


def _index_column(path: Path, column: str, max_keys: int = 250_000) -> Dict[str, float]:
    out: Dict[str, float] = {}
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        ts_col = "date"
        if reader.fieldnames:
            if "date" in reader.fieldnames:
                ts_col = "date"
            elif "Datetime" in reader.fieldnames:
                ts_col = "Datetime"
            elif "Timestamp" in reader.fieldnames:
                ts_col = "Timestamp"
            else:
                ts_col = reader.fieldnames[0]
        for row in reader:
            key = _ts_key(row.get(ts_col))
            val = _to_float(row.get(column))
            if key is None or val is None:
                continue
            out[key] = val
            if len(out) >= max_keys:
                break
    return out


def _load_joined(folder: Path, file_names: List[str], feature_map: Dict[str, str], target: str, max_rows: int = MAX_TRAIN_ROWS) -> Tuple[List[List[float]], List[float], List[str]]:
    paths = []
    headers: Dict[str, Path] = {}
    for name in file_names:
        path = _find_file(folder, name)
        if not path:
            return [], [], list(feature_map.keys())
        paths.append(path)
        with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
            cols = next(csv.reader(f), [])
        for c in cols:
            headers[c] = path
    needed = list(feature_map.values()) + [target]
    series: Dict[str, Dict[str, float]] = {}
    for col in needed:
        src = headers.get(col)
        if not src:
            return [], [], list(feature_map.keys())
        series[col] = _index_column(src, col)
    keys = set(series[target].keys())
    for col in feature_map.values():
        keys &= set(series[col].keys())
    names = list(feature_map.keys())
    X: List[List[float]] = []
    y: List[float] = []
    for key in sorted(keys):
        X.append([series[feature_map[n]][key] for n in names])
        y.append(series[target][key])
        if len(y) >= max_rows:
            break
    return X, y, names


def _load_influx_json(path: Path, feature_map: Dict[str, str], target: str, max_rows: int = MAX_TRAIN_ROWS, max_scan: int = 20_000) -> Tuple[List[List[float]], List[float], List[str]]:
    import json as json_mod

    names = list(feature_map.keys())
    text_head = path.read_text(encoding="utf-8", errors="replace")[:250_000]
    start = text_head.find('"columns"')
    if start < 0:
        return [], [], names
    sub = text_head[start:]
    arr_start = sub.find("[")
    decoder = json_mod.JSONDecoder()
    cols, _ = decoder.raw_decode(sub[arr_start:])
    col_index = {c: i for i, c in enumerate(cols)}
    needed = [feature_map[n] for n in names] + [target]
    if any(c not in col_index for c in needed):
        return [], [], names
    marker = '"values"'
    with path.open("r", encoding="utf-8", errors="replace") as f:
        chunk = f.read(400_000)
        pos = chunk.find(marker)
        if pos < 0:
            return [], [], names
        rest = chunk[pos + len(marker) :]
        bracket = rest.find("[")
        buf = rest[bracket + 1 :]
        X: List[List[float]] = []
        y: List[float] = []
        scanned = 0
        leftover = buf
        while scanned < max_scan and len(y) < max_rows:
            leftover = leftover.lstrip(" \n\r\t,")
            if leftover.startswith("]"):
                break
            if not leftover.startswith("["):
                more = f.read(400_000)
                if not more:
                    break
                leftover += more
                continue
            try:
                arr, idx = decoder.raw_decode(leftover)
            except json_mod.JSONDecodeError:
                more = f.read(400_000)
                if not more:
                    break
                leftover += more
                continue
            leftover = leftover[idx:]
            scanned += 1
            if not isinstance(arr, list):
                continue
            feats = []
            skip = False
            for n in names:
                val = _to_float(arr[col_index[feature_map[n]]] if col_index[feature_map[n]] < len(arr) else None)
                if val is None:
                    skip = True
                    break
                feats.append(val)
            t = _to_float(arr[col_index[target]] if col_index[target] < len(arr) else None)
            if skip or t is None:
                continue
            X.append(feats)
            y.append(t)
        return X, y, names


def _load_xy(path: Path, feature_map: Dict[str, str], target: str, max_rows: int = MAX_TRAIN_ROWS) -> Tuple[List[List[float]], List[float], List[str]]:
    names = list(feature_map.keys())
    X: List[List[float]] = []
    y: List[float] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= max_rows:
                break
            feats = []
            skip = False
            for feat in names:
                col = feature_map[feat]
                val = _to_float(row.get(col))
                if val is None:
                    skip = True
                    break
                feats.append(val)
            t = _to_float(row.get(target))
            if t is None or skip:
                continue
            X.append(feats)
            y.append(t)
    return X, y, names


def _split(X, y, seed: int = 7):
    n = len(y)
    idx = list(range(n))
    # deterministic shuffle
    for i in range(n - 1, 0, -1):
        j = (i * 1103515245 + seed) % (i + 1)
        idx[i], idx[j] = idx[j], idx[i]
    n_test = max(1, int(n * 0.15))
    n_val = max(1, int(n * 0.15))
    test_i = idx[:n_test]
    val_i = idx[n_test : n_test + n_val]
    train_i = idx[n_test + n_val :]
    take = lambda ids: ([X[i] for i in ids], [y[i] for i in ids])
    return take(train_i), take(val_i), take(test_i)


def _r2(y_true, y_pred) -> Optional[float]:
    if not y_true:
        return None
    mean = sum(y_true) / len(y_true)
    ss_tot = sum((t - mean) ** 2 for t in y_true)
    ss_res = sum((t - p) ** 2 for t, p in zip(y_true, y_pred))
    if ss_tot <= 0:
        return None
    return 1.0 - ss_res / ss_tot


def _mae(y_true, y_pred) -> float:
    return sum(abs(t - p) for t, p in zip(y_true, y_pred)) / max(len(y_true), 1)


def _accuracy(y_true, y_pred) -> float:
    return sum(int(t == p) for t, p in zip(y_true, y_pred)) / max(len(y_true), 1)


def _fit(task: str, Xtr, ytr):
    try:
        import numpy as np
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    except ImportError:
        return None, "sklearn_unavailable"
    X = np.array(Xtr, dtype=float)
    y = np.array(ytr, dtype=float)
    if task == "classification":
        model = RandomForestClassifier(n_estimators=80, random_state=7, n_jobs=1)
        model.fit(X, y.astype(int))
    else:
        model = RandomForestRegressor(n_estimators=80, random_state=7, n_jobs=1)
        model.fit(X, y)
    return model, "RandomForest"


def _predict_model(model, X):
    import numpy as np

    pred = model.predict(np.array(X, dtype=float))
    return [float(p) for p in pred]


def train_map(mapping: Dict[str, Any], db=None) -> Dict[str, Any]:
    own = db is None
    session = db or SessionLocal()
    oid = mapping["opportunity_id"]
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    try:
        if oid == "O10":
            reason = "O10 has no ML model by product rule."
            session.add(MLTrainingRunDB(id=run_id, opportunity_id=oid, status="MODEL_NOT_TRAINABLE", reason=reason))
            session.commit()
            return {"status": "MODEL_NOT_TRAINABLE", "opportunity_id": oid, "reason": reason}
        if mapping.get("dataset_id") == "ds_archive_5":
            reason = "Duplicate Building 59 archive; do not double-train."
            session.add(MLTrainingRunDB(id=run_id, opportunity_id=oid, dataset_id=mapping["dataset_id"], status="SKIPPED_DUPLICATE", reason=reason))
            session.commit()
            return {"status": "SKIPPED_DUPLICATE", "opportunity_id": oid, "reason": reason}
        if not mapping.get("training_allowed") or not mapping.get("target_column"):
            reason = mapping.get("notes") or "No legitimate target column."
            session.add(MLTrainingRunDB(id=run_id, opportunity_id=oid, dataset_id=mapping.get("dataset_id"), status="MODEL_NOT_TRAINABLE", reason=reason))
            session.commit()
            return {"status": "MODEL_NOT_TRAINABLE", "opportunity_id": oid, "reason": reason}

        folder = _archive_folder(mapping["dataset_id"])
        join_files = mapping.get("join_files")
        loader = mapping.get("loader") or "csv"
        X: List[List[float]] = []
        y: List[float] = []
        names: List[str] = list(mapping["feature_map"].keys())
        if join_files:
            if not folder:
                reason = f"Archive folder missing for {mapping['dataset_id']}"
                session.add(MLTrainingRunDB(id=run_id, opportunity_id=oid, dataset_id=mapping["dataset_id"], status="MODEL_NOT_TRAINABLE", reason=reason))
                session.commit()
                return {"status": "MODEL_NOT_TRAINABLE", "opportunity_id": oid, "reason": reason}
            X, y, names = _load_joined(folder, join_files, mapping["feature_map"], mapping["target_column"])
        else:
            path = _find_file(folder, mapping["file_name"]) if folder and mapping.get("file_name") else None
            if not path:
                reason = f"Training file not found: {mapping.get('file_name')}"
                session.add(MLTrainingRunDB(id=run_id, opportunity_id=oid, dataset_id=mapping["dataset_id"], status="MODEL_NOT_TRAINABLE", reason=reason))
                session.commit()
                return {"status": "MODEL_NOT_TRAINABLE", "opportunity_id": oid, "reason": reason}
            if loader == "influx_json":
                X, y, names = _load_influx_json(path, mapping["feature_map"], mapping["target_column"])
            else:
                X, y, names = _load_xy(path, mapping["feature_map"], mapping["target_column"])
        if len(y) < MIN_ROWS:
            reason = f"Insufficient complete rows ({len(y)} < {MIN_ROWS}) after dropping missing values."
            session.add(MLTrainingRunDB(id=run_id, opportunity_id=oid, dataset_id=mapping["dataset_id"], status="MODEL_NOT_TRAINABLE", reason=reason))
            session.commit()
            return {"status": "MODEL_NOT_TRAINABLE", "opportunity_id": oid, "reason": reason, "rows": len(y)}

        (Xtr, ytr), (Xva, yva), (Xte, yte) = _split(X, y)
        if len(ytr) < 20 or len(yva) < 5:
            reason = "Train/validation split too small."
            session.add(MLTrainingRunDB(id=run_id, opportunity_id=oid, dataset_id=mapping["dataset_id"], status="MODEL_NOT_TRAINABLE", reason=reason))
            session.commit()
            return {"status": "MODEL_NOT_TRAINABLE", "opportunity_id": oid, "reason": reason}

        model, algo = _fit(mapping["task_type"], Xtr, ytr)
        if model is None:
            reason = "scikit-learn is not installed; cannot train."
            session.add(MLTrainingRunDB(id=run_id, opportunity_id=oid, dataset_id=mapping["dataset_id"], status="MODEL_NOT_TRAINABLE", reason=reason))
            session.commit()
            return {"status": "MODEL_NOT_TRAINABLE", "opportunity_id": oid, "reason": reason}

        pva = _predict_model(model, Xva)
        pte = _predict_model(model, Xte)
        if mapping["task_type"] == "classification":
            pva_c = [int(round(v)) for v in pva]
            pte_c = [int(round(v)) for v in pte]
            yva_c = [int(v) for v in yva]
            yte_c = [int(v) for v in yte]
            val_m = {"accuracy": round(_accuracy(yva_c, pva_c), 4)}
            test_m = {"accuracy": round(_accuracy(yte_c, pte_c), 4)}
            ok = val_m["accuracy"] >= MIN_ACC
        else:
            val_m = {"r2": _r2(yva, pva), "mae": round(_mae(yva, pva), 4)}
            test_m = {"r2": _r2(yte, pte), "mae": round(_mae(yte, pte), 4)}
            ok = val_m["r2"] is not None and val_m["r2"] >= MIN_R2
        if not ok:
            reason = f"Validation insufficient: {val_m}"
            session.add(
                MLTrainingRunDB(
                    id=run_id,
                    opportunity_id=oid,
                    dataset_id=mapping["dataset_id"],
                    status="TRAINING_FAILED",
                    algorithm=algo,
                    metrics_json={"validation": val_m, "test": test_m},
                    reason=reason,
                )
            )
            session.commit()
            return {"status": "TRAINING_FAILED", "opportunity_id": oid, "reason": reason, "metrics": val_m}

        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        version = f"{oid}-v1"
        model_id = f"mdl-{oid.lower()}-v1"
        artifact = ARTIFACT_DIR / f"{model_id}.pkl"
        payload = {
            "model": model,
            "features": names,
            "target": mapping["target_column"],
            "task_type": mapping["task_type"],
            "feature_map": mapping["feature_map"],
        }
        with artifact.open("wb") as fh:
            pickle.dump(payload, fh)

        existing = session.query(MLModelRegistryDB).filter_by(id=model_id).first()
        if existing:
            session.delete(existing)
            session.query(MLModelMetricsDB).filter_by(model_id=model_id).delete()
        session.add(
            MLModelRegistryDB(
                id=model_id,
                opportunity_id=oid,
                agent_id=AGENT_FOR[oid],
                model_type=algo,
                model_version=version,
                features_json=names,
                target_json={"column": mapping["target_column"], "task": mapping["task_type"]},
                artifact_path=str(artifact),
                training_dataset_id=mapping["dataset_id"],
                status="MODEL_READY",
            )
        )
        session.add(MLModelMetricsDB(id=f"{model_id}-val", model_id=model_id, split="validation", metrics_json=val_m))
        session.add(MLModelMetricsDB(id=f"{model_id}-test", model_id=model_id, split="test", metrics_json=test_m))
        session.add(
            MLTrainingRunDB(
                id=run_id,
                opportunity_id=oid,
                dataset_id=mapping["dataset_id"],
                status="TRAINED",
                algorithm=algo,
                metrics_json={"validation": val_m, "test": test_m, "n_train": len(ytr), "n_val": len(yva), "n_test": len(yte)},
            )
        )
        session.commit()
        return {
            "status": "MODEL_READY",
            "opportunity_id": oid,
            "model_id": model_id,
            "model_version": version,
            "metrics": {"validation": val_m, "test": test_m},
            "algorithm": algo,
            "n_rows": len(y),
        }
    finally:
        if own:
            session.close()


def train_all(db=None) -> List[Dict[str, Any]]:
    results = []
    for mapping in trainable_maps():
        if mapping.get("dataset_id") == "ds_archive_5":
            results.append({"status": "SKIPPED_DUPLICATE", "opportunity_id": mapping["opportunity_id"], "reason": "Duplicate Building 59."})
            continue
        results.append(train_map(mapping, db=db))
    # persist not-trainable records for remaining official O's
    own = db is None
    session = db or SessionLocal()
    try:
        from backend.ml.features.maps import OPPORTUNITY_MAPS

        seen = {r.get("opportunity_id") for r in results}
        for m in OPPORTUNITY_MAPS:
            if m["opportunity_id"] in seen or m["training_allowed"]:
                continue
            if m["opportunity_id"] in seen:
                continue
            rid = f"run_{uuid.uuid4().hex[:10]}"
            session.add(
                MLTrainingRunDB(
                    id=rid,
                    opportunity_id=m["opportunity_id"],
                    dataset_id=m["dataset_id"],
                    status="MODEL_NOT_TRAINABLE",
                    reason=m.get("notes"),
                )
            )
            seen.add(m["opportunity_id"])
        session.commit()
    finally:
        if own:
            session.close()
    return results
