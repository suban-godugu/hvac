"""
Database Models for Energy & Operations Intelligence Agent (HVAC Operation & Maintenance).
Stores energy telemetry, weather-normalized baselines, consumption breakdown, IPMVP M&V,
anomalies with root-cause explanations, cross-agent coordination/conflicts, and forecasts.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Text, ForeignKey, Index
from database.base import Base

# 1. Building & Submeter Energy Telemetry
class EnergyTelemetryDB(Base):
    __tablename__ = "energy_telemetry"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    building_id = Column(String, default="BLD-01")
    meter_id = Column(String, nullable=False) # e.g. "MAIN-ELEC-METER", "CHILLER-PLANT-METER", "AHU-SUBMETER"
    category = Column(String, nullable=False) # "TOTAL_HVAC", "CHILLERS", "FANS", "PUMPS", "COOLING_TOWERS", "HEATING", "LIGHTING_BASE"
    power_kw = Column(Float, nullable=False)
    voltage_v = Column(Float, default=480.0)
    current_a = Column(Float, default=520.0)
    power_factor = Column(Float, default=0.94)
    quality = Column(String, default="GOOD")  # GOOD | BAD | UNCERTAIN | STALE | MISSING
    source = Column(String, default="BACnet_IP_PowerMeter")
    is_submetered = Column(Boolean, default=True)

    __table_args__ = (Index("ix_energy_tel_meter_ts", "meter_id", "timestamp"),)

# 2. Weather-Normalized Energy Baseline Engine Models
class EnergyBaselineDB(Base):
    __tablename__ = "energy_baselines"
    id = Column(String, primary_key=True) # e.g. "BASELINE-2026-08-18-H14"
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    building_id = Column(String, default="BLD-01")
    outdoor_temp_c = Column(Float, nullable=False)
    outdoor_rh_pct = Column(Float, default=55.0)
    wet_bulb_c = Column(Float, default=21.0)
    occupancy_mode = Column(String, default="OCCUPIED")
    cooling_load_tons = Column(Float, nullable=False)
    heating_load_kw = Column(Float, default=0.0)
    baseline_hvac_power_kw = Column(Float, nullable=False) # What HVAC would consume without AI
    actual_hvac_power_kw = Column(Float, nullable=False)
    optimized_hvac_power_kw = Column(Float, nullable=False)
    regression_model_version = Column(String, default="v3.1-weather-load-normalized")

# 3. Real-Time & Historical Energy Consumption
class EnergyConsumptionDB(Base):
    __tablename__ = "energy_consumption"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    interval_minutes = Column(Integer, default=15)
    total_building_kwh = Column(Float, nullable=False)
    total_hvac_kwh = Column(Float, nullable=False)
    chiller_kwh = Column(Float, nullable=False)
    fan_kwh = Column(Float, nullable=False)
    pump_kwh = Column(Float, nullable=False)
    tower_kwh = Column(Float, nullable=False)
    heating_kwh = Column(Float, default=0.0)
    tou_tariff_rate_usd_kwh = Column(Float, default=0.14) # Time-of-use rate
    cost_usd = Column(Float, nullable=False)
    carbon_avoided_kg_co2 = Column(Float, default=0.0)

# 4. Measurement & Verification (IPMVP Option B / Option C)
class EnergySavingsMVDB(Base):
    __tablename__ = "energy_savings_mv"
    id = Column(String, primary_key=True) # e.g. "MV-ACT-2026-08-18-001"
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    source_agent = Column(String, nullable=False) # "SCHEDULING", "PLANT_CONTROL", "VENTILATION", "VARIABLE_SPEED"
    action_id = Column(String, nullable=False)
    equipment_id = Column(String, nullable=False)
    baseline_kw = Column(Float, nullable=False)
    baseline_kwh = Column(Float, nullable=False)
    actual_kw = Column(Float, nullable=False)
    actual_kwh = Column(Float, nullable=False)
    predicted_savings_kw = Column(Float, nullable=False)
    predicted_savings_kwh = Column(Float, nullable=False)
    measured_savings_kw = Column(Float, nullable=False)
    measured_savings_kwh = Column(Float, nullable=False)
    verified_savings_kw = Column(Float, nullable=False)
    verified_savings_kwh = Column(Float, nullable=False)
    verification_confidence = Column(Float, default=0.96)
    verification_status = Column(String, default="VERIFIED") # "PENDING", "MEASURED", "VERIFIED", "REJECTED", "INCONCLUSIVE"
    mv_method = Column(String, default="IPMVP_Option_B_ECM_Isolation")
    notes = Column(Text, nullable=True)

# 5. HVAC Anomaly Detection & Automated Root-Cause Analysis
class HVACAnomalyDB(Base):
    __tablename__ = "hvac_anomalies"
    id = Column(String, primary_key=True) # e.g. "ANOM-2026-08-18-01"
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    anomaly_type = Column(String, nullable=False) # "UNEXPECTED_ENERGY_SURGE", "SIMULTANEOUS_HEAT_COOL", "LOW_DELTA_T", "EXCESSIVE_STATIC_PRESSURE", "NIGHTTIME_WASTE", "CHILLER_DEGRADATION"
    severity = Column(String, default="HIGH") # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    equipment_id = Column(String, nullable=False)
    equipment_name = Column(String, nullable=False)
    detected_value = Column(Float, nullable=False)
    expected_value = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    excess_power_kw = Column(Float, default=0.0)
    root_cause_explanation = Column(Text, nullable=False)
    recommended_action = Column(Text, nullable=False)
    status = Column(String, default="ACTIVE") # "ACTIVE", "ACKNOWLEDGED", "RESOLVED"
    acknowledged_by = Column(String, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)

# 6. Cross-Agent Coordination & Conflict Detection
class AgentCoordinationDB(Base):
    __tablename__ = "agent_coordination_events"
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    agent_name = Column(String, nullable=False)
    opportunity_code = Column(String, nullable=False)
    equipment_id = Column(String, nullable=False)
    target_point = Column(String, nullable=False)
    recommended_value = Column(Float, nullable=False)
    expected_savings_kw = Column(Float, nullable=False)
    confidence = Column(Float, default=0.95)
    safety_status = Column(String, default="PASS")
    conflict_detected = Column(Boolean, default=False)
    conflict_details = Column(JSON, nullable=True)
    arbitration_result = Column(String, default="APPROVED")

# 7. Agent Conflicts
class AgentConflictDB(Base):
    __tablename__ = "agent_conflicts"
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    agent_a = Column(String, nullable=False)
    action_a = Column(String, nullable=False)
    agent_b = Column(String, nullable=False)
    action_b = Column(String, nullable=False)
    conflict_type = Column(String, nullable=False) # "COMPETING_SETPOINT", "ZONE_STARVATION_FIGHT", "SIMULTANEOUS_HEAT_COOL"
    severity = Column(String, default="HIGH")
    resolution_strategy = Column(String, nullable=False)
    resolved_action = Column(String, nullable=False)
    resolved_at = Column(DateTime, default=datetime.utcnow)

# 8. Ranked Priority Recommendations
class EnergyRecommendationDB(Base):
    __tablename__ = "energy_ranked_recommendations"
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    title = Column(String, nullable=False)
    category = Column(String, nullable=False) # "ENERGY_OPTIMIZATION", "WASTE_ELIMINATION", "PEAK_AVOIDANCE", "MAINTENANCE"
    source_agent = Column(String, nullable=False)
    equipment_id = Column(String, nullable=False)
    recommended_action = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    expected_savings_kw = Column(Float, nullable=False)
    expected_savings_kwh_day = Column(Float, nullable=False)
    cost_savings_usd_month = Column(Float, default=0.0)
    priority_score = Column(Float, nullable=False) # Calculated multi-attribute score
    confidence = Column(Float, default=0.96)
    risk_level = Column(String, default="LOW")
    comfort_impact = Column(String, default="NONE")
    status = Column(String, default="ACTIVE") # "ACTIVE", "APPROVED", "REJECTED", "EXECUTED"
    reviewed_by = Column(String, nullable=True)

# 9. Load & Peak Demand Forecasts
class HVACForecastDB(Base):
    __tablename__ = "hvac_forecasts"
    id = Column(String, primary_key=True)
    forecast_horizon = Column(String, nullable=False) # "15_MIN", "1_HOUR", "4_HOUR", "24_HOUR", "7_DAY"
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    forecast_timestamp = Column(DateTime, nullable=False)
    predicted_hvac_kw = Column(Float, nullable=False)
    predicted_building_kw = Column(Float, nullable=False)
    confidence_lower_kw = Column(Float, nullable=False)
    confidence_upper_kw = Column(Float, nullable=False)
    expected_peak_time = Column(String, nullable=True)
    peak_avoidance_opportunity_kw = Column(Float, default=0.0)

# 10. Equipment Performance & Efficiency Tracking
class EquipmentPerformanceDB(Base):
    __tablename__ = "equipment_performance_tracking"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    equipment_id = Column(String, nullable=False)
    equipment_type = Column(String, nullable=False) # "CHILLER", "BOILER", "AHU_FAN", "PUMP", "COOLING_TOWER"
    current_efficiency = Column(Float, nullable=False) # kW/ton, COP, SFP, wire-to-water %
    target_efficiency = Column(Float, nullable=False)
    baseline_efficiency = Column(Float, nullable=False)
    optimized_efficiency = Column(Float, nullable=False)
    efficiency_unit = Column(String, nullable=False) # "kW/ton", "COP", "kW/(m3/s)", "%"
    runtime_hours_today = Column(Float, default=12.5)
    cycling_count_today = Column(Integer, default=2)
    load_factor_pct = Column(Float, default=68.5)
    health_status = Column(String, default="OPTIMAL") # "OPTIMAL", "ACCEPTABLE", "DEGRADED", "CRITICAL"
