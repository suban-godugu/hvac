/** Frontend formatter contract: never call toLocaleString on null/undefined. */
function finite(value) {
  if (value === null || value === undefined || value === '') return null;
  const n = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(n)) return null;
  return n;
}

function formatCfm(value) {
  const n = finite(value);
  if (n === null) return '—';
  return `${Math.round(n).toLocaleString('en-US')} CFM`;
}

function formatKw(value) {
  const n = finite(value);
  if (n === null) return '—';
  return `${n.toFixed(2)} kW`;
}

function formatPercent(value) {
  const n = finite(value);
  if (n === null) return '—';
  return `${n.toFixed(1)}%`;
}

function formatDash(value) {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'number' && !Number.isFinite(value)) return '—';
  const s = String(value);
  if (s === 'undefined' || s === 'null' || s === 'NaN') return '—';
  return s;
}

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

assert(formatCfm(undefined) === '—', 'undefined CFM');
assert(formatCfm(null) === '—', 'null CFM');
assert(formatCfm(Number.NaN) === '—', 'NaN CFM');
assert(formatCfm(Number.POSITIVE_INFINITY) === '—', 'Infinity CFM');
assert(formatKw('not-a-number') === '—', 'invalid string kW');

function formatHours(value) {
  const n = finite(value);
  if (n === null) return '—';
  return `${n.toFixed(1)} h`;
}
assert(formatHours(undefined) === '—', 'undefined hours');
assert(formatHours(8.2) === '8.2 h', 'hours');
assert(formatKw(undefined) === '—', 'undefined kW');
assert(formatPercent(null) === '—', 'null percent');
assert(formatDash(undefined) === '—', 'undefined dash');
assert(formatDash('undefined') === '—', 'string undefined');
assert(formatDash('NaN') === '—', 'string NaN');

let crashed = false;
try {
  undefined.toLocaleString();
} catch {
  crashed = true;
}
assert(crashed, 'baseline: undefined.toLocaleString must throw');
assert(formatCfm(undefined) === '—', 'guarded formatter must not throw');

function formatKwhMonth(value) {
  const n = finite(value);
  if (n === null) return '—';
  return `${n.toFixed(1)} kWh/month`;
}
assert(formatKwhMonth(undefined) === '—', 'undefined kWh/month');
assert(formatKwhMonth(Number.NaN) === '—', 'NaN kWh/month');

function displayKpiText(value) {
  if (value === null || value === undefined || value === '') return null;
  if (typeof value === 'number' && !Number.isFinite(value)) return null;
  const s = String(value);
  if (s === 'undefined' || s === 'null' || s === 'NaN') return null;
  if (/^(404|409|410|500|502|503)$/.test(s.trim())) return null;
  return s;
}
assert(displayKpiText(404) === null, 'HTTP 404 must not render as KPI');
assert(displayKpiText(500) === null, 'HTTP 500 must not render as KPI');
assert(displayKpiText(undefined) === null, 'undefined KPI');
assert(displayKpiText(Number.NaN) === null, 'NaN KPI');
assert(displayKpiText('SIMULATED') === 'SIMULATED', 'demo label');

console.log('formatters unit tests passed');
