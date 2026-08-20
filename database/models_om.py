"""Operations & Maintenance (O17–O20) persistence. Dialect-agnostic SQLAlchemy (SQLite now, PostgreSQL-capable)."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Index, JSON
from database.base import Base


class OmOpportunityDB(Base):
    __tablename__ = "om_opportunities"
    id = Column(String, primary_key=True)  # O17–O20
    opportunity_number = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class OmTelemetryDB(Base):
    __tablename__ = "om_telemetry"
    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_id = Column(String, ForeignKey("om_opportunities.id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    source = Column(String, default="DEMO")
    quality = Column(String, default="GOOD")
    payload_json = Column(Text, nullable=True)
    electrical_power_kw = Column(Float, nullable=True)
    hvac_power_kw = Column(Float, nullable=True)
    daily_energy_kwh = Column(Float, nullable=True)
    occupancy = Column(Float, nullable=True)
    outdoor_temp_c = Column(Float, nullable=True)
    __table_args__ = (Index("ix_om_tel_opp_ts", "opportunity_id", "timestamp"),)


class OmRecommendationDB(Base):
    __tablename__ = "om_recommendations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_id = Column(String, ForeignKey("om_opportunities.id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    source = Column(String, default="OM_AGENT")
    quality = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    action = Column(String, nullable=True)
    rationale = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class OmSupervisoryDecisionDB(Base):
    __tablename__ = "om_supervisory_decisions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_id = Column(String, ForeignKey("om_opportunities.id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    source = Column(String, default="OM_SUPERVISOR")
    quality = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    decision = Column(String, nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class OmMaintenanceFindingDB(Base):
    __tablename__ = "om_maintenance_findings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_id = Column(String, default="O19", index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    source = Column(String, default="O19_AGENT")
    quality = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    equipment_id = Column(String, nullable=True)
    finding = Column(Text, nullable=True)
    energy_impact_kw = Column(Float, nullable=True)
    priority = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class OmTrainingActionDB(Base):
    __tablename__ = "om_training_actions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_id = Column(String, default="O18", index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    source = Column(String, default="OPERATOR")
    quality = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    topic = Column(String, nullable=True)
    status = Column(String, default="OPEN")
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class OmSoftwareHealthDB(Base):
    __tablename__ = "om_software_health"
    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_id = Column(String, default="O20", index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    source = Column(String, default="O20_AGENT")
    quality = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    controller_id = Column(String, nullable=True)
    software_version = Column(String, nullable=True)
    drift_pct = Column(Float, nullable=True)
    exception_count = Column(Integer, nullable=True)
    change_risk = Column(String, nullable=True)
    backup_status = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class OmDispatchDB(Base):
    __tablename__ = "om_dispatches"
    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_id = Column(String, ForeignKey("om_opportunities.id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    source = Column(String, default="OPERATOR")
    quality = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    action_type = Column(String, nullable=False)
    status = Column(String, default="RECORDED")
    payload_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class OmVerificationDB(Base):
    __tablename__ = "om_verifications"
    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_id = Column(String, ForeignKey("om_opportunities.id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    source = Column(String, default="OM_MV")
    quality = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    outcome = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class OmRollbackDB(Base):
    __tablename__ = "om_rollbacks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_id = Column(String, ForeignKey("om_opportunities.id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    source = Column(String, default="OPERATOR")
    quality = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    previous_state = Column(String, nullable=True)
    rollback_state = Column(String, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class OmAuditEventDB(Base):
    __tablename__ = "om_audit_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_id = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    source = Column(String, default="OM_AGENT")
    quality = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    actor = Column(String, default="OM_AGENT")
    event_type = Column(String, nullable=False)
    message = Column(Text, nullable=True)
    details_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class OmAgentRunDB(Base):
    __tablename__ = "om_agent_runs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_id = Column(String, ForeignKey("om_opportunities.id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    source = Column(String, default="OM_ORCHESTRATOR")
    quality = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    decision = Column(String, nullable=True)
    status = Column(String, nullable=True)
    input_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (Index("ix_om_run_opp_ts", "opportunity_id", "timestamp"),)
