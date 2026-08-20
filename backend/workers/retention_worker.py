"""Retention/archive placeholder — do not delete historical telemetry silently."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from database.session import SessionLocal
from database.models_platform import CanonicalTelemetryDB


def archive_old_telemetry(retain_days: Optional[int] = None) -> int:
    days = retain_days if retain_days is not None else int(os.getenv("HVAC_TELEMETRY_RETAIN_DAYS", "90"))
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    db = SessionLocal()
    try:
        # Archive policy: count only. Physical delete requires HVAC_TELEMETRY_PURGE=1.
        q = db.query(CanonicalTelemetryDB).filter(CanonicalTelemetryDB.timestamp < cutoff)
        n = q.count()
        if os.getenv("HVAC_TELEMETRY_PURGE", "0") in ("1", "true", "TRUE") and n:
            q.delete(synchronize_session=False)
            db.commit()
        return n
    except Exception:
        db.rollback()
        return 0
    finally:
        db.close()
