/**
 * Plant Control Parameter Optimizations Client API Helpers (O5–O9)
 */
import { apiJson } from './api/client';

export interface CandidateMetric {
  candidate_id: string;
  static_pressure_sp?: number;
  delivery_temp_sp?: number;
  chws_setpoint?: number;
  condenser_water_sp?: number;
  power_shed_kw: number;
  comfort_risk: string;
  safety_status: string;
  decision: string;
  [key: string]: any;
}

export interface PlantControlDashboardState {
  agent_name: string;
  agent_health: string;
  agent_mode: string;
  bms_connection: string;
  telemetry_age_seconds: number;
  total_power_shed_kw: number;
  daily_energy_saved_kwh: number;
  safety_compliance_pct: number;
  active_opportunities_count: number;
  applied_optimizations_count: number;
  o5_summary: {
    title: string;
    current: string;
    optimized: string;
    power_shed_kw: number;
    status: string;
  };
  o6_summary: {
    title: string;
    current: string;
    optimized: string;
    power_shed_kw: number;
    status: string;
  };
  o7_summary: {
    title: string;
    current: string;
    optimized: string;
    power_shed_kw: number;
    status: string;
  };
  o8_summary: {
    title: string;
    current: string;
    optimized: string;
    power_shed_kw: number;
    status: string;
  };
  o9_summary: {
    title: string;
    status: string;
    annual_savings_usd: number;
    payback_years: number;
    roi_pct: number;
  };
}

const PC = '/agents/plant-control';

export async function fetchPlantControlDashboard(): Promise<PlantControlDashboardState> {
  return apiJson(`${PC}/state`);
}

export async function fetchPlantControlActivity(): Promise<any[]> {
  try {
    return (await apiJson(`${PC}/activity`)) || [];
  } catch {
    return [];
  }
}

export async function fetchO5State(): Promise<any> {
  return apiJson(`${PC}/o5/state`);
}

export async function dispatchO5Command(targetValue: number): Promise<any> {
  return apiJson(`${PC}/o5/command`, {
    method: 'POST',
    body: JSON.stringify({ target_setpoint: targetValue, context: { opportunity: 'O5' } }),
  });
}

export async function verifyO5Command(): Promise<any> {
  return apiJson(`${PC}/o5/verify`, { method: 'POST' });
}

export async function rollbackO5Command(): Promise<any> {
  return apiJson(`${PC}/o5/rollback`, { method: 'POST' });
}

export const triggerO5Optimize = dispatchO5Command;
export const triggerO5Rollback = rollbackO5Command;

export async function fetchO6State(): Promise<any> {
  return apiJson(`${PC}/o6/state`);
}

export async function dispatchO6Command(targetValue: number): Promise<any> {
  return apiJson(`${PC}/o6-8/command`, {
    method: 'POST',
    body: JSON.stringify({ target_setpoint: targetValue, reset_type: 'HHW' }),
  });
}

export async function verifyO6Command(): Promise<any> {
  return apiJson(`${PC}/o6-8/verify?mode=HHW`, { method: 'POST' });
}

export async function rollbackO6Command(): Promise<any> {
  return apiJson(`${PC}/o6-8/rollback?mode=HHW`, { method: 'POST' });
}

export const triggerO6Optimize = dispatchO6Command;
export const triggerO6Rollback = rollbackO6Command;

export async function fetchO7State(): Promise<any> {
  return apiJson(`${PC}/o7/state`);
}

export async function dispatchO7Command(targetValue: number): Promise<any> {
  return apiJson(`${PC}/o6-8/command`, {
    method: 'POST',
    body: JSON.stringify({ target_setpoint: targetValue, reset_type: 'CHW' }),
  });
}

export async function verifyO7Command(): Promise<any> {
  return apiJson(`${PC}/o6-8/verify?mode=CHW`, { method: 'POST' });
}

export async function rollbackO7Command(): Promise<any> {
  return apiJson(`${PC}/o6-8/rollback?mode=CHW`, { method: 'POST' });
}

export const triggerO7Optimize = dispatchO7Command;
export const triggerO7Rollback = rollbackO7Command;

export async function fetchO8State(): Promise<any> {
  return apiJson(`${PC}/o8/state`);
}

export async function dispatchO8Command(targetValue: number): Promise<any> {
  return apiJson(`${PC}/o6-8/command`, {
    method: 'POST',
    body: JSON.stringify({ target_setpoint: targetValue, reset_type: 'CW' }),
  });
}

export async function verifyO8Command(): Promise<any> {
  return apiJson(`${PC}/o6-8/verify?mode=CW`, { method: 'POST' });
}

export async function rollbackO8Command(): Promise<any> {
  return apiJson(`${PC}/o6-8/rollback?mode=CW`, { method: 'POST' });
}

export const triggerO8Optimize = dispatchO8Command;
export const triggerO8Rollback = rollbackO8Command;

export async function fetchO9Assessment(): Promise<any> {
  return apiJson(`${PC}/o9/assessment`);
}
