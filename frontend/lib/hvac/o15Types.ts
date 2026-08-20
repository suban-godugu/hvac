export type O15Quality = string | null | undefined;

export interface O15ClassifiedTelemetry {
  status?: string | null;
  quality?: string | null;
  source?: string | null;
  age_seconds?: number | null;
  usable?: boolean;
  demo?: boolean;
}

export interface O15CurrentState {
  outdoor_temperature_c?: number | null;
  outdoor_humidity_pct?: number | null;
  condenser_temperature_c?: number | null;
  head_pressure?: number | null;
  head_pressure_setpoint?: number | null;
  fan_speed_pct?: number | null;
  fan_status?: string | null;
  fan_power_kw?: number | null;
  fans_running?: number | null;
  compressor_status?: string | null;
  compressor_power_kw?: number | null;
  load?: number | null;
  power_kw?: number | null;
  observed_approach_c?: number | null;
  alarm?: number | null;
  current_setpoint_psig?: number | null;
}

export interface O15OptimizedState {
  recommended_condensing_temp_c?: number | null;
  recommended_head_pressure?: number | null;
  recommended_fan_speed_pct?: number | null;
  approach_c?: number | null;
  approach_source?: string | null;
  fan_trim_pct?: number | null;
  saturation_curve_source?: string | null;
}

export interface O15SafetyCheck {
  check_name: string;
  result: string;
  reason?: string | null;
}

export interface O15Safety {
  overall?: string | null;
  safety_status?: string | null;
  checks?: O15SafetyCheck[];
  gates?: O15SafetyCheck[];
  safe_mode?: boolean;
  bms_connected?: boolean;
}

export interface O15Why {
  outdoor_condition?: string;
  current_head_pressure?: string;
  current_fan_operation?: string;
  system_demand?: string;
  control_relationship?: string;
  active_engineering_limits?: Record<string, unknown>;
  recommended_target?: string;
  reason_for_change?: string;
  safety_gates?: string[];
}

export interface O15Command {
  id?: string;
  command_id: string;
  opportunity?: string;
  equipment_id?: string | null;
  point_id?: string | null;
  old_value?: number | null;
  new_value?: number | null;
  reason?: string | null;
  status?: string | null;
  engine_version?: string | null;
  config_version?: string | null;
  safety_gates?: unknown;
  created_at?: string | null;
  applied_at?: string | null;
  verified_at?: string | null;
  rollback_at?: string | null;
}

export interface O15HistoryResponse {
  period_hours?: number;
  points?: O15HistoryPoint[];
  fabricated?: boolean;
}

export interface O15HistoryPoint {
  timestamp?: string | null;
  head_pressure?: number | null;
  head_pressure_setpoint?: number | null;
  condensing_temperature?: number | null;
  outdoor_air_temperature?: number | null;
  fan_speed?: number | null;
  fan_power?: number | null;
  compressor_power?: number | null;
  load?: number | null;
  quality?: string | null;
  source?: string | null;
}

export interface O15EquipmentRow {
  equipment_id?: string | null;
  name?: string | null;
  command?: unknown;
  status?: unknown;
  speed?: number | null;
  pressure?: number | null;
  temperature?: number | null;
  power?: number | null;
  data_quality?: string | null;
  source?: string | null;
  last_seen?: string | null;
  fault?: unknown;
}

export interface O15Header {
  opportunity?: string;
  title?: string;
  bms?: string | null;
  telemetry?: string | null;
  control_mode?: string | null;
  safety?: string | null;
  optimization?: string | null;
  last_telemetry?: string | null;
  last_optimization?: string | null;
  safe_mode?: boolean;
  ui_state?: string | null;
}

export interface O15Config {
  building_id?: string | null;
  approach_c?: number | null;
  approach_min_c?: number | null;
  approach_max_c?: number | null;
  min_head_pressure?: number | null;
  max_head_pressure?: number | null;
  min_condensing_temp_c?: number | null;
  max_condensing_temp_c?: number | null;
  min_fan_speed_pct?: number | null;
  max_fan_speed_pct?: number | null;
  fan_trim_pct?: number | null;
  tcond_deadband_c?: number | null;
  max_fan_step_pct?: number | null;
  verify_tolerance?: number | null;
  control_mode?: string | null;
  enabled?: boolean | null;
  config_version?: string | null;
}

export interface O15Dashboard {
  opportunity_id?: string;
  live?: boolean;
  agent_status?: string | null;
  status?: string | null;
  ui_state?: string | null;
  recommendation?: string | null;
  recommendation_state?: string | null;
  reason?: string | null;
  confidence?: number | null;
  safety_status?: string | null;
  overall_safety?: string | null;
  current_value?: number | null;
  optimized_value?: number | null;
  unit?: string | null;
  engine_version?: string | null;
  evaluated_at?: string | null;
  energy_impact?: number | null;
  energy_impact_class?: string | null;
  predicted_fan_power_kw?: number | null;
  predicted_power_delta_kw?: number | null;
  verified_savings_kw?: number | null;
  applied_savings_kw?: number | null;
  guide_potential_note?: string | null;
  safe_mode?: boolean;
  bms_connected?: boolean;
  bms_status?: string | null;
  current_state?: O15CurrentState;
  optimized_state?: O15OptimizedState;
  classified_telemetry?: O15ClassifiedTelemetry;
  why?: O15Why;
  safety?: O15Safety;
  safety_checks?: O15SafetyCheck[];
  header?: O15Header;
  config?: O15Config;
  config_labels?: Record<string, string>;
  condensers?: O15EquipmentRow[];
  fans?: O15EquipmentRow[];
  commands?: O15Command[];
  command?: O15Command;
  kpis?: Array<{
    label?: string;
    value?: number | string | null;
    unit?: string | null;
    status?: string | null;
    timestamp?: string | null;
    data_quality?: string | null;
    source?: string | null;
  }>;
  audit?: Array<{ timestamp?: string | null; action?: string | null; result?: string | null }>;
}
