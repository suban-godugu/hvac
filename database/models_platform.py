"""Platform tables: auth, canonical telemetry, control audit, runtime commands. Additive."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, Index, JSON
from database.base import Base


class HvacUserDB(Base):
    __tablename__ = "hvac_users"
    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # viewer | operator | engineer
    building_id = Column(String, nullable=True, index=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ControlAuditLogDB(Base):
    __tablename__ = "control_audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=True, index=True)
    role = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    building_id = Column(String, nullable=True, index=True)
    opportunity_id = Column(String, nullable=True, index=True)
    action = Column(String, nullable=False)
    previous_value = Column(Text, nullable=True)
    requested_value = Column(Text, nullable=True)
    decision = Column(String, nullable=True)
    safety_status = Column(String, nullable=True)
    telemetry_status = Column(String, nullable=True)
    approval_status = Column(String, nullable=True)
    reason = Column(Text, nullable=True)
    payload_json = Column(JSON, nullable=True)
    __table_args__ = (Index("ix_audit_bldg_ts", "building_id", "timestamp"),)


class CanonicalTelemetryDB(Base):
    __tablename__ = "canonical_telemetry"
    id = Column(Integer, primary_key=True, autoincrement=True)
    point_id = Column(String, nullable=False, index=True)
    building_id = Column(String, nullable=True, index=True)
    asset_id = Column(String, nullable=True, index=True)
    equipment_id = Column(String, nullable=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    value = Column(Float, nullable=True)
    unit = Column(String, nullable=True)
    source = Column(String, nullable=False)  # LIVE_BMS | SIMULATION | DEMO | HISTORIAN
    quality = Column(String, nullable=False)  # GOOD | BAD | STALE | MISSING
    age_seconds = Column(Float, nullable=True)
    __table_args__ = (Index("ix_ctel_point_ts", "point_id", "timestamp"),)


class HvacApprovalDB(Base):
    """Internal APPROVAL_REQUIRED dispatch records. Not an Approval Queue product."""
    __tablename__ = "hvac_approvals"
    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String, nullable=False, index=True)
    building_id = Column(String, nullable=True, index=True)
    opportunity_id = Column(String, nullable=True, index=True)
    requested_by = Column(String, nullable=True)
    approved_by = Column(String, nullable=True)
    status = Column(String, default="PENDING")  # PENDING | APPROVED | REJECTED
    action = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    reason = Column(Text, nullable=True)


class PlatformSettingDB(Base):
    __tablename__ = "platform_settings"
    key = Column(String, primary_key=True)
    value = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


class TenantDB(Base):
    __tablename__ = "tenants"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ZoneDB(Base):
    __tablename__ = "zones"
    id = Column(String, primary_key=True)
    building_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    floor = Column(String, nullable=True)


class ControlCommandDB(Base):
    """Internal closed-loop command records. Not a Commands product UI."""
    __tablename__ = "control_commands"
    id = Column(String, primary_key=True)
    command_id = Column(String, unique=True, nullable=False, index=True)
    opportunity = Column(String, nullable=False, index=True)
    building_id = Column(String, nullable=True, index=True)
    equipment_id = Column(String, nullable=True)
    point_id = Column(String, nullable=True)
    old_value = Column(Float, nullable=True)
    new_value = Column(Float, nullable=True)
    reason = Column(Text, nullable=True)
    engine_version = Column(String, nullable=True)
    config_version = Column(String, nullable=True)
    safety_gates = Column(JSON, nullable=True)
    requested_by = Column(String, nullable=True)
    approval_id = Column(String, nullable=True)
    status = Column(String, default="PROPOSED", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    applied_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    rollback_at = Column(DateTime, nullable=True)
    payload_json = Column(JSON, nullable=True)
    __table_args__ = (Index("uq_cmd_opp_id", "opportunity", "command_id", unique=True),)


class AgentRunDB(Base):
    __tablename__ = "agent_runs"
    id = Column(String, primary_key=True)
    opportunity = Column(String, nullable=False, index=True)
    building_id = Column(String, nullable=True)
    engine_version = Column(String, nullable=True)
    status = Column(String, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    input_json = Column(JSON, nullable=True)
    output_json = Column(JSON, nullable=True)
