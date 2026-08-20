"""O16 Variable Head Pressure Control — Water-Cooled Condensers persistence."""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Text, Index

from database.base import Base


class O16ConfigDB(Base):
    __tablename__ = "o16_config"
    building_id = Column(String, primary_key=True)
    enabled = Column(Boolean, default=True)
    control_mode = Column(String, nullable=False, default="ADVISORY")
    control_strategy = Column(String, nullable=False, default="VSD_PUMP")
    shared_pump = Column(Boolean, default=False)
    # CONFIGURABLE — guide requires determining optimal/floating HP; no numeric formula given.
    target_head_pressure = Column(Float, nullable=True)
    target_condensing_temp_c = Column(Float, nullable=True)
    min_head_pressure = Column(Float, nullable=True)
    max_head_pressure = Column(Float, nullable=True)
    min_condensing_temp_c = Column(Float, nullable=True)
    max_condensing_temp_c = Column(Float, nullable=True)
    min_pump_speed_pct = Column(Float, nullable=True)
    max_pump_speed_pct = Column(Float, nullable=True)
    min_cw_flow = Column(Float, nullable=True)
    max_cw_flow = Column(Float, nullable=True)
    min_valve_pct = Column(Float, nullable=True)
    max_valve_pct = Column(Float, nullable=True)
    pump_trim_pct = Column(Float, nullable=True, default=2.0)
    valve_trim_pct = Column(Float, nullable=True, default=2.0)
    hp_deadband = Column(Float, nullable=True, default=2.0)
    max_pump_step_pct = Column(Float, nullable=True, default=25.0)
    high_load_pct = Column(Float, nullable=True, default=90.0)
    isolate_valve_pct = Column(Float, nullable=True, default=0.0)
    verify_tolerance = Column(Float, nullable=True, default=0.5)
    refrigerant = Column(String, nullable=True)
    config_version = Column(String, default="1.0")
    updated_at = Column(DateTime, default=datetime.utcnow)


class O16TelemetryDB(Base):
    __tablename__ = "o16_telemetry"
    id = Column(Integer, primary_key=True, autoincrement=True)
    building_id = Column(String, nullable=True, index=True)
    equipment_id = Column(String, nullable=True, index=True)
    point_id = Column(String, nullable=True, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    value = Column(Float, nullable=True)
    unit = Column(String, nullable=True)
    quality = Column(String, nullable=True)
    source = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        Index("ix_o16_tel_eq_ts", "equipment_id", "timestamp"),
        Index("ix_o16_tel_pt_ts", "point_id", "timestamp"),
        Index("ix_o16_tel_bldg_ts", "building_id", "timestamp"),
    )


class O16StateDB(Base):
    __tablename__ = "o16_state"
    id = Column(Integer, primary_key=True, autoincrement=True)
    building_id = Column(String, nullable=True, index=True)
    equipment_id = Column(String, nullable=True, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    load_ratio = Column(Float, nullable=True)
    condensing_pressure = Column(Float, nullable=True)
    condensing_temperature = Column(Float, nullable=True)
    cw_supply_temperature = Column(Float, nullable=True)
    cw_return_temperature = Column(Float, nullable=True)
    cw_flow = Column(Float, nullable=True)
    pump_speed = Column(Float, nullable=True)
    pump_power = Column(Float, nullable=True)
    valve_position = Column(Float, nullable=True)
    head_pressure_margin = Column(Float, nullable=True)
    quality = Column(String, nullable=True)
    source = Column(String, nullable=True)
    state_json = Column(JSON, nullable=True)
    __table_args__ = (
        Index("ix_o16_state_eq_ts", "equipment_id", "timestamp"),
        Index("ix_o16_state_bldg_ts", "building_id", "timestamp"),
    )


class O16RecommendationDB(Base):
    __tablename__ = "o16_recommendations"
    id = Column(String, primary_key=True)
    building_id = Column(String, nullable=True)
    equipment_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    run_id = Column(String, nullable=True, index=True)
    target_condensing_pressure = Column(Float, nullable=True)
    target_condensing_temperature = Column(Float, nullable=True)
    recommended_pump_speed = Column(Float, nullable=True)
    recommended_valve_position = Column(Float, nullable=True)
    predicted_power = Column(Float, nullable=True)
    predicted_savings = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    reason = Column(Text, nullable=True)
    engine_version = Column(String, nullable=True)
    config_version = Column(String, nullable=True)
    status = Column(String, nullable=True)
    payload_json = Column(JSON, nullable=True)
    __table_args__ = (Index("ix_o16_rec_created", "created_at"),)


class O16VerificationDB(Base):
    __tablename__ = "o16_verification"
    id = Column(Integer, primary_key=True, autoincrement=True)
    command_id = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    expected_value = Column(Float, nullable=True)
    actual_value = Column(Float, nullable=True)
    tolerance = Column(Float, nullable=True)
    verification_status = Column(String, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    details_json = Column(JSON, nullable=True)


class O16SavingsDB(Base):
    __tablename__ = "o16_savings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    building_id = Column(String, nullable=True, index=True)
    equipment_id = Column(String, nullable=True)
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    baseline_kw = Column(Float, nullable=True)
    predicted_kw = Column(Float, nullable=True)
    applied_kw = Column(Float, nullable=True)
    verified_kw = Column(Float, nullable=True)
    baseline_kwh = Column(Float, nullable=True)
    predicted_kwh = Column(Float, nullable=True)
    applied_kwh = Column(Float, nullable=True)
    verified_kwh = Column(Float, nullable=True)
    methodology = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
