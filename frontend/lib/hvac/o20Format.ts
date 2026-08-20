import type { PlatformGate } from '@/lib/hvac/o20Api';
import type { OmDashboardData, OmOpportunity, TelemetryValue } from '@/lib/hvac/omTypes';
import { metricNum, metricStr } from '@/lib/hvac/omTypes';
import { formatDash } from '@/lib/hvac/formatters';
import {
  isO17Simulation,
  o17Bms,
  o17ConfidencePct,
  o17ErrorMessage,
  o17Freshness,
  o17Mode,
  o17QualityLabel,
  o17SecondsAgo,
  o17TelemetryBadge,
} from '@/lib/hvac/o17Format';

export const O20_GUIDE_DESCRIPTION =
  'Management of system control software governs HVAC-BMS versions, configuration, overrides, and point quality so control logic is not changed ad hoc. Energy-efficient operation depends on approved control strategies remaining in place, with backups and rollback, rather than automatic firmware or logic deployment.';

export const isO20Simulation = isO17Simulation;
export const o20TelemetryBadge = o17TelemetryBadge;
export const o20Freshness = o17Freshness;
export const o20Bms = o17Bms;
export const o20Mode = o17Mode;
export const o20SecondsAgo = o17SecondsAgo;
export const o20ConfidencePct = o17ConfidencePct;

export function o20ErrorMessage(err: unknown): string {
  return o17ErrorMessage(err, 'Unable to load O20 control-software data');
}

export function o20QualityLabel(data: OmOpportunity): string {
  if (isO20Simulation(data)) return 'SIMULATED';
  const q = o17QualityLabel(data);
  return q === 'SIMULATION' ? 'SIMULATED' : q;
}

export function o20Int(data: OmOpportunity, current: TelemetryValue, metricKey: string): TelemetryValue {
  if (current != null && Number.isFinite(Number(current))) return Number(current);
  return metricNum(data.metrics, metricKey);
}

export function o20Counts(data: OmOpportunity) {
  return {
    points: o20Int(data, data.current?.controlPoints ?? null, 'point_count'),
    healthy: o20Int(data, data.current?.healthyPoints ?? null, 'healthy_points'),
    degraded: o20Int(data, data.current?.degradedPoints ?? null, 'degraded_points'),
    overrides: o20Int(data, data.current?.overrides ?? null, 'override_count'),
    drift: o20Int(data, data.current?.driftCount ?? null, 'drift_count'),
    stale: o20Int(data, null, 'stale_points'),
    failed: o20Int(data, null, 'failed_points'),
    critical: o20Int(data, data.current?.criticalIssues ?? null, 'critical_issues'),
    healthPct: data.current?.controlHealthPct ?? metricNum(data.metrics, 'control_health_pct'),
    driftPct: metricNum(data.metrics, 'config_drift_pct'),
  };
}

export function o20Decision(data: OmOpportunity): string {
  const d = (data.supervisory?.decision || '').toUpperCase();
  if (d === 'BLOCK' || d === 'BLOCKED') return 'BLOCKED';
  if (d === 'WAIT_FOR_TELEMETRY') return 'WAIT_FOR_TELEMETRY';
  if (d === 'SAFE_HOLD') return 'SAFE_HOLD';
  if (d === 'OPTIMIZE') return 'REVIEW_REQUIRED';
  if (d === 'MONITOR') return 'REVIEW_REQUIRED';
  if (d === 'REVIEW_REQUIRED') return 'REVIEW_REQUIRED';
  return d || 'WAIT_FOR_TELEMETRY';
}

export function o20WriteBlock(data: OmOpportunity, dash?: OmDashboardData | null, platform?: PlatformGate | null): string | null {
  if (platform?.safeMode || (platform?.mode || '').toUpperCase() === 'SAFE_MODE') {
    return 'SAFE_MODE ACTIVE — SOFTWARE WRITE DISABLED';
  }
  if (isO20Simulation(data)) return 'SIMULATION DATA — SOFTWARE WRITE DISABLED';
  const tel = o20TelemetryBadge(data);
  if (tel === 'STALE') return 'TELEMETRY STALE — CHANGE HELD';
  const q = o20QualityLabel(data).toUpperCase();
  if (q === 'BAD') return 'TELEMETRY QUALITY BAD — SAFETY BLOCK';
  const bms = o20Bms(dash, data);
  if (bms === 'OFFLINE') return 'BMS OFFLINE — DISPATCH UNAVAILABLE';
  const safety = (data.safety?.status || platform?.safety || '').toUpperCase();
  if (safety && safety !== 'PASS' && safety !== 'SAFE' && safety !== 'WARNING') {
    return 'SAFETY NOT PASS — SOFTWARE WRITE DISABLED';
  }
  if (data.safety?.passed === false) return 'SAFETY BLOCK — SOFTWARE WRITE DISABLED';
  return 'O20 requires change-request review; automatic software deploy is prohibited.';
}

export function o20CanSubmitChange(data: OmOpportunity, dash?: OmDashboardData | null, platform?: PlatformGate | null): boolean {
  if (platform?.safeMode || (platform?.mode || '').toUpperCase() === 'SAFE_MODE') return false;
  if (isO20Simulation(data)) return false;
  if (o20TelemetryBadge(data) === 'STALE' || o20TelemetryBadge(data) === 'NO DATA' || o20TelemetryBadge(data) === 'MISSING' || o20TelemetryBadge(data) === 'BMS OFFLINE') return false;
  if (o20QualityLabel(data) === 'BAD') return false;
  if (o20Bms(dash, data) === 'OFFLINE') return false;
  const safety = (data.safety?.status || platform?.safety || '').toUpperCase();
  if (safety === 'FAIL' || safety === 'BLOCK' || safety === 'BLOCKED' || safety === 'SAFE_HOLD') return false;
  if (data.safety?.passed === false) return false;
  return true;
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}

export function o20Controller(data: OmOpportunity): Record<string, unknown> | null {
  const c = data.metrics?.controller;
  return isRecord(c) ? c : null;
}

export function o20ControllerField(data: OmOpportunity, key: string): string {
  const ctrl = o20Controller(data);
  if (!ctrl) return formatDash(metricStr(data.metrics, key));
  const v = ctrl[key];
  if (v === null || v === undefined || v === '') return '—';
  const s = String(v);
  if (s === 'undefined' || s === 'null' || s === 'NaN') return '—';
  return s;
}
