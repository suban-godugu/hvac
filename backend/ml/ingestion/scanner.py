"""Scan local archives: schema/quality samples. Never labels files LIVE_BMS."""
from __future__ import annotations

import csv
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from backend.ml.paths import ARCHIVE_SPECS, DATA_EXTS, DOWNLOADS


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


def list_data_files(root: Path) -> List[Path]:
    if not root.exists() or not root.is_dir():
        return []
    out: List[Path] = []
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            p = Path(dirpath) / name
            if p.suffix.lower() in DATA_EXTS:
                out.append(p)
    return sorted(out)


def _count_csv_rows(path: Path, max_count: int = 50_000) -> int:
    n = 0
    try:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
            next(f, None)
            for n, _ in enumerate(f, start=1):
                if n >= max_count:
                    return n
    except OSError:
        return 0
    return n


def inspect_csv(path: Path, sample_limit: int = 4000) -> Dict[str, Any]:
    cols: List[str] = []
    rows: List[Dict[str, str]] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        cols = list(reader.fieldnames or [])
        for i, row in enumerate(reader):
            if i >= sample_limit:
                break
            rows.append({k: (row.get(k) or "") for k in cols})
    row_count = _count_csv_rows(path)
    return _quality_from_rows(cols, rows, row_count, str(path.suffix).lower().lstrip("."))


def inspect_json(path: Path, sample_limit: int = 200) -> Dict[str, Any]:
    size = path.stat().st_size if path.exists() else 0
    cols: List[str] = []
    if size > 8_000_000:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            chunk = f.read(80_000)
        if '"columns"' in chunk:
            try:
                # archive (7) influx export: {"name","columns":[...], ...}
                start = chunk.find('"columns"')
                sub = chunk[start:]
                arr_start = sub.find("[")
                arr_end = sub.find("]")
                if arr_start >= 0 and arr_end > arr_start:
                    cols = json.loads(sub[arr_start : arr_end + 1])
            except json.JSONDecodeError:
                cols = []
        return {
            "format": "json",
            "columns": cols,
            "schema": {c: "unknown" for c in cols},
            "row_count": None,
            "missing_pct": None,
            "duplicate_rows": None,
            "timestamp_valid": None,
            "numeric_valid_pct": None,
            "outlier_rate": None,
            "sampling_interval_seconds": None,
            "sample_rows": 0,
            "notes": "SAMPLED_LARGE_FILE",
            "size_bytes": size,
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return {"format": "json", "columns": [], "schema": {}, "row_count": 0, "notes": "INVALID_JSON"}
    records: List[Dict[str, Any]] = []
    if isinstance(data, list):
        records = [r for r in data if isinstance(r, dict)][:sample_limit]
    elif isinstance(data, dict) and isinstance(data.get("data"), list):
        records = [r for r in data["data"] if isinstance(r, dict)][:sample_limit]
    cols = sorted({k for r in records for k in r.keys()})
    rows = [{c: str(r.get(c, "") if r.get(c) is not None else "") for c in cols} for r in records]
    return _quality_from_rows(cols, rows, len(data) if isinstance(data, list) else len(records), "json")


def _quality_from_rows(cols: List[str], rows: List[Dict[str, str]], row_count: Optional[int], fmt: str) -> Dict[str, Any]:
    n = max(len(rows), 1)
    missing = 0
    cells = 0
    numeric_ok = 0
    numeric_n = 0
    schema: Dict[str, str] = {}
    ranges: Dict[str, Dict[str, Any]] = {}
    time_col = next((c for c in cols if any(x in c.lower() for x in ("time", "date", "timestamp"))), None)
    ts_ok = 0
    ts_n = 0
    signatures = set()
    dup = 0
    for row in rows:
        sig = tuple(row.get(c, "") for c in cols)
        if sig in signatures:
            dup += 1
        signatures.add(sig)
        for c in cols:
            v = row.get(c, "")
            cells += 1
            if v.strip() == "" or v.strip().upper() in ("NA", "NULL", "NONE"):
                missing += 1
                continue
            num = _to_float(v)
            if num is not None:
                numeric_n += 1
                numeric_ok += 1
                bucket = ranges.setdefault(c, {"min": num, "max": num})
                bucket["min"] = min(bucket["min"], num)
                bucket["max"] = max(bucket["max"], num)
            else:
                if any(ch.isdigit() for ch in v):
                    numeric_n += 1
        if time_col:
            ts_n += 1
            raw = row.get(time_col, "")
            if raw.strip():
                ts_ok += 1
    for c in cols:
        if c in ranges:
            schema[c] = "numeric"
        else:
            schema[c] = "string"
    return {
        "format": fmt,
        "columns": cols,
        "schema": schema,
        "ranges": ranges,
        "row_count": row_count,
        "missing_pct": round(100.0 * missing / cells, 3) if cells else None,
        "duplicate_rows": dup,
        "timestamp_valid": (ts_ok / ts_n >= 0.8) if ts_n else None,
        "numeric_valid_pct": round(100.0 * numeric_ok / numeric_n, 3) if numeric_n else None,
        "outlier_rate": None,
        "sampling_interval_seconds": None,
        "sample_rows": len(rows),
        "size_bytes": None,
    }


def inspect_file(path: Path) -> Dict[str, Any]:
    ext = path.suffix.lower()
    info: Dict[str, Any]
    if ext == ".csv":
        info = inspect_csv(path)
    elif ext == ".json":
        info = inspect_json(path)
    elif ext in {".xlsx", ".xls", ".parquet"}:
        info = {
            "format": ext.lstrip("."),
            "columns": [],
            "schema": {},
            "row_count": None,
            "notes": "FORMAT_DETECTED_NO_PARSER",
            "sample_rows": 0,
        }
    elif ext == ".txt":
        info = {"format": "txt", "columns": [], "schema": {}, "row_count": None, "sample_rows": 0, "notes": "TEXT_METADATA"}
    else:
        info = {"format": ext.lstrip("."), "columns": [], "schema": {}, "row_count": None, "sample_rows": 0}
    try:
        info["size_bytes"] = path.stat().st_size
    except OSError:
        info["size_bytes"] = None
    info["file_name"] = path.name
    info["file_path"] = str(path)
    return info


def fingerprint_dataset(files: List[Path]) -> str:
    names = tuple(sorted(p.name.lower() for p in files))
    return "|".join(names)


def scan_archives(root: Optional[Path] = None) -> List[Dict[str, Any]]:
    base = Path(root) if root else DOWNLOADS
    results: List[Dict[str, Any]] = []
    fingerprints: Dict[str, str] = {}
    for spec in ARCHIVE_SPECS:
        folder = base / spec["folder"]
        ds_id = spec["id"]
        rec: Dict[str, Any] = {
            "id": ds_id,
            "name": spec["name"],
            "source": "TRAINING_DATASET",
            "path": str(folder),
            "status": "REGISTERED",
            "alias_of": None,
            "notes": None,
            "files": [],
        }
        if not folder.exists():
            rec["status"] = "MISSING_PATH"
            rec["notes"] = "Folder not found."
            results.append(rec)
            continue
        files = list_data_files(folder)
        if spec["id"] == "ds_archive_3" or not files:
            rec["status"] = "SKIPPED_EMPTY"
            rec["notes"] = "No CSV/XLSX/JSON/Parquet data files."
            results.append(rec)
            continue
        fp = fingerprint_dataset(files)
        if fp in fingerprints:
            rec["status"] = "DUPLICATE"
            rec["alias_of"] = fingerprints[fp]
            rec["notes"] = f"Duplicate of {fingerprints[fp]}; do not double-train."
            rec["files"] = [{"file_name": p.name, "file_path": str(p), "format": p.suffix.lower().lstrip(".")} for p in files[:30]]
            results.append(rec)
            continue
        fingerprints[fp] = ds_id
        inspected = []
        # Cap inspection to keep scans production-honest and bounded.
        for p in files[:40]:
            inspected.append(inspect_file(p))
        rec["files"] = inspected
        results.append(rec)
    return results
