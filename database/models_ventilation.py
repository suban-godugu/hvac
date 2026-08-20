"""Wide ventilation telemetry snapshots and optimization results (O10–O13)."""
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Index,
)
from database.base import Base


class HvacTelemetryDB(Base):
    __tablename__ = "hvac_telemetry"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    site_id = Column(String, default="SKYLINE-BLR")
    ahu_id = Column(String, default="AHU-01")
    zone_id = Column(String, nullable=True)
    outdoor_temp_c = Column(Float, nullable=True)
    outdoor_rh_percent = Column(Float, nullable=True)
    outdoor_enthalpy_kjkg = Column(Float, nullable=True)
    return_temp_c = Column(Float, nullable=True)
    return_rh_percent = Column(Float, nullable=True)
    return_enthalpy_kjkg = Column(Float, nullable=True)
    supply_air_temp_c = Column(Float, nullable=True)
    supply_airflow_cfm = Column(Float, nullable=True)
    mixed_air_temp_c = Column(Float, nullable=True)
    damper_percent = Column(Float, nullable=True)
    co2_ppm = Column(Float, nullable=True)
    co_ppm = Column(Float, nullable=True)
    fan_power_kw = Column(Float, nullable=True)
    chiller_power_kw = Column(Float, nullable=True)
    total_hvac_power_kw = Column(Float, nullable=True)
    occupancy = Column(Float, nullable=True)
    occupied = Column(Boolean, nullable=True)
    schedule_state = Column(String, nullable=True)
    return_airflow_cfm = Column(Float, nullable=True)
    quality = Column(String, default="GOOD")
    source = Column(String, default="DEMO")
    site_name = Column(String, nullable=True)
    site_location = Column(String, nullable=True)
    plant_label = Column(String, nullable=True)
    building_area_sqft = Column(Float, nullable=True)

    __table_args__ = (
        Index("ix_hvac_tel_site_ts", "site_id", "timestamp"),
        Index("ix_hvac_tel_ahu_ts", "ahu_id", "timestamp"),
        Index("ix_hvac_tel_zone_ts", "zone_id", "timestamp"),
        Index("ix_hvac_tel_source", "source"),
    )


class HvacOptimizationResultDB(Base):
    __tablename__ = "hvac_optimization_results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_id = Column(String, ForeignKey("hvac_opportunities.id"), nullable=False, index=True)
    telemetry_id = Column(Integer, ForeignKey("hvac_telemetry.id"), nullable=True, index=True)
    current_value = Column(Float, nullable=True)
    optimized_value = Column(Float, nullable=True)
    energy_savings_kw = Column(Float, nullable=True)
    daily_savings_kwh = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    guardrail_pass = Column(Boolean, nullable=True)
    recommendation = Column(String, nullable=True)
    rationale = Column(Text, nullable=True)
    status = Column(String, nullable=True)
    payload_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (Index("ix_hvac_opt_opp_ts", "opportunity_id", "created_at"),)


class HvacOptimizationCandidateDB(Base):
    __tablename__ = "hvac_optimization_candidates"
    id = Column(Integer, primary_key=True, autoincrement=True)
    optimization_result_id = Column(Integer, ForeignKey("hvac_optimization_results.id"), nullable=False, index=True)
    candidate_id = Column(String, nullable=False)
    damper_position_percent = Column(Float, nullable=True)
    mixed_air_temp_c = Column(Float, nullable=True)
    chiller_power_kw = Column(Float, nullable=True)
    free_cooling_kw = Column(Float, nullable=True)
    economizer_mode = Column(String, nullable=True)
    outdoor_air_cfm = Column(Float, nullable=True)
    decision = Column(String, nullable=True)
    rejection_reason = Column(String, nullable=True)
