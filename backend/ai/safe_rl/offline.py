"""Stage H3 — offline scorer weight / action-prior update from logged rewards."""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

from backend.services.logging_service import log_event

SETTINGS_KEY = "SAFE_RL_OFFLINE_WEIGHTS"
_LAST_OFFLINE = 0.0


def _default_blob() -> Dict[str, Any]:
    return {
        "weights": {
            "energy": float(os.getenv("HVAC_SAFE_RL_SCORE_W_ENERGY", "1.0") or "1.0"),
            "comfort": float(os.getenv("HVAC_SAFE_RL_SCORE_W_COMFORT", "2.0") or "2.0"),
            "limit": float(os.getenv("HVAC_SAFE_RL_SCORE_W_LIMIT", "0.5") or "0.5"),
            "forecast": float(os.getenv("HVAC_SAFE_RL_SCORE_W_FORECAST", "0.3") or "0.3"),
        },
        "action_priors": {},
        "n_updates": 0,
        "updated_at": None,
    }


def load_offline_blob() -> Dict[str, Any]:
    from database.session import SessionLocal
    from database.models_platform import PlatformSettingDB

    db = SessionLocal()
    try:
        row = db.query(PlatformSettingDB).filter_by(key=SETTINGS_KEY).first()
        if not row or not row.value:
            return _default_blob()
        data = json.loads(row.value)
        base = _default_blob()
        if isinstance(data.get("weights"), dict):
            base["weights"].update({k: float(v) for k, v in data["weights"].items()})
        if isinstance(data.get("action_priors"), dict):
            base["action_priors"] = {k: float(v) for k, v in data["action_priors"].items()}
        base["n_updates"] = int(data.get("n_updates") or 0)
        base["updated_at"] = data.get("updated_at")
        return base
    except Exception:
        return _default_blob()
    finally:
        db.close()


def save_offline_blob(blob: Dict[str, Any]) -> None:
    from datetime import datetime, timezone

    from database.session import SessionLocal
    from database.models_platform import PlatformSettingDB

    blob = dict(blob)
    blob["updated_at"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    db = SessionLocal()
    try:
        row = db.query(PlatformSettingDB).filter_by(key=SETTINGS_KEY).first()
        raw = json.dumps(blob)
        if row:
            row.value = raw
            row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            db.add(
                PlatformSettingDB(
                    key=SETTINGS_KEY,
                    value=raw,
                    updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def update_weights_from_log(limit: int = 50) -> Dict[str, Any]:
    """Clipped EMA update of weights + action priors from realized rewards."""
    from database.session import SessionLocal
    from database.models_platform import SafeRlDecisionDB

    alpha = float(os.getenv("HVAC_SAFE_RL_OFFLINE_ALPHA", "0.1") or "0.1")
    alpha = max(0.01, min(0.5, alpha))
    clip = float(os.getenv("HVAC_SAFE_RL_OFFLINE_CLIP", "0.5") or "0.5")

    db = SessionLocal()
    try:
        rows = (
            db.query(SafeRlDecisionDB)
            .filter(SafeRlDecisionDB.realized_reward.isnot(None))
            .order_by(SafeRlDecisionDB.measured_at.desc())
            .limit(max(1, min(200, int(limit))))
            .all()
        )
    finally:
        db.close()

    if not rows:
        return {"updated": False, "n": 0, "wrote_setpoints": False}

    blob = load_offline_blob()
    weights = dict(blob["weights"])
    priors = dict(blob.get("action_priors") or {})

    # Aggregate mean reward components
    n = len(rows)
    mean_e = sum(float(r.reward_energy or 0) for r in rows) / n
    mean_c = sum(float(r.reward_comfort or 0) for r in rows) / n
    mean_r = sum(float(r.realized_reward or 0) for r in rows) / n

    # Nudge energy/comfort weights toward recent reward signal (clipped)
    def _nudge(cur: float, signal: float) -> float:
        delta = alpha * max(-clip, min(clip, signal))
        return max(0.05, min(5.0, cur + delta))

    weights["energy"] = _nudge(float(weights.get("energy") or 1.0), mean_e)
    weights["comfort"] = _nudge(float(weights.get("comfort") or 2.0), mean_c)

    for r in rows:
        action = (r.chosen_action_json or {}).get("action_id") if isinstance(r.chosen_action_json, dict) else None
        if not action:
            continue
        prev = float(priors.get(action, 0.0))
        reward = float(r.realized_reward or 0.0)
        priors[action] = prev * (1 - alpha) + reward * alpha

    blob["weights"] = weights
    blob["action_priors"] = priors
    blob["n_updates"] = int(blob.get("n_updates") or 0) + 1
    blob["last_mean_reward"] = mean_r
    save_offline_blob(blob)

    try:
        from backend.workers.watchdog import beat

        beat(note="offline", service="safe_rl")
    except Exception:
        pass

    log_event(
        "INFO",
        "safe-rl",
        "OFFLINE_WEIGHT_UPDATE",
        extra={"n": n, "mean_reward": mean_r, "weights": weights, "wrote_setpoints": False},
    )
    return {"updated": True, "n": n, "weights": weights, "action_priors": priors, "wrote_setpoints": False}


def maybe_offline_update() -> Optional[Dict[str, Any]]:
    global _LAST_OFFLINE
    try:
        interval = float(os.getenv("HVAC_SAFE_RL_OFFLINE_SECONDS", "3600") or "3600")
    except (TypeError, ValueError):
        interval = 3600.0
    now = time.monotonic()
    if interval > 0 and _LAST_OFFLINE > 0 and (now - _LAST_OFFLINE) < interval:
        return None
    _LAST_OFFLINE = now
    return update_weights_from_log()
