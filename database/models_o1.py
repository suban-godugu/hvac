"""Additive O1 Optimum Start/Stop relational schema. Imported from database.models."""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Text, ForeignKey, Index
from database.base import Base
from datetime import datetime


def _now():
    return datetime.utcnow()


class O1PointMapDB(Base):
    __tablename__ = "o1_point_map"
    id = Column(Integer, primary_key=True, autoincrement=True)
    building_id = Column(String, ForeignKey("buildings.id"), nullable=True)
    signal = Column(String, nullable=False)
    point_id = Column(String, ForeignKey("points.id"), nullable=True)
    unit = Column(String, nullable=True)
    data_type = Column(String, default="float")
    required = Column(Boolean, default=False)
    quality_requirement = Column(String, default="GOOD")
    freshness_seconds = Column(Integer, default=30)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now)


class O1ConfigurationDB(Base):
    __tablename__ = "o1_configuration"
    id = Column(String, primary_key=True)
    building_id = Column(String, ForeignKey("buildings.id"), nullable=True)
    equipment_id = Column(String, ForeignKey("equipment.id"), nullable=True)
    scheduled_start = Column(String, default="06:00")
    scheduled_stop = Column(String, default="18:00")
    occupancy_start = Column(String, default="08:00")
    occupancy_end = Column(String, default="18:00")
    comfort_target_c = Column(Float, default=22.5)
    comfort_lower_c = Column(Float, default=21.0)
    comfort_upper_c = Column(Float, default=24.0)
    max_start_delay_min = Column(Integer, default=120)
    candidate_interval_min = Column(Integer, default=15)
    stale_telemetry_seconds = Column(Integer, default=30)
    min_runtime_min = Column(Integer, default=15)
    min_off_time_min = Column(Integer, default=15)
    safety_margin_min = Column(Float, default=6.0)
    ahu_kw = Column(Float, default=17.0)
    energy_cost_usd_kwh = Column(Float, default=0.12)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now)


class O1TelemetrySampleDB(Base):
    __tablename__ = "o1_telemetry_sample"
    id = Column(Integer, primary_key=True, autoincrement=True)
    point_id = Column(String, nullable=False)
    signal = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    value = Column(Float, nullable=True)
    unit = Column(String, nullable=True)
    quality = Column(String, default="GOOD")
    source = Column(String, default="UNKNOWN")
    raw_value = Column(String, nullable=True)
    ingested_at = Column(DateTime, default=_now)
    building_id = Column(String, nullable=True)
    equipment_id = Column(String, nullable=True)
    zone_id = Column(String, nullable=True)
    __table_args__ = (
        Index("ix_o1_tel_point_ts", "point_id", "timestamp"),
        Index("ix_o1_tel_signal_ts", "signal", "timestamp"),
        Index("ix_o1_tel_zone_ts", "zone_id", "timestamp"),
    )


class WeatherObservationDB(Base):
    __tablename__ = "weather_observation"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)
    building_id = Column(String, ForeignKey("buildings.id"), nullable=True)
    oat_c = Column(Float, nullable=True)
    rh_pct = Column(Float, nullable=True)
    solar_w_m2 = Column(Float, nullable=True)
    wind_speed_ms = Column(Float, nullable=True)
    condition = Column(String, nullable=True)
    quality = Column(String, default="GOOD")
    source = Column(String, default="UNKNOWN")
    created_at = Column(DateTime, default=_now)
    __table_args__ = (Index("ix_weather_bldg_ts", "building_id", "timestamp"),)


class OccupancyScheduleDB(Base):
    __tablename__ = "occupancy_schedule"
    id = Column(Integer, primary_key=True, autoincrement=True)
    building_id = Column(String, ForeignKey("buildings.id"), nullable=True)
    zone_id = Column(String, nullable=True)
    weekday = Column(Integer, nullable=True)
    occupancy_start = Column(String, nullable=False)
    occupancy_end = Column(String, nullable=False)
    is_holiday = Column(Boolean, default=False)
    is_weekend = Column(Boolean, default=False)
    source = Column(String, default="CONFIG")
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now)


class O1ModelDB(Base):
    __tablename__ = "o1_model"
    id = Column(String, primary_key=True)
    version = Column(String, nullable=False)
    status = Column(String, default="TRAINING")
    artifact_path = Column(String, nullable=True)
    parameters = Column(JSON, nullable=True)
    mae_minutes = Column(Float, nullable=True)
    rmse_minutes = Column(Float, nullable=True)
    r2_score = Column(Float, nullable=True)
    sample_count = Column(Integer, nullable=True)
    dataset_version = Column(String, nullable=True)
    activated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now)


class O1ModelTrainingRunDB(Base):
    __tablename__ = "o1_model_training_run"
    id = Column(String, primary_key=True)
    model_id = Column(String, ForeignKey("o1_model.id"), nullable=True)
    dataset_version = Column(String, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String, default="CREATED")
    feature_count = Column(Integer, nullable=True)
    sample_count = Column(Integer, nullable=True)
    mae_minutes = Column(Float, nullable=True)
    rmse_minutes = Column(Float, nullable=True)
    r2_score = Column(Float, nullable=True)
    mape = Column(Float, nullable=True)
    validation_score = Column(Float, nullable=True)
    test_score = Column(Float, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_now)


class O1PredictionDB(Base):
    __tablename__ = "o1_prediction"
    id = Column(String, primary_key=True)
    run_id = Column(String, nullable=True)
    model_version = Column(String, nullable=True)
    timestamp = Column(DateTime, default=_now)
    time_to_target_minutes = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    input_quality = Column(String, nullable=True)
    status = Column(String, default="OK")
    features = Column(JSON, nullable=True)
    __table_args__ = (Index("ix_o1_pred_run", "run_id"),)


class O1DailyRunDB(Base):
    __tablename__ = "o1_daily_run"
    id = Column(String, primary_key=True)
    building_id = Column(String, nullable=True)
    equipment_id = Column(String, nullable=True)
    zone_id = Column(String, nullable=True)
    status = Column(String, default="CREATED")
    failure_reason = Column(Text, nullable=True)
    model_version = Column(String, nullable=True)
    started_at = Column(DateTime, default=_now)
    completed_at = Column(DateTime, nullable=True)
    source = Column(String, default="ENGINE")
    environment = Column(String, default="production")
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now)
    __table_args__ = (Index("ix_o1_run_status", "status"),)


class O1StartCandidateDB(Base):
    __tablename__ = "o1_start_candidate"
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("o1_daily_run.id"), nullable=True)
    candidate_start = Column(String, nullable=False)
    predicted_target_reached = Column(String, nullable=True)
    pull_down_minutes = Column(Float, nullable=True)
    energy_kwh = Column(Float, nullable=True)
    comfort_margin_c = Column(Float, nullable=True)
    safety_risk = Column(String, nullable=True)
    occupancy_breach_risk = Column(String, nullable=True)
    decision = Column(String, nullable=False)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_now)
    __table_args__ = (Index("ix_o1_start_run", "run_id"),)


class O1StopCandidateDB(Base):
    __tablename__ = "o1_stop_candidate"
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("o1_daily_run.id"), nullable=True)
    candidate_stop = Column(String, nullable=False)
    predicted_temp_at_occ_end = Column(Float, nullable=True)
    runtime_saved_min = Column(Float, nullable=True)
    energy_saved_kwh = Column(Float, nullable=True)
    comfort_margin_c = Column(Float, nullable=True)
    safety_status = Column(String, nullable=True)
    decision = Column(String, nullable=False)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_now)
    __table_args__ = (Index("ix_o1_stop_run", "run_id"),)


class O1SafetyValidationDB(Base):
    __tablename__ = "o1_safety_validation"
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, nullable=True)
    check_id = Column(String, nullable=False)
    check_name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    current_value = Column(String, nullable=True)
    limit_value = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    severity = Column(String, default="INFO")
    reason = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=_now)
    __table_args__ = (Index("ix_o1_safety_run", "run_id"),)


class O1ComfortValidationDB(Base):
    __tablename__ = "o1_comfort_validation"
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, nullable=True)
    check_id = Column(String, nullable=False)
    check_name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    current_value = Column(String, nullable=True)
    limit_value = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    reason = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=_now)


class O1EnergyBaselineDB(Base):
    __tablename__ = "o1_energy_baseline"
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, nullable=True)
    methodology = Column(String, default="scheduled_runtime_x_ahu_kw")
    baseline_runtime_min = Column(Float, nullable=True)
    baseline_energy_kwh = Column(Float, nullable=True)
    created_at = Column(DateTime, default=_now)


class O1SavingsVerificationDB(Base):
    __tablename__ = "o1_savings_verification"
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, nullable=True)
    calculation_timestamp = Column(DateTime, default=_now)
    baseline_reference = Column(String, nullable=True)
    optimized_reference = Column(String, nullable=True)
    energy_baseline = Column(Float, nullable=True)
    energy_optimized = Column(Float, nullable=True)
    energy_saved = Column(Float, nullable=True)
    runtime_baseline = Column(Float, nullable=True)
    runtime_optimized = Column(Float, nullable=True)
    runtime_saved = Column(Float, nullable=True)
    verification_status = Column(String, default="PREDICTED")
    cost_saved_usd = Column(Float, nullable=True)
    source = Column(String, default="ENGINE")
