"""
PlantControlCommandService: Manages the full lifecycle of optimization commands
from safety gatekeeping to BMS dispatch and audit logging.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import uuid

try:
    from database.session import SessionLocal
    from database.models import PlantControlActionDB, PlantControlActivityLogDB
except ImportError:
    from backend.database.session import SessionLocal
    from backend.database.models import PlantControlActionDB, PlantControlActivityLogDB

from backend.services.plant_control_bms_service import plant_control_bms_service
from backend.services.plant_control_safety_service import plant_control_safety_service
from backend.services.plant_control_telemetry_service import plant_control_telemetry_service

class PlantControlCommandService:
    def __init__(self):
        self.bms = plant_control_bms_service
        self.safety = plant_control_safety_service
        self.telemetry = plant_control_telemetry_service

    def execute_command(self, opportunity: str, target_value: float, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        opp = opportunity.upper()
        ctx = context or {}

        # 1. Safety validation
        safety_res = self.safety.validate_candidate(opp, target_value, ctx)
        if not safety_res["passed"]:
            violation_msg = "; ".join(safety_res["violations"])
            self._log_activity(opp, "SAFETY_REJECT", f"Command rejected: {violation_msg}")
            raise ValueError(f"Safety guardrail violation: {violation_msg}")

        # 2. BMS Priority 10 dispatch
        bms_record = self.bms.dispatch_point(opp, target_value, priority=10)

        # 3. Telemetry buffer update
        self.telemetry.buffer_history_entry(opp, {
            "action": "DISPATCHED",
            "setpoint": bms_record["dispatched_value"],
            "unit": bms_record["unit"]
        })

        # 4. Database persistence
        db = SessionLocal()
        try:
            action_entry = PlantControlActionDB(
                id=bms_record["command_id"],
                opportunity_code=opp,
                equipment_id=bms_record.get("equipment_id", f"EQ-{opp}"),
                point_id=bms_record["target_point"],
                previous_value=bms_record.get("previous_value", bms_record["baseline_value"]),
                requested_value=bms_record["dispatched_value"],
                priority=bms_record["priority"],
                status=bms_record["stage"]
            )
            db.add(action_entry)

            log_entry = PlantControlActivityLogDB(
                opportunity_code=opp,
                stage="DISPATCHED",
                message=f"Dispatched {bms_record['target_point']} = {bms_record['dispatched_value']} {bms_record['unit']} (Priority 10)",
                detail=bms_record
            )
            db.add(log_entry)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"[PlantControlCommandService] DB error: {e}")
        finally:
            db.close()

        return bms_record

    def _log_activity(self, opportunity: str, stage: str, message: str):
        db = SessionLocal()
        try:
            entry = PlantControlActivityLogDB(
                opportunity_code=opportunity,
                stage=stage,
                message=message,
                detail=None
            )
            db.add(entry)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

plant_control_command_service = PlantControlCommandService()
