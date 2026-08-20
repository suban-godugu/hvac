export interface O16ClassifiedTelemetry {
  status?: string | null;
  quality?: string | null;
  source?: string | null;
  age_seconds?: number | null;
  usable?: boolean;
  demo?: boolean;
}

export interface O16CurrentState {
  cewt_c?: number | null;
  clwt_c?: number | null;
  cw_delta_t_c?: number | null;
  cw_flow?: number | null;
  condensing_temperature_c?: number | null;
  head_pressure?: number | null;
  head_pressure_setpoint?: number | null;
  pump_speed_pct?: number | null;
  pump_status?: string | null;
  pump_power_kw?: number | null;
  valve_position_pct?: number | null;
  load_pct?: number | null;
  load_ratio?: number | null;
  compressor_status?: string | null;
  cooling_call?: number | null;
  approach_c?: number | null;
  head_pressure_margin?: number | null;
  outdoor_temperature_c?: number | null;
  outdoor_wet_bulb_c?: number | null;
  active_condensers?: number | null;
  alarm?: number | null;
  current_setpoint_c?: number | null;
}

export interface O16OptimizedState {
  recommended_head_pressure?: number | null;
  recommended_condensing_temp_c?: number | null;
  recommended_pump_speed_pct?: number | null;
  recommended_valve_position_pct?: number | null;
  recommended_cw_flow?: number | null;
  control_strategy?: string | null;
  shared_pump?: boolean | null;
  command_point?: string | null;
}

export interface O16SafetyCheck {
  check_name: string;
  result: string;
  reason?: string | null;
  actual_value?: number | null;
  minimum?: number | null;
  maximum?: number | null;
}

export interface O16Safety {
  overall?: string | null;
  status?: string | null;
  safety_status?: string | null;
  gates?: O16SafetyCheck[];
  checks?: O16SafetyCheck[];
  safe_mode?: boolean;
  bms_connected?: boolean;
}

export interface O16Why {
  outdoor_condition?: string;
  current_load?: string;
  current_head_pressure?: string;
  cw_temps?: string;
  current_pump?: string;
  current_valve?: string;
  estimated_pump_power?: number | null;
  estimated_optimized_pump_power?: number | null;
  control_relationship?: string;
  active_engineering_limits?: Record<string, unknown>;
  recommended_target?: string;
  reason_for_change?: string;
  safety_gates?: string[];
}

export interface O16RecommendationPayload {
  target_condensing_pressure?: number | null;
  target_condensing_temperature?: number | null;
  recommended_pump_speed?: number | null;
  recommended_valve_position?: number | null;
  reason?: string | null;
  confidence?: number | null;
}

export interface O16Command {
  id?: string;
  command_id: string;
  opportunity?: string;
  equipment_id?: string | null;
  point_id?: string | null;
  old_value?: number | null;
  new_value?: number | null;
  reason?: string | null;
  status?: string | null;
  created_at?: string | null;
  applied_at?: string | null;
  verified_at?: string | null;
  rollback_at?: string | null;
}

export interface O16HistoryPoint {
  timestamp?: string | null;
  head_pressure?: number | null;
  condensing_temperature?: number | null;
  cw_supply?: number | null;
  cw_return?: number | null;
  cw_flow?: number | null;
  pump_speed?: number | null;
  pump_power?: number | null;
  load?: number | null;
  quality?: string | null;
  source?: string | null;
}

export interface O16HistoryResponse {
  period_hours?: number;
  points?: O16HistoryPoint[];
  fabricated?: boolean;
}

export interface O16EquipmentRow {
  equipment_id?: string | null;
  name?: string | null;
  type?: string | null;
  status?: unknown;
  current_value?: number | null;
  target?: number | null;
  alarms?: unknown;
  data_quality?: string | null;
  source?: string | null;
  last_seen?: string | null;
}

export interface O16TelemetryPoint {
  point_id?: string | null;
  value?: number | string | null;
  unit?: string | null;
  quality?: string | null;
  source?: string | null;
  timestamp?: string | null;
  age_seconds?: number | null;
  classified?: string | null;
  equipment_id?: string | null;
}

export interface O16TelemetryResponse {
  opportunity?: string;
  points?: O16TelemetryPoint[];
  sampled?: Record<string, unknown>;
  source?: string | null;
  quality?: string | null;
}

export interface O16Header {
  opportunity?: string;
  title?: string;
  subtitle?: string;
  bms?: string | null;
  telemetry?: string | null;
  control_mode?: string | null;
  optimization?: string | null;
  safety?: string | null;
  last_telemetry?: string | null;
  last_optimization?: string | null;
  last_command?: string | null;
  last_verification?: string | null;
  safe_mode?: boolean;
  ui_state?: string | null;
  equipment?: Array<string | null>;
}

export interface O16Config {
  building_id?: string | null;
  enabled?: boolean | null;
  control_mode?: string | null;
  control_strategy?: string | null;
  target_head_pressure?: number | null;
  target_condensing_temp_c?: number | null;
  min_head_pressure?: number | null;
  max_head_pressure?: number | null;
  min_condensing_temp_c?: number | null;
  max_condensing_temp_c?: number | null;
  min_pump_speed_pct?: number | null;
  max_pump_speed_pct?: number | null;
  min_cw_flow?: number | null;
  max_cw_flow?: number | null;
  max_pump_step_pct?: number | null;
  config_version?: string | null;
}

export interface O16Dashboard {
  opportunity?: string;
  opportunity_id?: string;
  live?: boolean;
  agent_status?: string | null;
  status?: string | null;
  ui_state?: string | null;
  recommendation?: string | O16RecommendationPayload | null;
  recommendation_state?: string | null;
  reason?: string | null;
  confidence?: number | null;
  safety_status?: string | null;
  overall_safety?: string | null;
  engine_version?: string | null;
  evaluated_at?: string | null;
  energy_impact?: number | null;
  energy_impact_class?: string | null;
  predicted_pump_power_kw?: number | null;
  predicted_power_delta_kw?: number | null;
  verified_savings_kw?: number | null;
  applied_savings_kw?: number | null;
  guide_potential_note?: string | null;
  safe_mode?: boolean;
  bms_connected?: boolean;
  current_state?: O16CurrentState;
  optimized_state?: O16OptimizedState;
  classified_telemetry?: O16ClassifiedTelemetry;
  why?: O16Why;
  safety?: O16Safety;
  safety_checks?: O16SafetyCheck[];
  header?: O16Header;
  config?: O16Config;
  config_labels?: Record<string, string>;
  equipment?: O16EquipmentRow[];
  commands?: O16Command[];
  command?: O16Command;
  savings?: {
    predicted_kw?: number | null;
    predicted_kwh?: number | null;
    predicted?: number | null;
    applied?: number | null;
    verified?: number | null;
    guide_potential_note?: string | null;
  };
  current?: {
    condensing_pressure?: number | null;
    condensing_temperature?: number | null;
    cw_supply_temperature?: number | null;
    cw_return_temperature?: number | null;
    cw_flow?: number | null;
    pump_speed?: number | null;
    pump_power?: number | null;
  };
}
