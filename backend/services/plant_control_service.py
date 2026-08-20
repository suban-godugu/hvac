"""
PlantControlService: Primary coordinator combining Telemetry, BMS, Safety,
Commands, Verification, Realtime, and Database for Opportunities 5 through 9.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid

try:
    from database.session import SessionLocal
    from database.models import (
        PlantControlTelemetryDB,
        PlantControlDecisionDB,
        PlantControlActionDB,
        PlantControlVerificationDB,
        PlantControlRollbackDB,
        PlantControlRetrofitAssessmentDB,
        PlantControlActivityLogDB
    )
except ImportError:
    from backend.database.session import SessionLocal
    from backend.database.models import (
        PlantControlTelemetryDB,
        PlantControlDecisionDB,
        PlantControlActionDB,
        PlantControlVerificationDB,
        PlantControlRollbackDB,
        PlantControlRetrofitAssessmentDB,
        PlantControlActivityLogDB
    )

from backend.agents.plant_control.plant_control_agent import plant_control_agent
from backend.services.plant_control_telemetry_service import plant_control_telemetry_service
from backend.services.plant_control_bms_service import plant_control_bms_service
from backend.services.plant_control_safety_service import plant_control_safety_service
from backend.services.plant_control_command_service import plant_control_command_service
from backend.services.plant_control_verification_service import plant_control_verification_service
from backend.services.plant_control_realtime_service import plant_control_realtime_service
from backend.services.plant_control_provenance import stamp_plant_provenance

class PlantControlService:
    def __init__(self):
        self.agent = plant_control_agent
        self.telemetry = plant_control_telemetry_service
        self.bms = plant_control_bms_service
        self.safety = plant_control_safety_service
        self.commands = plant_control_command_service
        self.verification = plant_control_verification_service
        self.realtime = plant_control_realtime_service

    def get_dashboard_state(self) -> Dict[str, Any]:
        """Returns the high-level plant control fleet dashboard state."""
        return self.agent.get_fleet_summary()

    def get_o5_state(self) -> Dict[str, Any]:
        """Returns live O5 Duct Static Pressure Reset state and candidate matrix."""
        return stamp_plant_provenance(self.agent.o5.generate_and_evaluate_candidates(), "O5")

    def get_o6_state(self) -> Dict[str, Any]:
        """Returns live O6 Heating Hot Water Delivery Temperature Reset state."""
        return self.agent.o6.generate_and_evaluate_candidates()

    def get_o7_state(self) -> Dict[str, Any]:
        """Returns live O7 Chilled Water Delivery Temperature Reset state."""
        return self.agent.o7.generate_and_evaluate_candidates()

    def get_o8_state(self) -> Dict[str, Any]:
        """Returns live O8 Condenser Water Delivery Temperature Reset state."""
        return self.agent.o8.generate_and_evaluate_candidates()

    def get_o9_assessment(self) -> Dict[str, Any]:
        """Returns live O9 Electronic Expansion Valve Retrofit Assessment."""
        return stamp_plant_provenance(self.agent.o9.evaluate_retrofit_feasibility(), "O9")

    def get_activity_log(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Returns recent activity logs for Plant Control Parameter Optimizations."""
        db = SessionLocal()
        try:
            logs = db.query(PlantControlActivityLogDB).order_by(PlantControlActivityLogDB.timestamp.desc()).limit(limit).all()
            if logs:
                return [
                    {
                        "id": log.id,
                        "timestamp": log.timestamp.isoformat() if hasattr(log.timestamp, "isoformat") else str(log.timestamp),
                        "opportunity": log.opportunity_code,
                        "stage": log.stage,
                        "message": log.message,
                        "detail": log.detail
                    }
                    for log in logs
                ]
        except Exception as e:
            print(f"[PlantControlService] Activity log error: {e}")
        finally:
            db.close()
        return []

    def log_activity(self, opportunity: str, stage: str, message: str, detail: Optional[Dict[str, Any]] = None):
        """Persists a new event to the plant control activity log."""
        db = SessionLocal()
        try:
            entry = PlantControlActivityLogDB(
                opportunity_code=opportunity,
                stage=stage,
                message=message,
                detail=detail
            )
            db.add(entry)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"[PlantControlService] Failed to log activity: {e}")
        finally:
            db.close()

plant_control_service = PlantControlService()
