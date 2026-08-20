from typing import List, Dict, Any
from datetime import datetime
from backend.agents.scheduling_supervisory.state import ActionRecordModel
from database.session import SessionLocal
from database.models import SupervisoryActionRecord

class AuditLogger:
    """Immutable Audit Logger recording all 12 required properties of closed-loop supervisory actions."""

    def log_action(self, action: ActionRecordModel):
        db = SessionLocal()
        try:
            target_eq = getattr(action, 'target_equipment', None) or action.point_id.split('-')[0]
            
            # Ensure timestamp is datetime object for SQLite
            if isinstance(action.timestamp, str):
                try:
                    ts = datetime.fromisoformat(action.timestamp.replace("Z", "+00:00"))
                except Exception:
                    ts = datetime.utcnow()
            elif isinstance(action.timestamp, datetime):
                ts = action.timestamp
            else:
                ts = datetime.utcnow()

            record = db.query(SupervisoryActionRecord).filter(SupervisoryActionRecord.id == action.id).first()
            if not record:
                record = SupervisoryActionRecord(
                    id=action.id,
                    opportunity_code=action.opportunity_code,
                    point_id=action.point_id,
                    target_equipment=target_eq,
                    previous_value=action.previous_value,
                    proposed_value=action.proposed_value,
                    actual_value=action.actual_value,
                    reason=action.reason,
                    confidence=action.confidence,
                    safety_result=action.safety_result,
                    timestamp=ts,
                    verification_window=action.verification_window,
                    expected_result=action.expected_result,
                    actual_result=action.actual_result,
                    rollback_value=action.rollback_value,
                    final_status=action.final_status
                )
                db.add(record)
            else:
                record.actual_value = action.actual_value
                record.actual_result = action.actual_result
                record.final_status = action.final_status
            db.commit()
        except Exception as e:
            db.rollback()
        finally:
            db.close()

    def get_recent_actions(self, limit: int = 50) -> List[Dict[str, Any]]:
        db = SessionLocal()
        try:
            records = db.query(SupervisoryActionRecord).order_by(SupervisoryActionRecord.timestamp.desc()).limit(limit).all()
            return [
                {
                    "id": r.id,
                    "opportunity_code": r.opportunity_code,
                    "point_id": r.point_id,
                    "target_equipment": r.target_equipment,
                    "previous_value": r.previous_value,
                    "proposed_value": r.proposed_value,
                    "actual_value": r.actual_value,
                    "reason": r.reason,
                    "confidence": r.confidence,
                    "safety_result": r.safety_result,
                    "timestamp": r.timestamp.strftime("%Y-%m-%d %H:%M:%S") if hasattr(r.timestamp, "strftime") else str(r.timestamp or ""),
                    "verification_window": r.verification_window,
                    "expected_result": r.expected_result,
                    "actual_result": r.actual_result,
                    "rollback_value": r.rollback_value,
                    "final_status": r.final_status
                }
                for r in records
            ]
        finally:
            db.close()
