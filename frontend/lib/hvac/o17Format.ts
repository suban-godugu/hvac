import type { OmDashboardData, OmOpportunity, TelemetryValue } from '@/lib/hvac/omTypes';
import { metricNum, metricStr } from '@/lib/hvac/omTypes';
import { formatDash, formatKw } from '@/lib/hvac/formatters';
import { actionErrorText } from '@/lib/hvac/actionError';
import { provenanceFromAgent, type ProvenanceLabel } from '@/lib/hvac/provenance';

export const O17_GUIDE_DESCRIPTION =
  'Integrated energy management planning coordinates senior management, site operations and maintenance, electrical/mechanical/HVAC-BMS contractors, and the sustainability team. Policies, procedures, documentation, and training belong in a facility energy management plan so HVAC energy use, controls, and efficiency requirements are known and maintained.';

export function finiteKw(value: unknown): TelemetryValue {
  if (value === null || value === undefined || value === '') return null;
  const n = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

export function o17Kw(value: unknown): string {
  return formatKw(value);
}

export function o17SecondsAgo(iso?: string | null): string {
  if (!iso) return '—';
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return '—';
  const sec = Math.max(0, Math.round((Date.now() - t) / 1000));
  if (sec < 60) return `${sec} sec ago`;
  if (sec < 3600) return `${Math.round(sec / 60)} min ago`;
  return `${Math.round(sec / 3600)} h ago`;
}

export function o17Trend(current: unknown, baseline: unknown): string {
  const a = finiteKw(current);
  const b = finiteKw(baseline);
  if (a === null || b === null) return '—';
  if (a > b) return '↑';
  if (a < b) return '↓';
  return '→';
}

export function o17Safety(data: OmOpportunity): string {
  const s = (data.safety?.status || '').toUpperCase();
  if (s === 'PASS' || s === 'SAFE') return 'SAFE';
  if (s === 'WARNING' || s === 'WARN') return 'WARNING';
  if (s === 'FAIL' || s === 'BLOCK' || s === 'BLOCKED') return 'BLOCKED';
  return s || '—';
}

export function o17QualityLabel(data: OmOpportunity): string {
  const tel = o17Provenance(data);
  if (tel === 'SIMULATED') return 'SIMULATION';
  if (tel === 'STALE') return 'STALE';
  if (tel === 'BMS OFFLINE') return 'BMS OFFLINE';
  if (tel === 'NO DATA') return '—';
  const q = (data.telemetry?.quality || data.metadata?.dataQuality || '').toUpperCase();
  if (q === 'GOOD' || q === 'OK' || q === 'HEALTHY') return 'GOOD';
  if (q === 'BAD' || q === 'DEGRADED' || q === 'POOR') return 'BAD';
  if (q === 'SIMULATION' || q === 'SIMULATED') return 'SIMULATION';
  if (q === 'STALE') return 'STALE';
  if (!q) return tel === 'LIVE' ? 'GOOD' : tel || '—';
  return q;
}

export function o17Bms(dash?: OmDashboardData | null, data?: OmOpportunity | null): string {
  if (data && o17Provenance(data) === 'SIMULATED') return 'OFFLINE';
  if (data?.bmsConnected || dash?.module?.bmsConnected) return 'CONNECTED';
  const raw = (dash?.module?.bms?.status || '').toUpperCase();
  if (raw === 'CONNECTED' || raw === 'ONLINE') return 'CONNECTED';
  if (raw === 'DEGRADED') return 'STALE';
  if (raw === 'LIVE') return data && o17Provenance(data) === 'LIVE' ? 'CONNECTED' : 'OFFLINE';
  if (raw) return raw === 'OFFLINE' ? 'OFFLINE' : raw;
  return 'OFFLINE';
}

export function o17Mode(dash?: OmDashboardData | null): string {
  return (dash?.module?.mode || 'SUPERVISORY').toUpperCase();
}

export function o17ErrorMessage(err: unknown, fallback = 'Unable to load O17 energy planning data'): string {
  return actionErrorText(err, fallback);
}

export function o17Provenance(data?: OmOpportunity | null): ProvenanceLabel {
  return provenanceFromAgent(data as unknown as Record<string, unknown>);
}

export function o17CurrentKw(data: OmOpportunity, dash?: OmDashboardData | null): TelemetryValue {
  return (
    finiteKw(data.energy?.currentKw) ??
    finiteKw(data.current?.kw) ??
    finiteKw(dash?.charts?.energyPlanning?.currentKw)
  );
}

export function o17BaselineKw(data: OmOpportunity, dash?: OmDashboardData | null): TelemetryValue {
  return (
    finiteKw(data.energy?.baselineKw) ??
    finiteKw(data.current?.baselineKw) ??
    finiteKw(dash?.charts?.energyPlanning?.baselineKw)
  );
}

export function o17TargetKw(data: OmOpportunity, dash?: OmDashboardData | null): TelemetryValue {
  return (
    finiteKw(data.energy?.targetKw) ??
    finiteKw(data.current?.targetKw) ??
    finiteKw(dash?.charts?.energyPlanning?.targetKw)
  );
}

export function o17ImpactKw(data: OmOpportunity, dash?: OmDashboardData | null): TelemetryValue {
  return (
    finiteKw(data.energy?.savingKw) ??
    finiteKw(data.recommendation?.expectedImpactKw) ??
    finiteKw(dash?.charts?.energyPlanning?.savingsKw)
  );
}

export function isO17Simulation(data: OmOpportunity): boolean {
  return o17Provenance(data) === 'SIMULATED';
}

export function o17TelemetryBadge(data: OmOpportunity): string {
  return o17Provenance(data);
}

export function o17Freshness(data: OmOpportunity): string {
  const tel = o17Provenance(data);
  if (tel === 'SIMULATED') return 'SIMULATED';
  if (tel === 'STALE') return 'STALE';
  if (tel === 'LIVE') return 'FRESH';
  if (tel === 'NO DATA' || tel === 'BMS OFFLINE') return tel;
  return tel;
}

export function o17ConfidencePct(value?: number | null): string {
  if (value == null || !Number.isFinite(Number(value))) return '—';
  const n = Number(value);
  const pct = n <= 1 ? Math.round(n * 100) : Math.round(n);
  return `${pct}%`;
}

export function o17RecCardStatus(data: OmOpportunity): string {
  const decision = (data.supervisory?.decision || '').toUpperCase();
  const audit = data.audit || [];
  const types = audit.map((a) => (a.event_type || a.message || '').toUpperCase());
  if (types.some((t) => t.includes('VERIFY'))) return 'VERIFIED';
  if (types.some((t) => t.includes('DISPATCH') || t.includes('PLAN_DISPATCH'))) return 'IMPLEMENTED';
  if (decision === 'BLOCK' || decision === 'BLOCKED') return 'BLOCKED';
  if (decision === 'WAIT_FOR_TELEMETRY' || decision === 'SAFE_HOLD') return 'UNDER REVIEW';
  if (data.recommendation?.action) return 'RECOMMENDED';
  return '—';
}

export function o17Decision(data: OmOpportunity): string {
  const d = (data.supervisory?.decision || '').toUpperCase();
  if (d === 'BLOCK' || d === 'BLOCKED') return 'BLOCKED';
  if (d === 'MONITOR') return 'REVIEW_REQUIRED';
  return d || 'WAIT_FOR_TELEMETRY';
}

export function o17Metric(data: OmOpportunity, key: string): number | null {
  return metricNum(data.metrics, key);
}

export function o17MetricText(data: OmOpportunity, key: string): string {
  return formatDash(metricStr(data.metrics, key));
}

export function o17PlanningPeriod(data: OmOpportunity): string {
  return formatDash(
    metricStr(data.metrics, 'planning_period') ||
      metricStr(data.metrics, 'forecast_horizon') ||
      metricStr(data.metrics, 'horizon')
  );
}
