"""Persist Safe-RL decisions and audit events."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database.models_opportunities import OpportunityAuditEventDB
from database.models_platform import SafeRlDecisionDB
from database.session import SessionLocal


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def new_decision_id() -> str:
    return f"srl_{uuid.uuid4().hex[:12]}"


def _sanitize_snapshot(state: Dict[str, Any]) -> Dict[str, Any]:
    """Drop non-JSON-safe keys for persistence."""
    out = dict(state)
    out.pop("candidates", None)
    return out


def save_decision(
    *,
    decision_id: Optional[str] = None,
    zone_id: str,
    building_id: Optional[str],
    status: str,
    winner: Optional[Dict[str, Any]],
    rejected_actions: List[Dict[str, Any]],
    constraints: List[str],
    state_snapshot: Dict[str, Any],
    mapped_commands: List[Dict[str, Any]],
    confidence: float,
) -> Dict[str, Any]:
    decision_id = decision_id or new_decision_id()
    score = float(winner.get("score") or 0.0) if winner else None
    mapped_ids = [c.get("command_id") for c in mapped_commands if c.get("command_id")]

    db = SessionLocal()
    try:
        row = SafeRlDecisionDB(
            id=decision_id,
            building_id=building_id,
            zone_id=zone_id,
            status=status,
            chosen_action_json=winner,
            rejected_actions_json=rejected_actions,
            constraints_json=constraints,
            state_snapshot_json=_sanitize_snapshot(state_snapshot),
            score=score,
            confidence=confidence,
            mapped_command_ids_json=mapped_ids,
            created_at=_now(),
        )
        db.add(row)
        db.add(
            OpportunityAuditEventDB(
                timestamp=_now(),
                actor="SAFE_RL",
                opportunity_id="SAFE_RL",
                equipment_id=zone_id,
                action="SAFE_RL_RECOMMEND",
                result=status,
                details={
                    "decision_id": decision_id,
                    "chosen_action_id": (winner or {}).get("action_id"),
                    "mapped_command_ids": mapped_ids,
                    "score": score,
                    "confidence": confidence,
                },
            )
        )
        db.commit()
        db.refresh(row)
        return _dump(row, mapped_commands)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _load_mapped_commands(db, command_ids: List[str]) -> List[Dict[str, Any]]:
    from database.models_platform import ControlCommandDB

    if not command_ids:
        return []
    rows = db.query(ControlCommandDB).filter(ControlCommandDB.command_id.in_(command_ids)).all()
    by_id = {r.command_id: r for r in rows}
    out = []
    for cid in command_ids:
        row = by_id.get(cid)
        if row:
            out.append(
                {
                    "command_id": row.command_id,
                    "opportunity": row.opportunity,
                    "point_id": row.point_id,
                    "old_value": row.old_value,
                    "new_value": row.new_value,
                    "status": row.status,
                }
            )
    return out


def _dump(row: SafeRlDecisionDB, mapped_commands: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    cmds = mapped_commands
    if cmds is None:
        db = SessionLocal()
        try:
            ids = list(row.mapped_command_ids_json or [])
            cmds = _load_mapped_commands(db, ids)
        finally:
            db.close()
    return {
        "decision_id": row.id,
        "opportunity_id": "SAFE_RL",
        "status": row.status,
        "zone_id": row.zone_id,
        "building_id": row.building_id,
        "score": row.score,
        "confidence": row.confidence,
        "chosen_action": row.chosen_action_json,
        "rejected_actions": row.rejected_actions_json or [],
        "constraints": row.constraints_json or [],
        "state_snapshot": row.state_snapshot_json or {},
        "mapped_command_ids": row.mapped_command_ids_json or [],
        "mapped_commands": cmds or [],
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "realized_reward": row.realized_reward,
        "reward_energy": row.reward_energy,
        "reward_comfort": row.reward_comfort,
        "reward_equipment": row.reward_equipment,
        "measured_at": row.measured_at.isoformat() if getattr(row, "measured_at", None) else None,
        "command_id": getattr(row, "command_id", None),
        "wrote_setpoints": False,
    }


def get_decision_by_id(decision_id: str) -> Optional[Dict[str, Any]]:
    db = SessionLocal()
    try:
        row = db.query(SafeRlDecisionDB).filter_by(id=decision_id).first()
        if not row:
            return None
        return _dump(row, None)
    finally:
        db.close()


def list_recent(limit: int = 20) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        rows = (
            db.query(SafeRlDecisionDB)
            .order_by(SafeRlDecisionDB.created_at.desc())
            .limit(max(1, min(100, int(limit))))
            .all()
        )
        return [_dump(r, None) for r in rows]
    finally:
        db.close()


def latest_decision(zone_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    db = SessionLocal()
    try:
        q = db.query(SafeRlDecisionDB).order_by(SafeRlDecisionDB.created_at.desc())
        if zone_id:
            q = q.filter(SafeRlDecisionDB.zone_id == zone_id)
        row = q.first()
        if not row:
            return None
        return _dump(row, None)
    finally:
        db.close()
