"""
VariableSpeedCommandService: Validates safety guardrails, sends BACnet Priority 10 dispatch,
and logs audit trail records.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid

from backend.agents.variable_speed.safety_engine import vs_safety_engine
from backend.services.variable_speed_bms_service import vs_bms_service
from database.session import SessionLocal
from database.models import VariableSpeedActionDB, VariableSpeedAuditLogDB

class VariableSpeedCommandService:
    def execute_command(self, equipment_id: str, target_speed_pct: float, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ctx = context or {}
        current_speed = float(ctx.get("current_speed", target_speed_pct))

        # 1. Safety Guardrail Evaluation
        safety_res = vs_safety_engine.evaluate_safety(equipment_id, current_speed, target_speed_pct, ctx)
        if not safety_res.is_safe:
            return {
                "status": "BLOCKED_BY_SAFETY_GUARDRAIL",
                "equipment_id": equipment_id,
                "target_speed_pct": None,
                "violations": safety_res.violations,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # 2. BACnet Priority 10 Dispatch
        bms_record = vs_bms_service.dispatch_vfd_speed(equipment_id, target_speed_pct)

        # 3. Database Persistence
        db = SessionLocal()
        try:
            action = VariableSpeedActionDB(
                id=bms_record["command_id"],
                recommendation_id=ctx.get("recommendation_id", f"rec-{equipment_id.lower()}"),
                equipment_id=equipment_id,
                opportunity_id=ctx.get("opportunity_id", f"VS-{equipment_id}"),
                target_point=bms_record["target_point"],
                dispatched_value=target_speed_pct,
                previous_value=current_speed,
                unit="%",
                priority_level=10,
                dispatched_by="VARIABLE_SPEED_AI",
                bms_status="ACKNOWLEDGED"
            )
            db.add(action)

            audit = VariableSpeedAuditLogDB(
                agent="VARIABLE_SPEED_COMMAND_SERVICE",
                equipment_id=equipment_id,
                current_value=current_speed,
                recommended_value=target_speed_pct,
                final_value=target_speed_pct,
                reason=ctx.get("reason", "Optimized VFD speed dispatch."),
                confidence=float(ctx.get("confidence", 0.96)),
                safety_result="PASS",
                operator_mode="AUTO_CLOSED_LOOP",
                dispatch_result="SUCCESS",
                verification_result="PENDING_15M_MV",
                details={"command_id": bms_record["command_id"], "target_speed": target_speed_pct}
            )
            db.add(audit)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"[VS CommandService DB Error] {e}")
        finally:
            db.close()

        return {
            "status": "SUCCESS",
            "command_id": bms_record["command_id"],
            "equipment_id": equipment_id,
            "target_point": bms_record["target_point"],
            "dispatched_speed_pct": target_speed_pct,
            "frequency_hz": bms_record["frequency_hz"],
            "bms_status": "ACKNOWLEDGED",
            "timestamp": bms_record["timestamp"]
        }

vs_command_service = VariableSpeedCommandService()
