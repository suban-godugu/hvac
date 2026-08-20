"""O15 Variable Head Pressure Control — Air-Cooled Condensers persistence."""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Text, Index

from database.base import Base


class O15ConfigDB(Base):
    __tablename__ = "o15_config"
    building_id = Column(String, primary_key=True)
    # SOURCE-GUIDE range: condensing temperature typically 8–12°C above ambient DB.
    approach_c = Column(Float, nullable=False, default=10.0)
    approach_min_c = Column(Float, nullable=False, default=8.0)
    approach_max_c = Column(Float, nullable=False, default=12.0)
    # CONFIGURABLE — guide does not specify numeric HP/fan steps or manufacturer envelope.
    min_head_pressure = Column(Float, nullable=True)
    max_head_pressure = Column(Float, nullable=True)
    min_condensing_temp_c = Column(Float, nullable=True)
    max_condensing_temp_c = Column(Float, nullable=True)
    min_fan_speed_pct = Column(Float, nullable=True)
    max_fan_speed_pct = Column(Float, nullable=True)
    fan_trim_pct = Column(Float, nullable=True, default=2.0)
    tcond_deadband_c = Column(Float, nullable=True, default=0.5)
    max_fan_step_pct = Column(Float, nullable=True, default=25.0)
    verify_tolerance = Column(Float, nullable=True, default=0.5)
    refrigerant = Column(String, nullable=True)
    saturation_curve_json = Column(JSON, nullable=True)
    control_mode = Column(String, nullable=False, default="ADVISORY")
    enabled = Column(Boolean, default=True)
    config_version = Column(String, default="1.0")
    updated_at = Column(DateTime, default=datetime.utcnow)


class O15SystemSnapshotDB(Base):
    __tablename__ = "o15_system_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    building_id = Column(String, nullable=True, index=True)
    equipment_id = Column(String, nullable=True, index=True)
    outdoor_air_temperature = Column(Float, nullable=True)
    head_pressure = Column(Float, nullable=True)
    head_pressure_setpoint = Column(Float, nullable=True)
    condensing_temperature = Column(Float, nullable=True)
    fan_speed = Column(Float, nullable=True)
    fan_power = Column(Float, nullable=True)
    compressor_load = Column(Float, nullable=True)
    compressor_power = Column(Float, nullable=True)
    cooling_load = Column(Float, nullable=True)
    fans_running = Column(Integer, nullable=True)
    status = Column(String, nullable=True)
    quality = Column(String, nullable=True)
    source = Column(String, nullable=True)
    payload_json = Column(JSON, nullable=True)
    __table_args__ = (
        Index("ix_o15_snap_eq_ts", "equipment_id", "timestamp"),
        Index("ix_o15_snap_bldg_ts", "building_id", "timestamp"),
    )


class O15RecommendationDB(Base):
    __tablename__ = "o15_recommendations"
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
    __table_args__ = (Index("ix_o15_rec_created", "created_at"),)
