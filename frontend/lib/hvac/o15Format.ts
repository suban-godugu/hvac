import type { O15HistoryPoint } from '@/lib/hvac/o15Types';

export function isMissing(value: unknown): boolean {
  if (value === null || value === undefined || value === '') return true;
  if (typeof value === 'number' && !Number.isFinite(value)) return true;
  if (typeof value === 'string' && value.toLowerCase() === 'nan') return true;
  return false;
}

export function fmtDash(value: unknown, digits = 1): string {
  if (isMissing(value)) return '—';
  if (typeof value === 'number') {
    return Number.isInteger(value) ? String(value) : value.toFixed(digits);
  }
  return String(value);
}

export function fmtUnit(value: unknown, unit: string | null | undefined, digits = 1): string {
  if (isMissing(value)) return '—';
  return unit ? `${fmtDash(value, digits)} ${unit}` : fmtDash(value, digits);
}

export function secondsAgo(iso?: string | null): string {
  if (!iso) return '—';
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return '—';
  const sec = Math.max(0, Math.round((Date.now() - t) / 1000));
  if (sec < 60) return `${sec} seconds ago`;
  if (sec < 3600) return `${Math.round(sec / 60)} min ago`;
  return `${Math.round(sec / 3600)} h ago`;
}

export function confidencePct(value?: number | null): string {
  if (value == null || !Number.isFinite(Number(value))) return 'NO DATA';
  const n = Number(value);
  const pct = n <= 1 ? Math.round(n * 100) : Math.round(n);
  return `${pct}%`;
}

export function confidenceNumber(value?: number | null): number | null {
  if (value == null || !Number.isFinite(Number(value))) return null;
  const n = Number(value);
  return n <= 1 ? Math.round(n * 100) : Math.round(n);
}

export function numericTrend(current: unknown, previous: unknown): '↑' | '↓' | '—' {
  if (isMissing(current) || isMissing(previous)) return '—';
  const a = Number(current);
  const b = Number(previous);
  if (!Number.isFinite(a) || !Number.isFinite(b)) return '—';
  if (a > b) return '↑';
  if (a < b) return '↓';
  return '—';
}

export function mapDecision(data: O15Like): string {
  if (data.safe_mode || data.header?.safe_mode) return 'SAFE_HOLD';
  const rec = (data.recommendation || '').toUpperCase();
  const state = (data.recommendation_state || data.status || '').toUpperCase();
  const ui = (data.ui_state || data.header?.ui_state || '').toUpperCase();
  if (ui === 'NO_DATA' || state.includes('AWAITING')) return 'WAIT_FOR_TELEMETRY';
  if (rec === 'REJECT' || rec === 'BLOCKED' || state === 'REJECTED') return 'BLOCK';
  if (state === 'APPROVAL_REQUIRED') return 'APPROVAL_REQUIRED';
  if (rec === 'FLOAT_HEAD_PRESSURE' || state.includes('READY')) return 'OPTIMIZE';
  if (rec === 'HOLD' || state === 'HOLD') return 'HOLD';
  if (state.includes('REVIEW')) return 'REVIEW_REQUIRED';
  return rec || state || 'WAIT_FOR_TELEMETRY';
}

export function dispatchBlockReason(data: O15Like): string | null {
  const ui = (data.ui_state || data.header?.ui_state || '').toUpperCase();
  const tel = (data.header?.telemetry || data.classified_telemetry?.status || '').toUpperCase();
  const mode = (data.header?.control_mode || data.config?.control_mode || '').toUpperCase();
  if (data.safe_mode || data.header?.safe_mode) return 'SAFETY BLOCK — SAFE MODE';
  if (ui === 'SIMULATION' || tel === 'SIMULATED' || (data.classified_telemetry?.source || '').toUpperCase().includes('SIMUL')) {
    return 'SIMULATION DATA — BMS WRITE DISABLED';
  }
  if (data.header?.bms !== 'LIVE' && !data.bms_connected) return 'BMS OFFLINE — DISPATCH UNAVAILABLE';
  if (tel === 'STALE' || ui === 'STALE') return 'TELEMETRY STALE — OPTIMIZATION HELD';
  if (tel === 'BAD' || ui === 'DEGRADED') return 'TELEMETRY QUALITY BAD — SAFETY BLOCK';
  if (ui === 'NO_DATA') return 'NO TELEMETRY — DISPATCH DISABLED';
  if ((data.safety_status || '').toUpperCase() === 'REJECT') return 'SAFETY BLOCK — DISPATCH DISABLED';
  if (mode === 'ADVISORY') return 'ADVISORY MODE — BMS WRITE DISABLED';
  if (mode === 'APPROVAL_REQUIRED' && (data.commands?.[0]?.status || '').toUpperCase() !== 'APPROVED') {
    return 'APPROVAL REQUIRED — DISPATCH DISABLED';
  }
  if ((data.recommendation || '').toUpperCase() === 'HOLD') return 'HOLD — NO WRITE RECOMMENDED';
  return null;
}

export function operatorErrorMessage(err: unknown, fallback = 'Unable to load O15 data'): string {
  if (err && typeof err === 'object' && 'message' in err && typeof (err as { message: unknown }).message === 'string') {
    const m = (err as { message: string }).message.trim();
    if (!m || /undefined|null|NaN|HTTP\s*500|API ERROR|^500$/i.test(m)) return fallback;
    return m;
  }
  return fallback;
}

export function historyPoints(raw: unknown): O15HistoryPoint[] {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw as O15HistoryPoint[];
  if (typeof raw === 'object' && raw && Array.isArray((raw as { points?: unknown }).points)) {
    return (raw as { points: O15HistoryPoint[] }).points;
  }
  return [];
}

interface O15Like {
  safe_mode?: boolean;
  bms_connected?: boolean;
  recommendation?: string | null;
  recommendation_state?: string | null;
  status?: string | null;
  ui_state?: string | null;
  safety_status?: string | null;
  header?: { safe_mode?: boolean; ui_state?: string | null; telemetry?: string | null; bms?: string | null; control_mode?: string | null };
  classified_telemetry?: { status?: string | null; source?: string | null };
  config?: { control_mode?: string | null };
  commands?: Array<{ status?: string | null }>;
}
