"""Background jobs: weather, M&V, retention. Not the control loop."""
from __future__ import annotations

import time

from backend.services.logging_service import log_event
from backend.workers.retention_worker import archive_old_telemetry


def run_once() -> None:
    log_event("INFO", "job-worker", "JOB_CYCLE")
    try:
        n = archive_old_telemetry()
        log_event("INFO", "job-worker", "RETENTION", extra={"candidates": n})
    except Exception as exc:
        log_event("ERROR", "job-worker", "RETENTION_FAIL", extra={"error": type(exc).__name__})


if __name__ == "__main__":
    while True:
        run_once()
        time.sleep(int(__import__("os").getenv("HVAC_JOB_INTERVAL_SECONDS", "300")))
