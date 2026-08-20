export type AgentLifecycleState =
  | "IDLE"
  | "OBSERVE"
  | "VALIDATE_DATA"
  | "BUILD_STATE"
  | "DETECT_OPPORTUNITIES"
  | "GENERATE_CANDIDATES"
  | "EVALUATE_CANDIDATES"
  | "SAFETY_CHECK"
  | "EXECUTE"
  | "VERIFY"
  | "KEEP_OR_ROLLBACK"
  | "LEARN";

export type AgentMode = "ADVISORY" | "APPROVAL_REQUIRED" | "AUTO" | "SAFE_MODE";

export interface Zone {
  id: string;
  name: string;
  temp_actual: number;
  temp?: number;
  temp_setpoint: number;
  cooling_sp: number;
  heating_sp: number;
  deadband: number;
  proportional_band: number;
  damper_pos: number;
  damper?: number;
  cooling_request: boolean;
  heating_request: boolean;
  occupied: boolean;
  co2_ppm: number;
  airflow_cfm: number;
}

export interface AHU {
  id: string;
  name: string;
  fan_status: boolean;
  fan_speed_pct: number;
  fan_speed?: number;
  fan_power_kw: number;
  fan_kw?: number;
  sat_actual: number;
  sat_setpoint: number;
  cooling_valve_pct: number;
  vav_zones: Zone[];
}

export interface Chiller {
  id: string;
  name: string;
  status: boolean;
  capacity_tons: number;
  current_tons: number;
  pct_load: number;
  power_kw: number;
  cop: number;
  run_minutes: number;
}

export interface ChillerPlant {
  chillers: Chiller[];
  total_tons: number;
  total_power_kw: number;
  power_kw?: number;
  plant_efficiency_kw_per_ton: number;
  kw_per_ton?: number;
  chws_temp: number;
  chws_setpoint: number;
  chws_sp?: number;
  chwr_temp: number;
  flow_rate_lps: number;
  flow_lps?: number;
}

export interface Weather {
  oat: number;
  oah: number;
  humidity?: number;
  wet_bulb: number;
  solar_irradiance: number;
  solar?: number;
}

export interface ActionRecord {
  id: string;
  opportunity_code: string; // O1, O2, O3, O4
  point_id: string;
  target_equipment?: string;
  previous_value?: number;
  proposed_value: number;
  actual_value?: number;
  reason: string;
  confidence: number;
  safety_result: {
    status: string;
    checks: string[];
  };
  timestamp: string;
  verification_window: number;
  expected_result: string;
  actual_result?: string;
  rollback_value?: number;
  final_status: string; // PENDING_APPROVAL, EXECUTED, VERIFIED_KEPT, ROLLED_BACK, REJECTED_SAFETY
}

export interface Opportunity {
  id?: string;
  opportunity_code?: string;
  title: string;
  agent?: string;
  category?: string;
  savings_kw?: number;
  estimated_power_kw_impact?: number;
  confidence: number;
  impact?: 'High' | 'Medium' | 'Low';
  description?: string;
  trigger_reason?: string;
}

export interface OpportunityDetection {
  opportunity_code: string;
  title: string;
  is_triggered: boolean;
  trigger_reason: string;
  estimated_power_kw_impact?: number | null;
  confidence: number;
}

export interface TelemetryPoint {
  time: string;
  oat: number;
  solar?: number;
  chws_temp?: number;
  chws_sp?: number;
  chwr_temp?: number;
  total_plant_kw?: number;
  total_plant_tons?: number;
  ahu1_sat?: number;
  ahu1_sat_sp?: number;
  ahu1_fan_kw?: number;
  baseline_kw?: number;
  optimized_kw?: number;
  actual_kw?: number;
  predicted_kw?: number;
  applied_kw?: number;
  verified_kw?: number;
  savings_kw?: number;
  savings_pct?: number;
  comfort_pct?: number;
}

export interface SavingsSummary {
  predicted_kw: number;
  applied_kw: number;
  verified_kw: number;
  verified_kwh_today: number;
  verified_cost_saved_usd: number;
  comfort_compliance_pct: number;
  baseline_kw?: number;
  actual_kw?: number;
}

export interface EngineeringLimits {
  building_id: string;
  building: {
    min_space_temp_c: number;
    max_space_temp_c: number;
    min_comfort_deadband_c: number;
    max_comfort_deadband_c: number;
    max_zone_setpoint_step_c: number;
    max_co2_ppm: number;
  };
  ahu: {
    min_sat_c: number;
    max_sat_c: number;
    max_sat_step_c: number;
    min_fan_speed_pct: number;
    max_fan_speed_pct: number;
    min_static_pressure_pa: number;
    max_static_pressure_pa: number;
  };
  chiller_plant: {
    min_chws_temp_c: number;
    max_chws_temp_c: number;
    max_chws_step_c: number;
    min_evap_flow_lps: number;
    chiller_min_run_minutes: number;
    chiller_min_off_minutes: number;
    max_chiller_stages: number;
    compressors_per_chiller: number;
  };
}

export interface FacilityInfo {
  name?: string;
  location?: string;
  timezone?: string;
  areaSqFt?: number;
  plantCapacity?: string | number;
  capacity?: string | number;
}

export interface SupervisoryCycleResponse {
  lifecycle_state: AgentLifecycleState;
  mode: AgentMode;
  simulation_time: string;
  scenario_id: string;
  data_quality_valid: boolean;
  sensor_health: Array<{
    point_id: string;
    is_valid: boolean;
    is_frozen?: boolean;
    is_out_of_range?: boolean;
    error_message?: string;
  }>;
  sensor_faults?: Array<{ point_id?: string; message?: string }>;
  detected_opportunities: OpportunityDetection[];
  candidate_actions: ActionRecord[];
  pending_approvals: ActionRecord[];
  completed_actions: ActionRecord[];
  savings_summary: SavingsSummary;
  cycle_summary: string;
  opportunity_results?: unknown[];
  weather: Weather;
  plant: ChillerPlant;
  ahus: AHU[];
  facility?: FacilityInfo;
}
