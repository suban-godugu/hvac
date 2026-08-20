import type { OmOpportunity, TelemetryValue } from '@/lib/hvac/omTypes';
import { metricNum } from '@/lib/hvac/omTypes';
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

export const O18_GUIDE_DESCRIPTION =
  'Energy management training and awareness addresses operator and occupant capability: policies, procedures, documentation, and role-based training so HVAC energy-efficiency requirements and approved control strategies are understood and applied. Outcomes include fewer inappropriate overrides, transparent reporting of energy objectives, and maintained energy-efficient BMS/HVAC operation.';

export const isO18Simulation = isO17Simulation;
export const o18TelemetryBadge = o17TelemetryBadge;
export const o18Freshness = o17Freshness;
export const o18Bms = o17Bms;
export const o18Mode = o17Mode;
export const o18QualityLabel = o17QualityLabel;
export const o18SecondsAgo = o17SecondsAgo;
export const o18ConfidencePct = o17ConfidencePct;

export function o18ErrorMessage(err: unknown): string {
  return o17ErrorMessage(err, 'Unable to load O18 training and awareness data');
}

export interface OmTrainingProgram {
  id: string | null;
  topic: string | null;
  programName: string | null;
  required: boolean | null;
  status: string | null;
}

export interface OmTrainingCompletion {
  programId: string | null;
  roleLabel: string | null;
  completionPct: TelemetryValue;
  status: string | null;
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

export function o18Programs(data: OmOpportunity): OmTrainingProgram[] | null {
  const raw = data.metrics?.programs;
  if (!Array.isArray(raw)) return null;
  return raw.filter(isRecord).map((p) => ({
    id: str(p.id),
    topic: str(p.topic),
    programName: str(p.program_name) || str(p.programName),
    required: typeof p.required === 'boolean' ? p.required : null,
    status: str(p.status),
  }));
}

export function o18Completions(data: OmOpportunity): OmTrainingCompletion[] | null {
  const raw = data.metrics?.completions;
  if (!Array.isArray(raw)) return null;
  return raw.filter(isRecord).map((c) => ({
    programId: str(c.program_id) || str(c.programId),
    roleLabel: str(c.role_label) || str(c.roleLabel),
    completionPct: num(c.completion_pct ?? c.completionPct),
    status: str(c.status),
  }));
}

export function o18Gaps(data: OmOpportunity): string[] | null {
  const raw = data.metrics?.knowledge_gaps;
  if (!Array.isArray(raw)) return null;
  return raw.map((g) => str(g)).filter((g): g is string => Boolean(g));
}

export type TrainingBucket = 'Pending' | 'In Progress' | 'Completed';

export function o18Bucket(status?: string | null): TrainingBucket | null {
  const s = (status || '').toUpperCase();
  if (!s) return null;
  if (s === 'COMPLETED' || s === 'COMPLETE' || s === 'DONE') return 'Completed';
  if (s === 'ACTIVE' || s === 'IN_PROGRESS' || s === 'IN PROGRESS') return 'In Progress';
  if (s === 'OPEN' || s === 'PENDING' || s === 'ASSIGNED') return 'Pending';
  return null;
}

export function o18Counts(programs: OmTrainingProgram[] | null): {
  total: number | null;
  completed: number | null;
  inProgress: number | null;
  pending: number | null;
} {
  if (!programs) return { total: null, completed: null, inProgress: null, pending: null };
  let completed = 0;
  let inProgress = 0;
  let pending = 0;
  for (const p of programs) {
    const b = o18Bucket(p.status);
    if (b === 'Completed') completed += 1;
    else if (b === 'In Progress') inProgress += 1;
    else pending += 1;
  }
  return { total: programs.length, completed, inProgress, pending };
}

export function o18Coverage(data: OmOpportunity): TelemetryValue {
  return data.current?.trainingCoveragePct ?? metricNum(data.metrics, 'training_coverage_pct');
}

export function o18Affected(data: OmOpportunity): TelemetryValue {
  return data.current?.affectedUsers ?? metricNum(data.metrics, 'affected_users');
}

export function o18EnergyImpact(data: OmOpportunity): TelemetryValue {
  return data.energy?.impactKwhDay ?? metricNum(data.metrics, 'energy_impact_kwh_day');
}

export function o18Decision(data: OmOpportunity): string {
  const d = (data.supervisory?.decision || '').toUpperCase();
  const rec = (data.recommendation?.action || '').toUpperCase();
  if (d === 'WAIT_FOR_TELEMETRY' || d === 'SAFE_HOLD' || rec === 'HOLD') return 'WAIT_FOR_DATA';
  if (d === 'REVIEW_REQUIRED') return 'REVIEW_REQUIRED';
  if (d === 'MONITOR' && rec.includes('MAINTAIN')) return 'COMPLETE';
  if (rec.includes('ASSIGN') || d === 'OPTIMIZE') return 'RECOMMEND';
  if (d === 'MONITOR') return 'COMPLETE';
  return d || 'WAIT_FOR_DATA';
}

export function o18RecStatus(action?: string | null, programStatus?: string | null): string {
  const bucket = o18Bucket(programStatus);
  if (bucket === 'Completed') return 'COMPLETED';
  if (bucket === 'In Progress') return 'IN PROGRESS';
  const a = (action || '').toUpperCase();
  if (a.includes('MAINTAIN')) return 'COMPLETED';
  if (a.includes('HOLD')) return 'REVIEW REQUIRED';
  if (a) return 'RECOMMENDED';
  return 'REVIEW REQUIRED';
}

export function o18Dash(value: unknown): string {
  return formatDash(value);
}
