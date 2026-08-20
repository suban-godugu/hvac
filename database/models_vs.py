from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Text, Index
from database.base import Base

# ==============================================================================
# VARIABLE SPEED BASED OPTIMIZATIONS TABLES (VFD FANS, PUMPS, TOWERS)
# ==============================================================================

# 1. Variable Speed Equipment Registry
class VariableSpeedEquipmentDB(Base):
    __tablename__ = "variable_speed_equipment"
    id = Column(String, primary_key=True) # e.g. "AHU-FAN-01", "CHW-PUMP-01", "CT-FAN-01"
    equipment_type = Column(String, nullable=False) # "AHU_FAN", "SUPPLY_FAN", "RETURN_FAN", "CHW_PUMP", "HHW_PUMP", "CW_PUMP", "COOLING_TOWER_FAN"
    building_id = Column(String, default="BLD-01")
    name = Column(String, nullable=False)
    manufacturer = Column(String, default="Schneider / ABB")
    rated_power_kw = Column(Float, nullable=False) # e.g. 18.4 kW, 22.0 kW, 30.0 kW
    rated_speed_rpm = Column(Float, default=1750.0)
    minimum_speed_pct = Column(Float, default=30.0) # VFD minimum safe speed clamp
    maximum_speed_pct = Column(Float, default=100.0)
    minimum_frequency_hz = Column(Float, default=20.0) # Motor cooling limit
    maximum_frequency_hz = Column(Float, default=60.0)
    design_flow = Column(Float, nullable=False) # CFM for fans, GPM for pumps
    flow_unit = Column(String, default="GPM") # "CFM" or "GPM"
    design_pressure = Column(Float, nullable=False) # in.w.c. for fans, PSI / ft head for pumps
    pressure_unit = Column(String, default="PSI") # "in.w.c.", "PSI", "ft_hd"
    efficiency = Column(Float, default=0.92)
    vfd_enabled = Column(Boolean, default=True)
    control_mode = Column(String, default="AUTO_CLOSED_LOOP") # "ADVISORY", "AUTO", "AUTO_CLOSED_LOOP", "MANUAL"
    status = Column(String, default="RUNNING") # "RUNNING", "STANDBY", "OPTIMAL", "FAULT"

# 2. Variable Speed Telemetry
class VariableSpeedTelemetryDB(Base):
    __tablename__ = "variable_speed_telemetry"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    building_id = Column(String, default="BLD-01")
    equipment_id = Column(String, nullable=False)
    point_id = Column(String, nullable=False)
    point_name = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    quality = Column(String, default="GOOD")  # GOOD | BAD | UNCERTAIN | STALE | MISSING
    source = Column(String, default="BACnet_IP")
    received_at = Column(DateTime, default=datetime.utcnow)
    opportunity_id = Column(String, nullable=True)

    __table_args__ = (
        Index("ix_vs_tel_eq_ts", "equipment_id", "timestamp"),
        Index("ix_vs_tel_point_ts", "point_id", "timestamp"),
    )

# 3. VFD Fan Measurements
class VFDFanMeasurementDB(Base):
    __tablename__ = "vfd_fan_measurements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    equipment_id = Column(String, nullable=False)
    fan_speed_pct = Column(Float, nullable=False)
    fan_frequency_hz = Column(Float, nullable=False)
    fan_power_kw = Column(Float, nullable=False)
    fan_airflow_cfm = Column(Float, nullable=False)
    duct_static_pressure_inwc = Column(Float, nullable=False)
    static_pressure_setpoint_inwc = Column(Float, default=1.20)
    vav_airflow_demand_cfm = Column(Float, default=6500.0)
    avg_vav_damper_pct = Column(Float, default=65.0)
    max_vav_damper_pct = Column(Float, default=82.0)
    critical_zones_count = Column(Integer, default=1)
    specific_fan_power = Column(Float, default=1.65) # kW/(m3/s)

# 4. VFD Pump Measurements
class VFDPumpMeasurementDB(Base):
    __tablename__ = "vfd_pump_measurements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    equipment_id = Column(String, nullable=False)
    pump_type = Column(String, nullable=False) # "CHW_PUMP", "HHW_PUMP", "CW_PUMP", "SECONDARY_PUMP"
    pump_speed_pct = Column(Float, nullable=False)
    pump_frequency_hz = Column(Float, nullable=False)
    pump_power_kw = Column(Float, nullable=False)
    flow_gpm = Column(Float, nullable=False)
    differential_pressure_psi = Column(Float, nullable=False)
    dp_setpoint_psi = Column(Float, default=14.0)
    supply_temp_c = Column(Float, default=6.7)
    return_temp_c = Column(Float, default=12.2)
    delta_t_c = Column(Float, default=5.5)
    chiller_load_pct = Column(Float, default=68.0)
    valve_positions_avg_pct = Column(Float, default=72.0)

# 5. VFD Inverter Measurements
class VfdMeasurementDB(Base):
    __tablename__ = "vfd_measurements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    equipment_id = Column(String, nullable=False)
    frequency_hz = Column(Float, nullable=False)
    output_voltage_v = Column(Float, default=460.0)
    output_current_a = Column(Float, default=26.5)
    motor_rpm = Column(Float, default=1450.0)
    dc_bus_voltage_v = Column(Float, default=650.0)
    inverter_temp_c = Column(Float, default=42.5)
    vfd_fault_code = Column(String, default="NORMAL_00")
    power_factor = Column(Float, default=0.94)

# 6. Optimization Predictions (ML Output)
class VariableSpeedPredictionDB(Base):
    __tablename__ = "variable_speed_predictions"
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    equipment_id = Column(String, nullable=False)
    agent_id = Column(String, nullable=False)
    model_version = Column(String, default="v2.5.0-xgb-affinity")
    current_speed = Column(Float, nullable=False)
    recommended_speed = Column(Float, nullable=False)
    current_power_kw = Column(Float, nullable=False)
    predicted_power_kw = Column(Float, nullable=False)
    power_savings_kw = Column(Float, default=0.0)
    predicted_flow = Column(Float, nullable=False)
    predicted_pressure = Column(Float, nullable=False)
    confidence = Column(Float, default=0.96)
    safety_status = Column(String, default="PASS")
    status = Column(String, default="OPTIMAL")
    reason = Column(Text, nullable=False)

# 7. Optimization Recommendations
class VariableSpeedRecommendationDB(Base):
    __tablename__ = "variable_speed_recommendations"
    recommendation_id = Column(String, primary_key=True)
    opportunity_id = Column(String, nullable=False) # "VS-FAN", "VS-PUMP", "VS-CHW", "VS-CW", "VS-CT"
    equipment_id = Column(String, nullable=False)
    current_speed = Column(Float, nullable=False)
    recommended_speed = Column(Float, nullable=False)
    current_power_kw = Column(Float, nullable=False)
    predicted_power_kw = Column(Float, nullable=False)
    expected_savings_kw = Column(Float, default=0.0)
    expected_savings_kwh_day = Column(Float, default=0.0)
    confidence = Column(Float, default=0.96)
    reason = Column(Text, nullable=False)
    safety_status = Column(String, default="PASS")
    dispatch_status = Column(String, default="READY")
    timestamp = Column(DateTime, default=datetime.utcnow)

# 8. Optimization Actions (BMS Dispatches)
class VariableSpeedActionDB(Base):
    __tablename__ = "variable_speed_actions"
    id = Column(String, primary_key=True)
    recommendation_id = Column(String, nullable=True)
    equipment_id = Column(String, nullable=False)
    opportunity_id = Column(String, nullable=False)
    target_point = Column(String, nullable=False) # e.g. "AHU-FAN-01.SpeedSetpoint"
    dispatched_value = Column(Float, nullable=False)
    previous_value = Column(Float, nullable=False)
    unit = Column(String, default="%")
    priority_level = Column(Integer, default=10)
    dispatched_by = Column(String, default="VARIABLE_SPEED_AI")
    timestamp = Column(DateTime, default=datetime.utcnow)
    bms_status = Column(String, default="ACKNOWLEDGED")

# 9. Optimization Results (15-min M&V)
class VariableSpeedResultDB(Base):
    __tablename__ = "variable_speed_results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    action_id = Column(String, nullable=False)
    equipment_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    baseline_power_kw = Column(Float, default=0.0)
    optimized_power_kw = Column(Float, default=0.0)
    measured_power_savings_kw = Column(Float, default=0.0)
    verified_energy_savings_kwh = Column(Float, default=0.0)
    airflow_comfort_preserved = Column(Boolean, default=True)
    pressure_preserved = Column(Boolean, default=True)
    verification_outcome = Column(String, default="VERIFIED_KEPT") # "VERIFIED_KEPT", "ROLLED_BACK"

# 10. Safety Constraints & Guardrails
class VariableSpeedSafetyConstraintDB(Base):
    __tablename__ = "variable_speed_safety_constraints"
    id = Column(String, primary_key=True)
    equipment_id = Column(String, nullable=False)
    rule_name = Column(String, nullable=False)
    min_speed_pct = Column(Float, nullable=False)
    max_speed_pct = Column(Float, nullable=False)
    min_flow = Column(Float, nullable=False)
    max_flow = Column(Float, nullable=False)
    min_pressure = Column(Float, nullable=False)
    max_pressure = Column(Float, nullable=False)
    min_frequency_hz = Column(Float, default=20.0)
    max_frequency_hz = Column(Float, default=60.0)
    ramp_rate_limit_pct_per_min = Column(Float, default=10.0)
    is_active = Column(Boolean, default=True)

# 11. Model Versions
class VariableSpeedModelVersionDB(Base):
    __tablename__ = "variable_speed_model_versions"
    id = Column(String, primary_key=True)
    agent_id = Column(String, nullable=False)
    version = Column(String, nullable=False)
    algorithm = Column(String, default="XGBoost_Affinity_Hybrid")
    trained_timestamp = Column(DateTime, default=datetime.utcnow)
    mae_power_kw = Column(Float, default=0.28)
    rmse_power_kw = Column(Float, default=0.45)
    r2_score = Column(Float, default=0.975)
    status = Column(String, default="PRODUCTION") # "PRODUCTION", "STAGING", "MODEL_DEGRADED"

# 12. Energy Savings Measurement
class VariableSpeedEnergySavingsDB(Base):
    __tablename__ = "variable_speed_energy_savings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    equipment_id = Column(String, nullable=False)
    category = Column(String, nullable=False) # "FAN", "PUMP", "CHW", "CW", "TOWER"
    predicted_savings_kw = Column(Float, default=0.0)
    measured_savings_kw = Column(Float, default=0.0)
    verified_savings_kwh = Column(Float, default=0.0)
    calculation_method = Column(String, default="IPMVP_Option_B")

# 13. Audit Logs
class VariableSpeedAuditLogDB(Base):
    __tablename__ = "variable_speed_audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    agent = Column(String, nullable=False)
    equipment_id = Column(String, nullable=False)
    current_value = Column(Float, nullable=False)
    recommended_value = Column(Float, nullable=False)
    final_value = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    model_version = Column(String, default="v2.5.0")
    confidence = Column(Float, default=0.96)
    safety_result = Column(String, default="PASS")
    operator_mode = Column(String, default="AUTO_CLOSED_LOOP")
    dispatch_result = Column(String, default="SUCCESS")
    verification_result = Column(String, default="VERIFIED_KEPT")
    rollback_result = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
