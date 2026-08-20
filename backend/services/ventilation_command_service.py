"""
VentilationCommandService: Dispatches validated optimization setpoints
and persists audit trail records into the database.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid

from backend.agents.ventilation_airflow.safety_engine import ventilation_safety_engine
from backend.services.ventilation_bms_service import ventilation_bms_service
from database.session import SessionLocal
from database.models import VentilationActionDB, VentilationAuditLogDB

class VentilationCommandService:
    POINT_MAPPINGS = {
        "O10": {"target_point": "AHU-01.OutdoorAirDamperPositionSetpoint", "equipment_id": "AHU-01", "default_unit": "%"},
        "O11": {"target_point": "AHU-01.OADamper", "equipment_id": "AHU-01", "default_unit": "%"},
        "O12": {"target_point": "AHU-01.OutdoorAirflowSetpoint", "equipment_id": "AHU-01", "default_unit": "CFM"},
        "O13": {"target_point": "PARK-FAN-01.Speed", "equipment_id": "PARK-FAN-01", "default_unit": "%"},
    }

    def execute_command(self, opportunity_code: str, target_value: float, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Validates safety guardrails, sends BACnet Priority 10 dispatch, and logs audit record."""
        opp = opportunity_code.upper()
        mapping = self.POINT_MAPPINGS.get(opp)
        if not mapping:
            raise ValueError(f"Unknown opportunity code: {opp}. Supported: O10, O11, O12, O13.")

        ctx = context or {}
        current_val = float(ctx.get("current_value", target_value))

        # 1. Safety validation
        safety_res = ventilation_safety_engine.evaluate_safety(opp, current_val, target_value, ctx)
        if not safety_res.is_safe:
            return {
                "status": "BLOCKED_BY_SAFETY_GUARDRAIL",
                "opportunity_code": opp,
                "target_point": mapping["target_point"],
                "dispatched_value": None,
                "violations": safety_res.violations,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # 2. Hardware / BMS Dispatch
        bms_record = ventilation_bms_service.dispatch_point(
            opp,
            mapping["target_point"],
            target_value,
            source=ctx.get("source"),
            telemetry=ctx.get("telemetry") if isinstance(ctx.get("telemetry"), dict) else None,
        )

        # 3. Database Persistence
        db = SessionLocal()
        try:
            action_entry = VentilationActionDB(
                id=bms_record["command_id"],
                recommendation_id=ctx.get("recommendation_id", f"rec-{opp.lower()}-auto"),
                opportunity_id=opp,
                equipment_id=mapping["equipment_id"],
                target_point=mapping["target_point"],
                dispatched_value=target_value,
                previous_value=current_val,
                unit=mapping["default_unit"],
                priority_level=10,
                dispatched_by="SUPERVISORY_AI",
                bms_status="ACKNOWLEDGED"
            )
            db.add(action_entry)

            audit = VentilationAuditLogDB(
                opportunity_id=opp,
                actor="VENTILATION_COMMAND_SERVICE",
                event_type="BMS_DISPATCH",
                message=f"Dispatched {opp} setpoint {target_value} {mapping['default_unit']} to {mapping['target_point']} at Priority 10.",
                details={"command_id": bms_record["command_id"], "target_value": target_value}
            )
            db.add(audit)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"[CommandService DB Error] {e}")
        finally:
            db.close()

        return {
            "status": "SUCCESS",
            "command_id": bms_record["command_id"],
            "opportunity_code": opp,
            "target_point": mapping["target_point"],
            "dispatched_value": target_value,
            "bms_status": "ACKNOWLEDGED",
            "timestamp": bms_record["timestamp"]
        }

ventilation_command_service = VentilationCommandService()
