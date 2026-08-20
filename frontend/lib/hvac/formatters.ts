/** Safe HVAC formatters. Never call toLocaleString/toFixed on null. */

function finite(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null;
  const n = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(n)) return null;
  return n;
}

/** 0.685 → 68.5; 68.5 → 68.5; never 68.5 → 6850. Values > 1000 are not percents. */
export function asPercentNumber(value: unknown): number | null {
  const n = finite(value);
  if (n === null) return null;
  if (Math.abs(n) <= 1) return Math.round(n * 1000) / 10;
  if (Math.abs(n) > 1000) return null;
  return Math.round(n * 10) / 10;
}

export function formatPercent(value: unknown): string {
  const n = asPercentNumber(value);
  if (n === null) return '—';
  return `${n.toFixed(1)}%`;
}

export function formatNumber(value: unknown, digits?: number): string {
  const n = finite(value);
  if (n === null) return '—';
  if (digits === undefined) {
    if (Number.isInteger(n)) return Math.round(n).toLocaleString('en-US');
    return n.toFixed(1);
  }
  if (digits === 0) return Math.round(n).toLocaleString('en-US');
  return n.toFixed(digits);
}

export function formatCfm(value: unknown): string {
  const n = finite(value);
  if (n === null) return '—';
  return `${Math.round(n).toLocaleString('en-US')} CFM`;
}

export function formatKw(value: unknown, signed = false): string {
  const n = finite(value);
  if (n === null) return '—';
  return signed ? `${n >= 0 ? '+' : ''}${n.toFixed(2)} kW` : `${n.toFixed(2)} kW`;
}

export function formatKwh(value: unknown, perDay = true): string {
  const n = finite(value);
  if (n === null) return '—';
  return perDay ? `${n.toFixed(1)} kWh/day` : `${n.toFixed(1)} kWh`;
}

export function formatKwhMonth(value: unknown): string {
  const n = finite(value);
  if (n === null) return '—';
  return `${n.toFixed(1)} kWh/month`;
}

export function formatPpm(value: unknown): string {
  const n = finite(value);
  if (n === null) return '—';
  return `${Math.round(n)} ppm`;
}

export function formatTemperature(value: unknown): string {
  const n = finite(value);
  if (n === null) return '—';
  return `${n.toFixed(1)}°C`;
}

export function formatEnthalpy(value: unknown): string {
  const n = finite(value);
  if (n === null) return '—';
  return `${n.toFixed(2)} kJ/kg`;
}

export function formatAgeSeconds(age: unknown): string {
  const n = finite(age);
  if (n === null) return '—';
  if (n < 60) return `${Math.round(n)} sec ago`;
  const minutes = Math.floor(n / 60);
  const seconds = Math.round(n % 60);
  return `${minutes}m ${seconds}s ago`;
}

export function formatDash(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'number' && !Number.isFinite(value)) return '—';
  const s = String(value);
  if (s === 'undefined' || s === 'null' || s === 'NaN') return '—';
  return s;
}

export function formatCFM(value: unknown): string {
  return formatCfm(value);
}

export function formatKW(value: unknown, signed = false): string {
  return formatKw(value, signed);
}

export function formatKWh(value: unknown, perDay = true): string {
  return formatKwh(value, perDay);
}

export function formatPPM(value: unknown): string {
  return formatPpm(value);
}

export function formatEnergyPerDay(value: unknown): string {
  return formatKwh(value, true);
}

export function formatNumberWithUnit(value: unknown, unit: string): string {
  const n = finite(value);
  if (n === null) return '—';
  const num = Number.isInteger(n) ? String(Math.round(n)) : n.toFixed(1);
  return `${num} ${unit}`;
}

export function formatHours(value: unknown): string {
  const n = finite(value);
  if (n === null) return '—';
  return `${n.toFixed(1)} h`;
}

export function formatDateTime(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  const s = String(value);
  if (s === 'undefined' || s === 'null' || s === 'NaN') return '—';
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return s;
  return d.toISOString().replace('T', ' ').slice(0, 19);
}

export function formatConfidence(value: unknown): string {
  const n = asPercentNumber(value);
  if (n === null) return '—';
  return `${Math.round(n)}%`;
}
