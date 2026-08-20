from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Text, ForeignKey, Index
from datetime import datetime

from database.base import Base

class Building(Base):
    __tablename__ = "buildings"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    area_sqft = Column(Float, nullable=False)
    floors = Column(Integer, nullable=False)
    design_cooling_tonnage = Column(Float, nullable=False)
    location = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Equipment(Base):
    __tablename__ = "equipment"
    id = Column(String, primary_key=True)
    building_id = Column(String, ForeignKey("buildings.id"))
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # CHILLER, COMPRESSOR, AHU, VAV, PUMP
    specs = Column(JSON, nullable=True)

class EngineeringLimitDB(Base):
    __tablename__ = "engineering_limits"
    id = Column(String, primary_key=True) # e.g. "bldg-corp-hq-01"
    config_json = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Point(Base):
    __tablename__ = "points"
    id = Column(String, primary_key=True)
    equipment_id = Column(String, ForeignKey("equipment.id"), nullable=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    point_type = Column(String, nullable=False) # AI, AO, BI, BO
    unit = Column(String, nullable=True)
    current_value = Column(Float, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow)

class SupervisoryActionRecord(Base):
    """Immutable log of closed-loop supervisory control actions containing all 12 required fields."""
    __tablename__ = "supervisory_actions"
    id = Column(String, primary_key=True)
    opportunity_code = Column(String, nullable=False) # O1, O2, O3, O4
    point_id = Column(String, nullable=False)
    target_equipment = Column(String, nullable=True)
    previous_value = Column(Float, nullable=True)
    proposed_value = Column(Float, nullable=False)
    actual_value = Column(Float, nullable=True)
    reason = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    safety_result = Column(JSON, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    verification_window = Column(Integer, default=15)
    expected_result = Column(String, nullable=False)
    actual_result = Column(String, nullable=True)
    rollback_value = Column(Float, nullable=True)
    final_status = Column(String, nullable=False)

class EnergySavingsMetric(Base):
    __tablename__ = "energy_savings_metrics"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    tier = Column(String, nullable=False)
    opportunity_code = Column(String, nullable=False)
    power_kw_saved = Column(Float, nullable=False)
    kwh_saved_cumulative = Column(Float, nullable=False)
    cost_saved_usd = Column(Float, nullable=False)
    comfort_index_pct = Column(Float, default=100.0)

class ZoneTelemetryDB(Base):
    __tablename__ = "zone_telemetry"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    zone_id = Column(String, nullable=False)
    actual_temperature = Column(Float, nullable=False)
    current_setpoint = Column(Float, nullable=False)
    optimized_setpoint = Column(Float, nullable=True)
    deadband = Column(Float, nullable=False)
    occupancy = Column(Boolean, default=True)
    cooling_demand = Column(Float, default=0.0)
    heating_demand = Column(Float, default=0.0)
    damper_position = Column(Float, default=30.0)
    cooling_valve = Column(Float, default=0.0)
    reheat_valve = Column(Float, default=0.0)
    airflow_cfm = Column(Float, default=1200.0)
    sensor_quality = Column(String, default="GOOD")

class O2DecisionDB(Base):
    __tablename__ = "o2_decisions"
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    zone_id = Column(String, nullable=False)
    previous_setpoint = Column(Float, nullable=False)
    recommended_setpoint = Column(Float, nullable=False)
    comfort_band_min = Column(Float, nullable=False)
    comfort_band_max = Column(Float, nullable=False)
    expected_savings_kw = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    safety_check = Column(String, nullable=False)
    status = Column(String, nullable=False)

class O2ActionDB(Base):
    __tablename__ = "o2_actions"
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    zone_id = Column(String, nullable=False)
    target_point = Column(String, nullable=False)
    applied_value = Column(Float, nullable=False)
    previous_value = Column(Float, nullable=False)
    status = Column(String, default="APPLIED")
    verification_status = Column(String, default="VERIFIED_KEPT")
    comfort_impact = Column(String, default="PASS")
    rollback_performed = Column(Boolean, default=False)

class O3DecisionDB(Base):
    __tablename__ = "o3_decisions"
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ahu_id = Column(String, nullable=False)
    previous_sat_sp = Column(Float, nullable=False)
    recommended_sat_sp = Column(Float, nullable=False)
    master_demand_pct = Column(Float, nullable=False)
    fan_power_kw = Column(Float, nullable=False)
    chiller_power_kw = Column(Float, nullable=False)
    net_power_shed_kw = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    safety_check = Column(String, nullable=False)
    status = Column(String, nullable=False)

class O3ActionDB(Base):
    __tablename__ = "o3_actions"
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ahu_id = Column(String, nullable=False)
    target_point = Column(String, nullable=False)
    applied_sat_sp = Column(Float, nullable=False)
    previous_sat_sp = Column(Float, nullable=False)
    status = Column(String, default="APPLIED")
    verification_status = Column(String, default="VERIFIED_KEPT")
    actual_sat_reading = Column(Float, nullable=True)
    comfort_impact = Column(String, default="PASS")
    rollback_performed = Column(Boolean, default=False)

class O4DecisionDB(Base):
    __tablename__ = "o4_decisions"
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    current_active_chillers = Column(Integer, nullable=False)
    recommended_active_chillers = Column(Integer, nullable=False)
    total_cooling_load_tons = Column(Float, nullable=False)
    average_plr_pct = Column(Float, nullable=False)
    staging_action = Column(String, nullable=False)
    total_lift_head = Column(Float, nullable=False)
    total_plant_power_kw = Column(Float, nullable=False)
    expected_power_shed_kw = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    safety_check = Column(String, nullable=False)
    status = Column(String, nullable=False)

class O4ActionDB(Base):
    __tablename__ = "o4_actions"
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    target_equipment = Column(String, nullable=False)
    action_type = Column(String, nullable=False)
    chillers_running = Column(Integer, nullable=False)
    status = Column(String, default="APPLIED")
    verification_status = Column(String, default="VERIFIED_KEPT")
    actual_power_kw = Column(Float, nullable=True)
    rollback_performed = Column(Boolean, default=False)

class O1ThermalTelemetryDB(Base):
    __tablename__ = "o1_thermal_telemetry"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    oat = Column(Float, nullable=False)
    indoor_temp = Column(Float, nullable=False)
    target_setpoint = Column(Float, default=22.0)
    ahu_status = Column(String, default="RUNNING")
    heating_demand = Column(Float, default=0.0)
    cooling_demand = Column(Float, default=0.0)
    solar_gain_index = Column(Float, default=0.5)
    building_mass_temp = Column(Float, default=22.5)
    occupancy_state = Column(Boolean, default=True)

class O1DecisionDB(Base):
    __tablename__ = "o1_decisions"
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    building_id = Column(String, default="bldg-corp-hq-01")
    scheduled_start = Column(String, default="06:00")
    optimized_start = Column(String, nullable=False)
    start_delay_min = Column(Float, nullable=True)
    start_confidence = Column(Float, nullable=True)
    start_decision = Column(String, nullable=True)
    scheduled_stop = Column(String, default="18:00")
    optimized_stop = Column(String, nullable=True)
    coast_advance_min = Column(Float, nullable=True)
    stop_confidence = Column(Float, nullable=True)
    stop_decision = Column(String, nullable=True)
    thermal_rate_used = Column(Float, nullable=True)
    predicted_savings_kwh = Column(Float, nullable=True)
    safety_check = Column(String, default="PASS")
    model_version = Column(String, default="O1-v1.2.0")
    reason = Column(String, default="")
    confidence = Column(Float, default=0.0)
    coast_reduction_min = Column(Float, default=0.0)
    coast_decision = Column(String, default="")
    safety_result = Column(String, default="PASS")
    energy_saved_kwh = Column(Float, default=0.0)

class O1ActionDB(Base):
    __tablename__ = "o1_actions"
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action_type = Column(String, nullable=False)
    target_equipment = Column(String, default="AHU-01")
    previous_state = Column(String, default="OFF")
    requested_state = Column(String, default="STARTING")
    applied_state = Column(String, default="RUNNING")
    bms_status = Column(String, default="ACKNOWLEDGED")
    verification_status = Column(String, default="PENDING")
    actual_response = Column(String, nullable=True)
    rollback_applied = Column(Boolean, default=False)
    run_id = Column(String, nullable=True)
    command_status = Column(String, default="PENDING")
    verified_state = Column(String, nullable=True)
    verification_timestamp = Column(DateTime, nullable=True)
    safety_validation_id = Column(String, nullable=True)

class O1CalibrationRecordDB(Base):
    __tablename__ = "o1_calibration_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String, nullable=False)
    oat = Column(Float, nullable=False)
    initial_temp = Column(Float, nullable=False)
    target_temp = Column(Float, nullable=False)
    scheduled_start = Column(String, default="06:00")
    optimized_start = Column(String, nullable=False)
    actual_start = Column(String, nullable=False)
    target_reached = Column(String, nullable=False)
    predicted_target_reached = Column(String, nullable=False)
    pulldown_duration_min = Column(Float, nullable=True)
    prediction_error_min = Column(Float, nullable=True)
    scheduled_stop = Column(String, default="18:00")
    optimized_stop = Column(String, nullable=True)
    actual_stop = Column(String, nullable=True)
    comfort_result = Column(String, nullable=True)
    energy_saved_kwh = Column(Float, nullable=True)
    verification = Column(String, default="PREDICTED")
    model_version = Column(String, default="O1-v1.2.0")

class HistoricalThermalResponse(Base):
    __tablename__ = "historical_thermal_response"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String, nullable=True)
    outdoor_temperature = Column(Float, nullable=True)
    initial_zone_temperature = Column(Float, nullable=True)
    target_temperature = Column(Float, nullable=True)
    hvac_start = Column(String, nullable=True)
    target_reached_time = Column(String, nullable=True)
    warmup_duration_minutes = Column(Float, nullable=True)
    overshoot_c = Column(Float, nullable=True)
    comfort_result = Column(String, nullable=True)
    energy_consumed_kwh = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    oat = Column(Float, nullable=True)
    initial_temp = Column(Float, nullable=True)
    target_temp = Column(Float, nullable=True)
    pulldown_time_minutes = Column(Float, nullable=True)
    pulldown_rate = Column(Float, nullable=True)

class O2ActivityLogDB(Base):
    __tablename__ = "o2_activity_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    stage = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    detail = Column(JSON, nullable=True)

class O3ActivityLogDB(Base):
    __tablename__ = "o3_activity_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    stage = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    detail = Column(JSON, nullable=True)

class O4ActivityLogDB(Base):
    __tablename__ = "o4_activity_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    stage = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    detail = Column(JSON, nullable=True)

class O1ActivityLogDB(Base):
    __tablename__ = "o1_activity_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    stage = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    detail = Column(JSON, nullable=True)
    run_id = Column(String, nullable=True)
    event_type = Column(String, nullable=True)
    severity = Column(String, default="INFO")

# ==============================================================================
# PLANT CONTROL PARAMETER OPTIMIZATIONS (O5–O9) FULL DATABASE SCHEMA (16 TABLES)
# ==============================================================================

# 1. Telemetry
class PlantControlTelemetryDB(Base):
    __tablename__ = "plant_control_telemetry"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    opportunity_code = Column(String, nullable=False)
    equipment_id = Column(String, nullable=False)
    point_name = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    quality = Column(String, default="GOOD")
    source = Column(String, default="DETERMINISTIC_SIMULATOR")
    telemetry_json = Column(JSON, nullable=True)

# 2. Zones
class PlantControlZoneDB(Base):
    __tablename__ = "plant_control_zones"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    ahu_id = Column(String, default="AHU-01")
    design_cfm = Column(Float, default=1000.0)
    current_temp = Column(Float, default=22.5)
    setpoint = Column(Float, default=22.0)
    damper_pct = Column(Float, default=65.0)
    is_critical = Column(Boolean, default=False)
    occupancy = Column(Boolean, default=True)

# 3. Equipment Fleet
class PlantControlEquipmentDB(Base):
    __tablename__ = "plant_control_equipment"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    capacity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    status = Column(String, default="ACTIVE")
    health = Column(String, default="EXCELLENT")

# 4. Decisions
class PlantControlDecisionDB(Base):
    __tablename__ = "plant_control_decisions"
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    opportunity_code = Column(String, nullable=False)
    equipment_id = Column(String, nullable=False)
    target_point = Column(String, nullable=False)
    current_value = Column(Float, nullable=False)
    proposed_value = Column(Float, nullable=False)
    decision = Column(String, nullable=False)
    confidence = Column(Float, default=0.95)
    expected_power_shed_kw = Column(Float, default=0.0)
    safety_status = Column(String, default="PASS")
    model_version = Column(String, default="PC-v2.0.0")
    reason = Column(Text, nullable=False)
    details_json = Column(JSON, nullable=True)

# 5. Optimization Runs
class PlantControlOptimizationRunDB(Base):
    __tablename__ = "plant_control_optimization_runs"
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    opportunity_code = Column(String, nullable=False)
    status = Column(String, default="COMPLETED")
    candidates_count = Column(Integer, default=5)
    selected_candidate = Column(String, nullable=False)
    power_shed_kw = Column(Float, default=0.0)
    safety_status = Column(String, default="PASS")
    metrics_json = Column(JSON, nullable=True)

# 6. Safety Checks
class PlantControlSafetyCheckDB(Base):
    __tablename__ = "plant_control_safety_checks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    opportunity_code = Column(String, nullable=False)
    guardrail_name = Column(String, nullable=False)
    outcome = Column(String, default="PASS")
    checked_value = Column(Float, nullable=True)
    limit_min = Column(Float, nullable=True)
    limit_max = Column(Float, nullable=True)
    details = Column(String, nullable=True)

# 7. BMS Commands
class PlantControlBMSCommandDB(Base):
    __tablename__ = "plant_control_bms_commands"
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    opportunity_code = Column(String, nullable=False)
    equipment_id = Column(String, nullable=False)
    point_id = Column(String, nullable=False)
    previous_value = Column(Float, nullable=True)
    requested_value = Column(Float, nullable=False)
    priority = Column(Integer, default=10)
    status = Column(String, default="DISPATCHED")

# 8. Command Lifecycle Events
class PlantControlCommandEventDB(Base):
    __tablename__ = "plant_control_command_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    command_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    event_type = Column(String, nullable=False)
    payload_json = Column(JSON, nullable=True)

# 9. Verification
class PlantControlVerificationDB(Base):
    __tablename__ = "plant_control_verification"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action_id = Column(String, nullable=False)
    opportunity_code = Column(String, nullable=False)
    window_minutes = Column(Integer, default=15)
    expected_metric = Column(String, nullable=False)
    measured_metric = Column(String, nullable=False)
    outcome = Column(String, default="VERIFIED_KEPT")
    requires_rollback = Column(Boolean, default=False)
    details_json = Column(JSON, nullable=True)

# 10. Rollbacks
class PlantControlRollbackDB(Base):
    __tablename__ = "plant_control_rollbacks"
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    opportunity_code = Column(String, nullable=False)
    command_id = Column(String, nullable=True)
    target_point = Column(String, nullable=False)
    reverted_value = Column(Float, nullable=False)
    baseline_value = Column(Float, default=0.0)
    unit = Column(String, default="")
    reason = Column(Text, nullable=False)
    bms_status = Column(String, default="ACKNOWLEDGED")

# 11. Energy Measurements
class PlantControlEnergyMeasurementDB(Base):
    __tablename__ = "plant_control_energy_measurements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    opportunity_code = Column(String, nullable=False)
    baseline_kw = Column(Float, nullable=False)
    optimized_kw = Column(Float, nullable=False)
    shed_kw = Column(Float, nullable=False)
    cumulative_kwh = Column(Float, nullable=False)
    cost_savings_usd = Column(Float, nullable=False)

# 12. Model Versions
class PlantControlModelVersionDB(Base):
    __tablename__ = "plant_control_model_versions"
    id = Column(String, primary_key=True)
    opportunity_code = Column(String, nullable=False)
    version = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    features_json = Column(JSON, nullable=True)
    metrics_json = Column(JSON, nullable=True)
    hyperparameters_json = Column(JSON, nullable=True)
    validation_status = Column(String, default="VALIDATED")
    is_production = Column(Boolean, default=True)

# 13. Training Runs
class PlantControlTrainingRunDB(Base):
    __tablename__ = "plant_control_training_runs"
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    opportunity_code = Column(String, nullable=False)
    dataset_name = Column(String, nullable=False)
    samples_count = Column(Integer, default=2880)
    training_loss_mse = Column(Float, default=0.012)
    validation_r2 = Column(Float, default=0.965)
    training_status = Column(String, default="COMPLETED")

# 14. Calibration Records
class PlantControlCalibrationDB(Base):
    __tablename__ = "plant_control_calibration"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    opportunity_code = Column(String, nullable=False)
    equipment_id = Column(String, nullable=False)
    baseline_power_kw = Column(Float, nullable=False)
    optimized_power_kw = Column(Float, nullable=False)
    measured_savings_kw = Column(Float, nullable=False)
    model_prediction_error_pct = Column(Float, default=1.8)
    calibration_status = Column(String, default="VERIFIED_ONLINE")

# 15. Retrofit Assessments (O9)
class PlantControlRetrofitAssessmentDB(Base):
    __tablename__ = "plant_control_retrofit_assessments"
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    opportunity_code = Column(String, default="O9")
    equipment_id = Column(String, default="CHILLER-01-EVAP")
    current_technology = Column(String, default="Thermostatic Expansion Valve (TXV)")
    proposed_technology = Column(String, default="Electronic Expansion Valve (EXV)")
    superheat_oscillation_deg = Column(Float, default=3.5)
    projected_superheat_stability_deg = Column(Float, default=0.5)
    annual_kwh_savings = Column(Float, default=18400.0)
    annual_cost_savings_usd = Column(Float, default=2208.0)
    estimated_capital_cost_usd = Column(Float, default=4200.0)
    payback_years = Column(Float, default=1.9)
    net_roi_pct = Column(Float, default=52.6)
    technical_feasibility_pct = Column(Float, default=94.0)
    recommendation_status = Column(String, default="RECOMMENDED")
    justification = Column(Text, nullable=False)

# 16. Activity Log
class PlantControlActivityLogDB(Base):
    __tablename__ = "plant_control_activity_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    opportunity_code = Column(String, nullable=False)
    stage = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    detail = Column(JSON, nullable=True)

# Aliases for compatibility
PlantControlActionDB = PlantControlBMSCommandDB
PlantControlModelRegistryDB = PlantControlModelVersionDB

# ==============================================================================
# VENTILATION TELEMETRY TABLES (supporting). Official opportunity numbers are O10–O13.
# ==============================================================================

# 1. Ventilation Opportunities
class VentilationOpportunityDB(Base):
    __tablename__ = "ventilation_opportunities"
    id = Column(String, primary_key=True)  # official O10–O13 when used as catalog rows
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    standard_code = Column(String, default="ASHRAE 62.1-2022")
    status = Column(String, default="ACTIVE")
    mode = Column(String, default="AUTO_CLOSED_LOOP")
    current_value = Column(Float, default=0.0)
    optimized_value = Column(Float, default=0.0)
    unit = Column(String, default="CFM")
    current_airflow_cfm = Column(Float, default=0.0)
    optimized_airflow_cfm = Column(Float, default=0.0)
    fan_power_kw = Column(Float, default=0.0)
    energy_impact_kw = Column(Float, default=0.0)
    daily_kwh_savings = Column(Float, default=0.0)
    comfort_iaq_impact = Column(String, default="OPTIMAL_COMPLIANT")
    confidence = Column(Float, default=0.95)
    updated_at = Column(DateTime, default=datetime.utcnow)

# 2. Ventilation Telemetry
class VentilationTelemetryDB(Base):
    __tablename__ = "ventilation_telemetry"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    building_id = Column(String, default="HQ_MAIN")
    equipment_id = Column(String, nullable=False)
    zone_id = Column(String, nullable=True)
    sensor_id = Column(String, nullable=False)
    sensor_type = Column(String, nullable=False) # "CO2", "AIRFLOW", "STATIC_PRESSURE", "DAMPER_POS", "FAN_SPEED", "FAN_KW"
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    quality = Column(String, default="GOOD")  # GOOD | BAD | UNCERTAIN | STALE | MISSING
    source = Column(String, default="BACnet_IP")
    is_valid = Column(Boolean, default=True)
    opportunity_id = Column(String, nullable=True)

    __table_args__ = (
        Index("ix_vent_tel_eq_ts", "equipment_id", "timestamp"),
        Index("ix_vent_tel_sensor_ts", "sensor_id", "timestamp"),
    )

# 3. Ventilation Zones
class VentilationZoneDB(Base):
    __tablename__ = "ventilation_zones"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    ahu_id = Column(String, nullable=False)
    vav_box_id = Column(String, nullable=False)
    floor_area_sqft = Column(Float, default=1200.0)
    design_occupancy = Column(Integer, default=25)
    current_occupancy = Column(Integer, default=12)
    co2_ppm = Column(Float, default=580.0)
    target_co2_ppm = Column(Float, default=800.0)
    current_airflow_cfm = Column(Float, default=450.0)
    min_airflow_cfm = Column(Float, default=180.0)
    max_airflow_cfm = Column(Float, default=650.0)
    current_temperature_c = Column(Float, default=22.5)
    setpoint_temperature_c = Column(Float, default=23.0)
    damper_position_pct = Column(Float, default=62.0)
    iaq_status = Column(String, default="EXCELLENT")

# 4. Ventilation Equipment
class VentilationEquipmentDB(Base):
    __tablename__ = "ventilation_equipment"
    id = Column(String, primary_key=True) # e.g. "AHU-01", "VAV-101", "EXHAUST-FAN-01"
    name = Column(String, nullable=False)
    equipment_type = Column(String, nullable=False) # "AHU", "VAV", "SUPPLY_FAN", "RETURN_FAN", "RELIEF_DAMPER"
    building_id = Column(String, default="HQ_MAIN")
    rated_cfm = Column(Float, default=10000.0)
    fan_motor_hp = Column(Float, default=15.0)
    vfd_equipped = Column(Boolean, default=True)
    current_vfd_hz = Column(Float, default=48.5)
    current_airflow_cfm = Column(Float, default=7800.0)
    current_static_pressure_inwc = Column(Float, default=1.45)
    current_power_kw = Column(Float, default=8.4)
    operating_status = Column(String, default="RUNNING")

# 5. Airflow Measurements
class AirflowMeasurementDB(Base):
    __tablename__ = "airflow_measurements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    equipment_id = Column(String, nullable=False)
    supply_cfm = Column(Float, nullable=False)
    return_cfm = Column(Float, nullable=False)
    outdoor_air_cfm = Column(Float, nullable=False)
    exhaust_cfm = Column(Float, default=0.0)
    airflow_imbalance_cfm = Column(Float, default=0.0)
    building_differential_pressure_inwc = Column(Float, default=0.03)

# 6. Fan Measurements
class FanMeasurementDB(Base):
    __tablename__ = "fan_measurements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    fan_id = Column(String, nullable=False)
    speed_rpm = Column(Float, default=1450.0)
    vfd_frequency_hz = Column(Float, default=48.5)
    power_kw = Column(Float, nullable=False)
    specific_fan_power_sfp = Column(Float, default=1.12) # kW / (m3/s)
    fan_efficiency_pct = Column(Float, default=78.2)

# 7. Damper Measurements
class DamperMeasurementDB(Base):
    __tablename__ = "damper_measurements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    damper_id = Column(String, nullable=False)
    damper_type = Column(String, nullable=False) # "OUTDOOR_AIR", "RETURN_AIR", "RELIEF_AIR", "VAV_ZONE"
    commanded_position_pct = Column(Float, nullable=False)
    feedback_position_pct = Column(Float, nullable=False)
    damper_status = Column(String, default="OK")

# 8. CO2 Measurements
class CO2MeasurementDB(Base):
    __tablename__ = "co2_measurements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    zone_id = Column(String, nullable=False)
    co2_ppm = Column(Float, nullable=False)
    outdoor_co2_ppm = Column(Float, default=415.0)
    occupant_count = Column(Integer, default=10)
    ashrae_min_vent_rate_cfm = Column(Float, default=210.0)
    ventilation_compliance_pct = Column(Float, default=100.0)

# 9. Outdoor Air Measurements
class OutdoorAirMeasurementDB(Base):
    __tablename__ = "outdoor_air_measurements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    outdoor_drybulb_c = Column(Float, nullable=False)
    outdoor_rh_pct = Column(Float, nullable=False)
    outdoor_enthalpy_kj_kg = Column(Float, nullable=False)
    return_drybulb_c = Column(Float, nullable=False)
    return_rh_pct = Column(Float, nullable=False)
    return_enthalpy_kj_kg = Column(Float, nullable=False)
    mixed_air_temp_c = Column(Float, nullable=False)
    economizer_eligible = Column(Boolean, default=False)
    economizer_mode = Column(String, default="MINIMUM_VENTILATION") # "FREE_COOLING_100", "INTEGRATED_ECONOMIZER", "MINIMUM_VENTILATION"

# 10. Optimization Predictions
class VentilationPredictionDB(Base):
    __tablename__ = "ventilation_predictions"
    id = Column(String, primary_key=True)
    opportunity_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    current_value = Column(Float, nullable=False)
    predicted_value = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    expected_power_saving_kw = Column(Float, default=0.0)
    expected_energy_saving_kwh_day = Column(Float, default=0.0)
    comfort_impact = Column(String, default="within_limit")
    iaq_status = Column(String, default="compliant")
    confidence = Column(Float, default=0.95)
    model_version = Column(String, default="v2.4.1")

# 11. Optimization Recommendations
class VentilationRecommendationDB(Base):
    __tablename__ = "ventilation_recommendations"
    recommendation_id = Column(String, primary_key=True)
    opportunity_id = Column(String, nullable=False)
    agent_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    current_value = Column(Float, nullable=False)
    recommended_value = Column(Float, nullable=False)
    expected_savings_kw = Column(Float, default=0.0)
    expected_savings_kwh_day = Column(Float, default=0.0)
    unit = Column(String, default="CFM")
    confidence = Column(Float, default=0.95)
    reason = Column(Text, nullable=False)
    safety_status = Column(String, default="PASS") # "PASS", "BLOCKED_BY_SAFETY_GUARDRAIL"
    approval_status = Column(String, default="AUTO_APPROVED")
    dispatch_status = Column(String, default="READY")
    model_version = Column(String, default="v2.4.1")

# 12. Optimization Actions
class VentilationActionDB(Base):
    __tablename__ = "ventilation_actions"
    id = Column(String, primary_key=True)
    recommendation_id = Column(String, nullable=True)
    opportunity_id = Column(String, nullable=False)
    equipment_id = Column(String, nullable=False)
    target_point = Column(String, nullable=False)
    dispatched_value = Column(Float, nullable=False)
    previous_value = Column(Float, nullable=False)
    unit = Column(String, default="")
    priority_level = Column(Integer, default=10) # BACnet Priority 10
    dispatched_by = Column(String, default="AUTO_AGENT")
    timestamp = Column(DateTime, default=datetime.utcnow)
    bms_status = Column(String, default="ACKNOWLEDGED")

# 13. Optimization Results
class VentilationResultDB(Base):
    __tablename__ = "ventilation_results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    action_id = Column(String, nullable=False)
    opportunity_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    measured_kw_pre = Column(Float, default=0.0)
    measured_kw_post = Column(Float, default=0.0)
    actual_kw_shed = Column(Float, default=0.0)
    iaq_preserved = Column(Boolean, default=True)
    comfort_preserved = Column(Boolean, default=True)
    verification_outcome = Column(String, default="VERIFIED_KEPT")

# 14. Optimization History
class VentilationHistoryDB(Base):
    __tablename__ = "ventilation_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    opportunity_id = Column(String, nullable=False)
    metric_name = Column(String, nullable=False)
    baseline_value = Column(Float, nullable=False)
    optimized_value = Column(Float, nullable=False)
    power_savings_kw = Column(Float, default=0.0)
    iaq_metric = Column(Float, default=0.0)

# 15. Safety Guardrails
class VentilationSafetyGuardrailDB(Base):
    __tablename__ = "ventilation_safety_guardrails"
    id = Column(String, primary_key=True)
    rule_name = Column(String, nullable=False)
    parameter = Column(String, nullable=False)
    min_allowed = Column(Float, nullable=False)
    max_allowed = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)

# 16. Model Versions
class VentilationModelVersionDB(Base):
    __tablename__ = "ventilation_model_versions"
    id = Column(String, primary_key=True)
    opportunity_id = Column(String, nullable=False)
    version = Column(String, nullable=False)
    algorithm = Column(String, nullable=False)
    trained_timestamp = Column(DateTime, default=datetime.utcnow)
    r2_score = Column(Float, default=0.96)
    mae = Column(Float, default=0.04)
    validation_status = Column(String, default="PASSED")
    is_production = Column(Boolean, default=True)

# 17. Agent Runs
class VentilationAgentRunDB(Base):
    __tablename__ = "ventilation_agent_runs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_timestamp = Column(DateTime, default=datetime.utcnow)
    cycle_mode = Column(String, default="AUTO_CLOSED_LOOP")
    opportunities_evaluated = Column(Integer, default=5)
    total_power_shed_kw = Column(Float, default=0.0)
    total_daily_kwh_savings = Column(Float, default=0.0)
    safety_compliance_pct = Column(Float, default=100.0)
    details_json = Column(JSON, nullable=True)

# 18. Audit Logs
class VentilationAuditLogDB(Base):
    __tablename__ = "ventilation_audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    opportunity_id = Column(String, nullable=False)
    actor = Column(String, default="VENTILATION_AGENT")
    event_type = Column(String, nullable=False) # "TELEMETRY_INGEST", "CANDIDATE_OPTIMIZE", "SAFETY_CHECK", "BMS_DISPATCH", "MV_VERIFICATION", "ROLLBACK"
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)


# ==============================================================================
# VARIABLE SPEED BASED OPTIMIZATIONS TABLES (VFD FANS, PUMPS, TOWERS)
# ==============================================================================
from database.models_o14 import O14ConfigDB, O14SystemSnapshotDB, O14RecommendationDB  # noqa: F401
from database.models_o15 import O15ConfigDB, O15SystemSnapshotDB, O15RecommendationDB  # noqa: F401
from database.models_o16 import (  # noqa: F401
    O16ConfigDB,
    O16TelemetryDB,
    O16StateDB,
    O16RecommendationDB,
    O16VerificationDB,
    O16SavingsDB,
)

from database.models_vs import (
    VariableSpeedEquipmentDB,
    VariableSpeedTelemetryDB,
    VFDFanMeasurementDB,
    VFDPumpMeasurementDB,
    VfdMeasurementDB,
    VariableSpeedPredictionDB,
    VariableSpeedRecommendationDB,
    VariableSpeedActionDB,
    VariableSpeedResultDB,
    VariableSpeedSafetyConstraintDB,
    VariableSpeedModelVersionDB,
    VariableSpeedEnergySavingsDB,
    VariableSpeedAuditLogDB
)

# ==============================================================================
# ENERGY & OPERATIONS INTELLIGENCE TABLES (HVAC OPERATION & MAINTENANCE)
# ==============================================================================
from database.models_energy_ops import (
    EnergyTelemetryDB,
    EnergyBaselineDB,
    EnergyConsumptionDB,
    EnergySavingsMVDB,
    HVACAnomalyDB,
    AgentCoordinationDB,
    AgentConflictDB,
    EnergyRecommendationDB,
    HVACForecastDB,
    EquipmentPerformanceDB
)

from database.models_o1 import (
    O1PointMapDB,
    O1ConfigurationDB,
    O1TelemetrySampleDB,
    WeatherObservationDB,
    OccupancyScheduleDB,
    O1ModelDB,
    O1ModelTrainingRunDB,
    O1PredictionDB,
    O1DailyRunDB,
    O1StartCandidateDB,
    O1StopCandidateDB,
    O1SafetyValidationDB,
    O1ComfortValidationDB,
    O1EnergyBaselineDB,
    O1SavingsVerificationDB,
)

from database.models_opportunities import HvacOpportunityDB  # noqa: E402,F401

from database.models_ventilation import (  # noqa: E402,F401
    HvacTelemetryDB,
    HvacOptimizationResultDB,
    HvacOptimizationCandidateDB,
)

from database.models_om import (  # noqa: E402,F401
    OmOpportunityDB,
    OmTelemetryDB,
    OmRecommendationDB,
    OmSupervisoryDecisionDB,
    OmMaintenanceFindingDB,
    OmTrainingActionDB,
    OmSoftwareHealthDB,
    OmDispatchDB,
    OmVerificationDB,
    OmRollbackDB,
    OmAuditEventDB,
    OmAgentRunDB,
)

from database.models_platform import (  # noqa: E402,F401
    HvacUserDB,
    ControlAuditLogDB,
    CanonicalTelemetryDB,
    HvacApprovalDB,
    PlatformSettingDB,
    TenantDB,
    ZoneDB,
    ControlCommandDB,
    AgentRunDB,
)

from database.models_bms import (  # noqa: E402,F401
    BmsConnectionDB,
    BmsDeviceDB,
    BmsPointDB,
    EquipmentPointMappingDB,
)

from database.models_ml import (  # noqa: E402,F401
    MLDatasetRegistryDB,
    MLDatasetFileDB,
    MLDatasetQualityDB,
    MLDatasetOpportunityMapDB,
    MLFeatureDefinitionDB,
    MLTrainingRunDB,
    MLModelRegistryDB,
    MLModelMetricsDB,
    MLPredictionDB,
    MLPredictionFeatureDB,
    MLAgentPredictionDB,
)


