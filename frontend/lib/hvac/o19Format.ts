import type { OmOpportunity, TelemetryValue } from '@/lib/hvac/omTypes';
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

export const O19_GUIDE_DESCRIPTION =
  'Energy-efficiency maintenance keeps HVAC plant in a condition that avoids unnecessary energy use: filters, coils, sensors, and cycling behaviour are inspected against maintenance baselines so degraded equipment is corrected before it becomes an energy and reliability defect.';

export const isO19Simulation = isO17Simulation;
export const o19TelemetryBadge = o17TelemetryBadge;
export const o19Freshness = o17Freshness;
export const o19Bms = o17Bms;
export const o19Mode = o17Mode;
export const o19SecondsAgo = o17SecondsAgo;
export const o19ConfidencePct = o17ConfidencePct;

export function o19ErrorMessage(err: unknown): string {
  return o17ErrorMessage(err, 'Unable to load O19 energy efficiency maintenance data');
}

export function o19QualityLabel(data: OmOpportunity): string {
  if (isO19Simulation(data)) return 'SIMULATED';
  return o17QualityLabel(data) === 'SIMULATION' ? 'SIMULATED' : o17QualityLabel(data);
}

export function o19FleetStatus(data: OmOpportunity): string {
  const s = (data.status || '').toUpperCase().replace(/ /g, '_');
  if (s.includes('URGENT')) return 'URGENT MAINTENANCE';
  if (s.includes('MAINTENANCE_REQUIRED') || s === 'MAINTENANCE REQUIRED') return 'MAINTENANCE REQUIRED';
  if (s.includes('MONITOR')) return 'MONITOR';
  if (s.includes('NORMAL') || s === 'OPTIMAL') return 'NORMAL';
  return formatDash(data.status);
}

export function o19Decision(data: OmOpportunity): string {
  const d = (data.supervisory?.decision || '').toUpperCase();
  if (d === 'WAIT_FOR_TELEMETRY' || d === 'SAFE_HOLD') return 'REVIEW_REQUIRED';
  if (d === 'URGENT_MAINTENANCE') return 'URGENT_MAINTENANCE';
  if (d === 'MAINTENANCE_REQUIRED') return 'MAINTENANCE_REQUIRED';
  if (d === 'MONITOR') return 'MONITOR';
  if (d === 'NORMAL') return 'NORMAL';
  const fleet = o19FleetStatus(data);
  if (fleet === 'URGENT MAINTENANCE') return 'URGENT_MAINTENANCE';
  if (fleet === 'MAINTENANCE REQUIRED') return 'MAINTENANCE_REQUIRED';
  if (fleet === 'MONITOR') return 'MONITOR';
  if (fleet === 'NORMAL') return 'NORMAL';
  return d || 'REVIEW_REQUIRED';
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}

function str(v: unknown): string | null {
  if (v === null || v === undefined || v === '') return null;
  const s = String(v);
  if (s === 'undefined' || s === 'null' || s === 'NaN') return null;
  return s;
}

function num(v: unknown): TelemetryValue {
  if (v === null || v === undefined || v === '') return null;
  const n = typeof v === 'number' ? v : Number(v);
  return Number.isFinite(n) ? n : null;
}

export interface O19Finding {
  id: string | null;
  equipmentId: string | null;
  maintenanceType: string | null;
  status: string | null;
  runtimeHours: TelemetryValue;
  efficiency: TelemetryValue;
  degradation: TelemetryValue;
  priority: string | null;
    recommendation: string | null;
    energyImpact: TelemetryValue;
    finding: string | null;
    completedAt: string | null;
}

export interface O19Issue {
  finding: string | null;
  energyImpactKw: TelemetryValue;
  priority: string | null;
  equipmentId: string | null;
  issueType: string | null;
}

export function o19Findings(data: OmOpportunity): O19Finding[] | null {
  const raw = data.metrics?.findings ?? data.metrics?.work_orders;
  if (!Array.isArray(raw)) return null;
  return raw.filter(isRecord).map((o) => ({
    id: str(o.id),
    equipmentId: str(o.equipment_id) || str(o.equipmentId),
    maintenanceType: str(o.maintenance_type) || str(o.maintenanceType),
    status: str(o.status),
    runtimeHours: num(o.runtime_hours ?? o.runtimeHours),
    efficiency: num(o.efficiency),
    degradation: num(o.degradation),
    priority: str(o.priority),
    recommendation: str(o.recommendation),
    energyImpact: num(o.energy_impact ?? o.energyImpact),
    finding: str(o.finding) || str(o.recommendation),
    completedAt: str(o.completed_at) || str(o.completedAt),
  }));
}

export function o19Issues(data: OmOpportunity): O19Issue[] | null {
  const raw = data.metrics?.detected_issues;
  if (!Array.isArray(raw)) return null;
  return raw.filter(isRecord).map((i) => ({
    finding: str(i.finding),
    energyImpactKw: num(i.energy_impact_kw ?? i.energyImpactKw),
    priority: str(i.priority),
    equipmentId: str(i.equipment_id) || str(i.equipmentId),
    issueType: str(i.issue_type) || str(i.issueType),
  }));
}

export function o19EquipmentType(id: string): string {
  const u = id.toUpperCase();
  if (u.startsWith('AHU')) return 'AHU';
  if (u.includes('CHILLER') || /^CH[-_]?\d/.test(u)) return 'Chiller';
  if (u.includes('PUMP')) return 'Pump';
  if (u.includes('FAN')) return 'Fan';
  if (u.includes('TOWER') || u.startsWith('CT') || u.includes('CONDENSER')) return 'Cooling Equipment';
  return 'Other';
}

export interface O19EquipmentRow {
  id: string;
  name: string;
  type: string;
  status: string;
  health: TelemetryValue;
  lastSeen: string | null;
  indicator: string;
  priority: string | null;
}

export function o19EquipmentRows(data: OmOpportunity): O19EquipmentRow[] | null {
  const findings = o19Findings(data);
  const issues = o19Issues(data);
  const telId = metricStr(data.metrics, 'equipment_id');
  const ids = new Set<string>();
  if (telId) ids.add(telId);
  for (const f of findings || []) if (f.equipmentId) ids.add(f.equipmentId);
  for (const i of issues || []) if (i.equipmentId) ids.add(i.equipmentId);
  if (ids.size === 0) return null;
  const health = data.current?.equipmentHealthPct ?? metricNum(data.metrics, 'equipment_health_pct');
  const lastSeen = data.telemetry?.lastUpdated || data.timestamp || null;
  const fleet = o19FleetStatus(data);
  return Array.from(ids).map((id) => {
    const open = (findings || []).filter((f) => f.equipmentId === id && !['COMPLETED', 'CLOSED', 'CANCELLED'].includes((f.status || '').toUpperCase()));
    const eqIssues = (issues || []).filter((i) => i.equipmentId === id);
    const p1 = eqIssues.some((i) => (i.priority || '').toUpperCase() === 'P1' || (i.priority || '').toUpperCase() === 'CRITICAL');
    let status = 'NORMAL';
    if (p1 || fleet === 'URGENT MAINTENANCE') status = 'URGENT MAINTENANCE';
    else if (open.length || eqIssues.length || fleet === 'MAINTENANCE REQUIRED') status = 'MAINTENANCE REQUIRED';
    else if ((health != null && health < 90) || fleet === 'MONITOR') status = 'MONITOR';
    const pri = open[0]?.priority || eqIssues[0]?.priority || data.priority || null;
    const indicator =
      metricNum(data.metrics, 'filter_dp_rise_pct') != null
        ? `Filter ΔP rise ${formatDash(metricNum(data.metrics, 'filter_dp_rise_pct'))}%`
        : open[0]?.maintenanceType || eqIssues[0]?.issueType || '—';
    return {
      id,
      name: id,
      type: o19EquipmentType(id),
      status,
      health,
      lastSeen,
      indicator,
      priority: pri,
    };
  });
}

export function o19Health(data: OmOpportunity): TelemetryValue {
  return data.current?.equipmentHealthPct ?? metricNum(data.metrics, 'equipment_health_pct');
}

export function o19OpenCount(data: OmOpportunity): TelemetryValue {
  const findings = o19Findings(data);
  if (findings) {
    return findings.filter((f) => !['COMPLETED', 'CLOSED', 'CANCELLED'].includes((f.status || '').toUpperCase())).length;
  }
  const alerts = data.current?.maintenanceAlerts;
  return alerts == null ? null : alerts;
}
