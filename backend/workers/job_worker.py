"""Background jobs: weather, M&V, retention, RLS, LSTM retrain, Safe RL offline."""
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
    try:
        from backend.ai.rls.runner import tick_debounced
        from backend.workers.watchdog import beat

        rls = tick_debounced()
        beat(note="tick", service="rls")
        if rls:
            log_event("INFO", "job-worker", "RLS_TICK", extra={"updated": rls.get("updated"), "wrote_setpoints": False})
    except Exception as exc:
        log_event("ERROR", "job-worker", "RLS_TICK_FAIL", extra={"error": type(exc).__name__})
    try:
        from backend.ai.safe_rl.runner import tick_debounced as safe_rl_tick

        srl = safe_rl_tick()
        if srl:
            log_event(
                "INFO",
                "job-worker",
                "SAFE_RL_TICK",
                extra={"status": srl.get("status"), "code": srl.get("code"), "wrote_setpoints": False},
            )
    except Exception as exc:
        log_event("ERROR", "job-worker", "SAFE_RL_TICK_FAIL", extra={"error": type(exc).__name__})
    try:
        from backend.ai.lstm.train import maybe_retrain_lstm

        lstm = maybe_retrain_lstm()
        if lstm and not lstm.get("skipped"):
            log_event("INFO", "job-worker", "LSTM_RETRAIN", extra={"wrote_setpoints": False})
    except Exception as exc:
        log_event("ERROR", "job-worker", "LSTM_RETRAIN_FAIL", extra={"error": type(exc).__name__})
    try:
        from backend.ai.safe_rl.offline import maybe_offline_update

        off = maybe_offline_update()
        if off and off.get("updated"):
            log_event("INFO", "job-worker", "SAFE_RL_OFFLINE", extra={"n": off.get("n"), "wrote_setpoints": False})
    except Exception as exc:
        log_event("ERROR", "job-worker", "SAFE_RL_OFFLINE_FAIL", extra={"error": type(exc).__name__})


if __name__ == "__main__":
    while True:
        run_once()
        time.sleep(int(__import__("os").getenv("HVAC_JOB_INTERVAL_SECONDS", "300")))
