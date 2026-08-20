"""Standalone control-loop process (not inside the API)."""
from __future__ import annotations

import time

from database.session import init_db
from backend.agents.scheduling_supervisory.worker import control_worker
from backend.services.logging_service import log_event


def main() -> None:
    init_db()
    control_worker.start()
    log_event("INFO", "control-worker", "STARTED")
    try:
        while True:
            time.sleep(30)
    except KeyboardInterrupt:
        control_worker.stop()


if __name__ == "__main__":
    main()
