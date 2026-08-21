"""Smoke the deployed demo: Dataset labels, writes off, one path per O1–O20 section."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

PATHS = [
    "/healthz",
    "/api/platform/status",
    "/api/platform/telemetry",
    "/api/agents",
    "/api/ml/health",
    "/api/agents/O1/recommendation",
    "/api/agents/O5/recommendation",
    "/api/agents/O11/recommendation",
    "/api/agents/O15/recommendation",
    "/api/agents/O18/recommendation",
]


def get(url: str) -> tuple[int, dict | str]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            body = res.read().decode("utf-8", "replace")
            try:
                return res.status, json.loads(body)
            except json.JSONDecodeError:
                return res.status, body
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")[:500]


def main() -> int:
    origin = (sys.argv[1] if len(sys.argv) > 1 else os.getenv("HVAC_API_ORIGIN") or "").rstrip("/")
    if not origin:
        print("Usage: python scripts/smoke_demo.py https://<space>.hf.space")
        return 2
    failed = 0
    code, health = get(f"{origin}/healthz")
    print("healthz", code, health)
    if code != 200:
        return 1
    code, status = get(f"{origin}/api/platform/status")
    print("status", code)
    if code != 200 or not isinstance(status, dict):
        print(status)
        return 1
    tel = (status.get("telemetry") or {}).get("status")
    bms = (status.get("bms") or {}).get("status") or status.get("bmsStatus")
    print("plantMode", status.get("plantMode"), "bms", bms, "tel", tel, "control", status.get("controlEnabled"))
    if str(tel).upper() == "LIVE":
        print("FAIL: telemetry labeled LIVE")
        failed += 1
    if str(bms).upper() == "CONNECTED" and status.get("plantMode") == "DATASET":
        print("FAIL: Dataset plant reported BMS CONNECTED")
        failed += 1
    if status.get("controlEnabled") is True:
        print("FAIL: controlEnabled true")
        failed += 1
    if status.get("writeEnabled") is True:
        print("FAIL: writeEnabled true")
        failed += 1
    for path in PATHS:
        c, body = get(f"{origin}{path}")
        ok = c == 200
        print(f"{'OK' if ok else 'FAIL'} {c} {path}")
        if not ok:
            failed += 1
            print(str(body)[:240])
        elif path.endswith("/recommendation") and isinstance(body, dict):
            dispatch = body.get("dispatch") or {}
            if dispatch.get("allowed") is True:
                print("FAIL: dispatch allowed on", path)
                failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
