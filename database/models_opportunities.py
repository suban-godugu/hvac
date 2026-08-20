"""Shared opportunity catalog, executions, optimization results, audit, and O18–O20 tables."""
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    JSON,
    Text,
    ForeignKey,
    Index,
)
from database.base import Base


class HvacOpportunityDB(Base):
    __tablename__ = "hvac_opportunities"
    id = Column(String, primary_key=True)  # O11, O13, O15...
    opportunity_number = Column(Integer, nullable=False)
    section = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String, default="ACTIVE")
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class AgentExecutionDB(Base):
    __tablename__ = "agent_executions"
    id = Column(String, primary_key=True)
    agent_id = Column(String, nullable=False)
    opportunity_id = Column(String, ForeignKey("hvac_opportunities.id"), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String, default="RUNNING")
    input_timestamp = Column(DateTime, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)


class OpportunityOptimizationResultDB(Base):
    __tablename__ = "opportunity_optimization_results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_id = Column(String, ForeignKey("hvac_opportunities.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    current_value = Column(Float, nullable=True)
    optimized_value = Column(Float, nullable=True)
    energy_impact = Column(Float, nullable=True)
    comfort_impact = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    reason = Column(Text, nullable=True)
    status = Column(String, default="PROPOSED")

    __table_args__ = (Index("ix_opt_result_opp_ts", "opportunity_id", "timestamp"),)


class OpportunityAuditEventDB(Base):
    __tablename__ = "opportunity_audit_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    actor = Column(String, default="SUPERVISORY_SERVICE")
    opportunity_id = Column(String, nullable=False)
    equipment_id = Column(String, nullable=True)
    action = Column(String, nullable=False)
    result = Column(String, nullable=False)
    details = Column(JSON, nullable=True)


class COMeasurementDB(Base):
    """O13 DCV-CO safety-critical measurements (sibling of co2_measurements)."""
    __tablename__ = "co_measurements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    zone_id = Column(String, nullable=False)
    co_ppm = Column(Float, nullable=False)
    co_trend = Column(String, nullable=True)
    fan_state = Column(String, nullable=True)
    fan_speed = Column(Float, nullable=True)
    damper_pct = Column(Float, nullable=True)
    airflow_cfm = Column(Float, nullable=True)
    quality = Column(String, default="GOOD")
    source = Column(String, default="BACnet_IP")

    __table_args__ = (Index("ix_co_zone_ts", "zone_id", "timestamp"),)


class TrainingProgramDB(Base):
    __tablename__ = "training_programs"
    id = Column(String, primary_key=True)
    topic = Column(String, nullable=False)
    program_name = Column(String, nullable=False)
    required = Column(Boolean, default=False)
    status = Column(String, default="ACTIVE")


class TrainingCompletionDB(Base):
    __tablename__ = "training_completions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    program_id = Column(String, ForeignKey("training_programs.id"), nullable=False)
    role_label = Column(String, default="OPERATOR")
    completion_pct = Column(Float, default=0.0)
    status = Column(String, default="IN_PROGRESS")
    completed_at = Column(DateTime, nullable=True)


class MaintenanceWorkOrderDB(Base):
    __tablename__ = "maintenance_work_orders"
    id = Column(String, primary_key=True)
    equipment_id = Column(String, nullable=False)
    maintenance_type = Column(String, nullable=False)
    status = Column(String, default="OPEN")
    due_date = Column(DateTime, nullable=True)
    runtime_hours = Column(Float, nullable=True)
    efficiency = Column(Float, nullable=True)
    degradation = Column(Float, nullable=True)
    priority = Column(String, default="MEDIUM")
    recommendation = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class ControllerSoftwareStatusDB(Base):
    __tablename__ = "controller_software_status"
    id = Column(Integer, primary_key=True, autoincrement=True)
    controller_id = Column(String, nullable=False)
    software_version = Column(String, nullable=True)
    firmware_version = Column(String, nullable=True)
    comm_status = Column(String, default="UNKNOWN")
    point_quality = Column(String, default="UNKNOWN")
    override_state = Column(String, nullable=True)
    alarm_state = Column(String, nullable=True)
    control_loop_state = Column(String, nullable=True)
    last_communication = Column(DateTime, nullable=True)
    health_status = Column(String, default="UNKNOWN")
    updated_at = Column(DateTime, default=datetime.utcnow)
