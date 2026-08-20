"""Default local Kaggle/archive roots. Never treated as LIVE_BMS."""
from __future__ import annotations

import os
from pathlib import Path

DOWNLOADS = Path(os.environ.get("HVAC_ML_DATA_ROOT", r"C:\Users\subha\Downloads"))

ARCHIVE_SPECS = (
    {"id": "ds_archive", "name": "Building 59 (LBNL)", "folder": "archive"},
    {"id": "ds_archive_1", "name": "BDG2 building meters", "folder": "archive (1)"},
    {"id": "ds_archive_2", "name": "ASHRAE GEP III meters", "folder": "archive (2)"},
    {"id": "ds_archive_3", "name": "archive (3) empty", "folder": "archive (3)"},
    {"id": "ds_archive_4", "name": "HVAC Energy Data chiller plant", "folder": "archive (4)"},
    {"id": "ds_archive_5", "name": "Building 59 duplicate", "folder": "archive (5)"},
    {"id": "ds_archive_6", "name": "LBNL AHU/VAV FDD", "folder": "archive (6)"},
    {"id": "ds_archive_7", "name": "IAQ MQTT JSON", "folder": "archive (7)"},
    {"id": "ds_archive_8", "name": "Room occupancy CO2", "folder": "archive (8)"},
)

DATA_EXTS = {".csv", ".xlsx", ".xls", ".parquet", ".json", ".txt"}

ARTIFACT_DIR = Path(os.environ.get("HVAC_ML_ARTIFACT_DIR", os.path.join(os.path.dirname(__file__), "artifacts")))
