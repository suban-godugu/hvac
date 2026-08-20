import { fmtDash, fmtUnit, historyPoints, isMissing, numericTrend, operatorErrorMessage, secondsAgo } from '@/lib/hvac/o15Format';
import type { O16Dashboard, O16HistoryPoint, O16RecommendationPayload } from '@/lib/hvac/o16Types';

export { fmtDash, fmtUnit, isMissing, numericTrend, secondsAgo };

export function o16Error(err: unknown) {
  return operatorErrorMessage(err, 'Unable to load O16 data');
}

export function o16HistoryPoints(raw: unknown): O16HistoryPoint[] {
  return historyPoints(raw) as O16HistoryPoint[];
}

export function recPayload(data: O16Dashboard): O16RecommendationPayload {
  const r = data.recommendation;
  if (r && typeof r === 'object') return r;
  return {};
}

export function recCode(data: O16Dashboard): string {
  const r = data.recommendation;
  if (typeof r === 'string' && r.trim()) return r.toUpperCase();
  return (data.recommendation_state || data.status || '').toUpperCase();
}

export function isSimulation(data: O16Dashboard): boolean {
  const ui = (data.ui_state || data.header?.ui_state || '').toUpperCase();
  const tel = (data.header?.telemetry || data.classified_telemetry?.status || '').toUpperCase();
  const src = (data.classified_telemetry?.source || '').toUpperCase();
  return ui === 'SIMULATION' || tel === 'SIMULATED' || src.includes('SIMUL') || src.includes('DEMO');
}

export function telemetryBadge(data: O16Dashboard): string {
  if (isSimulation(data)) return 'SIMULATED';
  const tel = (data.header?.telemetry || data.classified_telemetry?.status || 'MISSING').toUpperCase();
  if (tel === 'GOOD') return 'GOOD';
  if (tel === 'LIVE') return data.bms_connected ? 'LIVE' : 'NO DATA';
  return tel || 'MISSING';
}

export function freshnessBadge(data: O16Dashboard): string {
  if (isSimulation(data)) return 'SIMULATED';
  const ui = (data.ui_state || data.header?.ui_state || '').toUpperCase();
  const tel = (data.header?.telemetry || '').toUpperCase();
  if (ui === 'STALE' || tel === 'STALE') return 'STALE';
  if (ui === 'NO_DATA' || tel === 'MISSING' || tel === 'NO_DATA') return 'NO DATA';
  if (data.live && tel === 'LIVE' && !isSimulation(data) && data.bms_connected) return 'FRESH';
  return 'NO DATA';
}

export function bmsBadge(data: O16Dashboard): string {
  if (isSimulation(data)) return 'OFFLINE';
  return data.header?.bms === 'CONNECTED' || data.header?.bms === 'LIVE' || data.bms_connected ? 'CONNECTED' : 'OFFLINE';
}

export function mapO16Decision(data: O16Dashboard): string {
  if (data.safe_mode || data.header?.safe_mode) return 'SAFE_HOLD';
  const rec = recCode(data);
  const ui = (data.ui_state || data.header?.ui_state || '').toUpperCase();
  if (ui === 'NO_DATA' || rec.includes('AWAITING')) return 'WAIT_FOR_TELEMETRY';
  if (rec === 'REJECT' || rec === 'BLOCKED' || rec === 'REJECTED') return 'BLOCK';
  if (rec === 'APPROVAL_REQUIRED') return 'APPROVAL_REQUIRED';
  if (rec === 'OPTIMIZE_HP' || rec === 'ISOLATE_UNIT' || rec.includes('READY')) return 'OPTIMIZE';
  if (rec === 'HOLD') return 'HOLD';
  return rec || 'WAIT_FOR_TELEMETRY';
}

export function dispatchBlockReason(data: O16Dashboard): string | null {
  const ui = (data.ui_state || data.header?.ui_state || '').toUpperCase();
  const tel = (data.header?.telemetry || data.classified_telemetry?.status || '').toUpperCase();
  const mode = (data.header?.control_mode || data.config?.control_mode || '').toUpperCase();
  if (data.safe_mode || data.header?.safe_mode) return 'SAFETY BLOCK — SAFE MODE';
  if (isSimulation(data)) return 'SIMULATION DATA — BMS WRITE DISABLED';
  if (data.header?.bms !== 'LIVE' && !data.bms_connected) return 'BMS OFFLINE — DISPATCH UNAVAILABLE';
  if (tel === 'STALE' || ui === 'STALE') return 'TELEMETRY STALE — OPTIMIZATION HELD';
  if (tel === 'BAD') return 'TELEMETRY QUALITY BAD — SAFETY BLOCK';
  if (ui === 'NO_DATA') return 'NO TELEMETRY — DISPATCH DISABLED';
  if ((data.safety_status || '').toUpperCase() === 'REJECT') return 'SAFETY BLOCK — DISPATCH DISABLED';
  if (mode === 'ADVISORY') return 'ADVISORY MODE — BMS WRITE DISABLED';
  if (mode === 'APPROVAL_REQUIRED' && (data.commands?.[0]?.status || '').toUpperCase() !== 'APPROVED') {
    return 'APPROVAL REQUIRED — DISPATCH DISABLED';
  }
  if (recCode(data) === 'HOLD') return 'HOLD — NO WRITE RECOMMENDED';
  return null;
}

export function confidencePct(value?: number | null): string {
  if (value == null || !Number.isFinite(Number(value))) return 'NO DATA';
  const n = Number(value);
  const pct = n <= 1 ? Math.round(n * 100) : Math.round(n);
  return `${pct}%`;
}
