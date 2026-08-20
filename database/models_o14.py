"""O14 Optimised Secondary Chilled Water Pumping persistence.

Uses shared control_commands, canonical_telemetry, agent_runs, and
opportunity_audit_events for command/audit lifecycle.
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Text, Index, UniqueConstraint

from database.base import Base


class O14ConfigDB(Base):
    __tablename__ = "o14_config"
    building_id = Column(String, primary_key=True)
    # SOURCE-GUIDE: most-open CHW valve target (OEH HVAC guide Opportunity 14).
    most_open_valve_target_pct = Column(Float, nullable=False, default=95.0)
    # CONFIGURABLE_DEFAULT — guide says incremental DP reset, no numeric step.
    dp_setpoint_trim = Column(Float, nullable=True, default=0.5)
    dp_setpoint_trim_unit = Column(String, nullable=True, default="psi")
    speed_trim_pct = Column(Float, nullable=True, default=2.0)
    min_pump_speed_pct = Column(Float, nullable=True)
    max_pump_speed_pct = Column(Float, nullable=True)
    min_dp = Column(Float, nullable=True)
    max_dp = Column(Float, nullable=True)
    min_flow = Column(Float, nullable=True)
    max_flow = Column(Float, nullable=True)
    max_speed_step_pct = Column(Float, nullable=True, default=25.0)
    verify_tolerance = Column(Float, nullable=True, default=0.5)
    control_mode = Column(String, nullable=False, default="ADVISORY")
    enabled = Column(Boolean, default=True)
    config_version = Column(String, default="1.0")
    updated_at = Column(DateTime, default=datetime.utcnow)


class O14SystemSnapshotDB(Base):
    __tablename__ = "o14_system_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    building_id = Column(String, nullable=True, index=True)
    equipment_id = Column(String, nullable=True, index=True)
    flow = Column(Float, nullable=True)
    dp = Column(Float, nullable=True)
    dp_setpoint = Column(Float, nullable=True)
    speed = Column(Float, nullable=True)
    power = Column(Float, nullable=True)
    valve_position = Column(Float, nullable=True)
    most_open_valve_pct = Column(Float, nullable=True)
    supply_temperature = Column(Float, nullable=True)
    return_temperature = Column(Float, nullable=True)
    load = Column(Float, nullable=True)
    pumps_running = Column(Integer, nullable=True)
    cooling_call = Column(Float, nullable=True)
    status = Column(String, nullable=True)
    quality = Column(String, nullable=True)
    source = Column(String, nullable=True)
    payload_json = Column(JSON, nullable=True)
    __table_args__ = (
        Index("ix_o14_snap_eq_ts", "equipment_id", "timestamp"),
        Index("ix_o14_snap_bldg_ts", "building_id", "timestamp"),
    )


class O14RecommendationDB(Base):
    __tablename__ = "o14_recommendations"
    recommendation_id = Column(String, primary_key=True)
    run_id = Column(String, nullable=True, index=True)
    building_id = Column(String, nullable=True)
    point_id = Column(String, nullable=True)
    current_value = Column(Float, nullable=True)
    recommended_value = Column(Float, nullable=True)
    unit = Column(String, nullable=True)
    reason = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    safety_result = Column(String, nullable=True)
    status = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    payload_json = Column(JSON, nullable=True)
    __table_args__ = (Index("ix_o14_rec_created", "created_at"),)
