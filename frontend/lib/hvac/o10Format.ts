import type { PlatformGate } from '@/lib/hvac/o20Api';
import { formatDash, formatEnthalpy, formatPercent, formatTemperature } from '@/lib/hvac/formatters';
import { provenanceFromAgent, type ProvenanceLabel } from '@/lib/hvac/provenance';
import type { VentilationOpportunity } from '@/lib/hvac/ventilationTypes';
import { metricNum, metricStr } from '@/lib/hvac/ventilationTypes';

export const O10_GUIDE = {
  source: '150317hvacguide.pdf — Opportunity 10 Economy cycle',
  compressorPotential: 'Up to 20% compressor energy reduction under suitable conditions',
  outdoorTempC: '10–20°C',
  outdoorEnthalpyKjkg: '< 52 kJ/kg',
  dewPointC: '< 12°C',
  enthalpyMarginKjkg: '≥ 10 kJ/kg below return-air enthalpy',
} as const;

export function o10Provenance(data: VentilationOpportunity | null | undefined): ProvenanceLabel {
  if (!data) return 'NO DATA';
  return provenanceFromAgent({
    ...data,
    bmsConnected: data.bmsConnected,
    source: data.source || data.telemetry?.source,
    quality: data.telemetry?.quality,
    classified: data.classified || data.telemetry?.state,
    telemetry_age_seconds: data.telemetry?.ageSeconds,
  } as Record<string, unknown>);
}

const O10_ALIASES: Record<string, string[]> = {
  outdoor_drybulb_c: ['outdoor_temp_c'],
  outdoor_temp_c: ['outdoor_drybulb_c'],
  return_drybulb_c: ['return_temp_c'],
  return_temp_c: ['return_drybulb_c'],
  outdoor_enthalpy_kj_kg: ['outdoor_enthalpy_kjkg'],
  outdoor_enthalpy_kjkg: ['outdoor_enthalpy_kj_kg'],
  return_enthalpy_kj_kg: ['return_enthalpy_kjkg'],
  return_enthalpy_kjkg: ['return_enthalpy_kj_kg'],
  outdoor_rh_pct: ['outdoor_rh_percent'],
  outdoor_rh_percent: ['outdoor_rh_pct'],
  return_rh_pct: ['return_rh_percent'],
  return_rh_percent: ['return_rh_pct'],
  oa_damper_pct: ['damper_percent', 'current_value'],
  damper_percent: ['oa_damper_pct', 'current_value'],
  mixed_air_temp_c: ['mixed_air_temperature_c'],
  supply_air_temp_c: ['supply_air_temperature_c'],
};

function o10Bags(data: VentilationOpportunity | null | undefined): Array<Record<string, unknown>> {
  const m = data?.metrics;
  if (!m) return [];
  const bags: Array<Record<string, unknown>> = [m];
  const nest = [m.current, m.optimized, m.current_state, m.optimized_state];
  for (const n of nest) {
    if (n && typeof n === 'object' && !Array.isArray(n)) {
      const rec = n as Record<string, unknown>;
      bags.push(rec);
      if (rec.values && typeof rec.values === 'object' && !Array.isArray(rec.values)) {
        bags.push(rec.values as Record<string, unknown>);
      }
    }
  }
  return bags;
}

function o10LookupKeys(keys: string[]): string[] {
  const out: string[] = [];
  for (const k of keys) {
    out.push(k);
    for (const a of O10_ALIASES[k] || []) out.push(a);
  }
  return out;
}

export function o10Num(data: VentilationOpportunity, ...keys: string[]): number | null {
  for (const bag of o10Bags(data)) {
    for (const k of o10LookupKeys(keys)) {
      const m = metricNum(bag, k);
      if (m != null) return m;
    }
  }
  return null;
}

export function o10Str(data: VentilationOpportunity, ...keys: string[]): string {
  for (const bag of o10Bags(data)) {
    for (const k of o10LookupKeys(keys)) {
      const s = metricStr(bag, k);
      if (s) return s;
    }
  }
  return '—';
}

export function o10EconomizerMode(data: VentilationOpportunity): string {
  return o10Str(data, 'economizer_status', 'economy_cycle_mode', 'visual_mode');
}

/** Map engine economizer_status onto the requested visual state machine. */
export function o10VisualMode(data: VentilationOpportunity): string {
  const raw = o10EconomizerMode(data).toUpperCase();
  if (raw === '—') return 'WAITING FOR DATA';
  if (raw.includes('LOCK') || (data.safety?.status || '').toUpperCase() === 'BLOCKED') return 'LOCKED OUT';
  if (raw.includes('100%') || raw.includes('FREE_COOLING')) return 'ECONOMY ACTIVE';
  if (raw.includes('INTEGRATED') || raw.includes('PARTIAL')) return 'ECONOMY + MECHANICAL COOLING';
  if (raw.includes('MINIMUM') || raw.includes('CLAMP')) return 'MINIMUM OUTDOOR AIR';
  if (raw.includes('ENABLE')) return 'ECONOMY ENABLED';
  if (raw.includes('OFF')) return 'OFF';
  return raw;
}

export function o10CycleStatus(data: VentilationOpportunity, prov: ProvenanceLabel): { status: string; reason: string } {
  if (prov === 'SIMULATED') {
    return { status: 'SIMULATED', reason: 'Telemetry source is simulation. Simulation is never LIVE.' };
  }
  if (prov === 'BMS OFFLINE') {
    return { status: 'BMS OFFLINE', reason: 'Production BMS is not connected. No BMS command will be issued.' };
  }
  if (prov === 'STALE') {
    return { status: 'WAITING FOR DATA', reason: 'Telemetry is stale. Economy-cycle writes are held.' };
  }
  if (prov === 'NO DATA') {
    return { status: 'WAITING FOR DATA', reason: 'Required outdoor/return/damper measurements are not qualified.' };
  }
  const vis = o10VisualMode(data);
  const rationale = formatDash(data.recommendation?.rationale || data.supervisory?.reason);
  if (vis === 'LOCKED OUT') return { status: 'LOCKED OUT', reason: rationale === '—' ? 'Economy cycle is locked out by safety or freeze guardrail.' : rationale };
  if (vis === 'ECONOMY ACTIVE') return { status: 'ACTIVE', reason: rationale };
  if (vis === 'ECONOMY + MECHANICAL COOLING' || vis === 'ECONOMY ENABLED') {
    return { status: 'ELIGIBLE', reason: rationale === '—' ? 'Outdoor air conditions are favorable for economy-cycle cooling.' : rationale };
  }
  if (vis === 'MINIMUM OUTDOOR AIR') {
    return { status: 'INELIGIBLE', reason: rationale === '—' ? 'Outdoor-air enthalpy is not favorable compared with return air.' : rationale };
  }
  return { status: formatDash(data.status), reason: rationale };
}

function triFromAdvantage(adv: number | null, needPositive: boolean): string {
  if (adv == null) return 'UNKNOWN';
  return (needPositive ? adv > 0 : adv < 0) ? 'PASS' : 'FAIL';
}

export function o10Eligibility(data: VentilationOpportunity, prov: ProvenanceLabel, platform?: PlatformGate | null) {
  const oat = o10Num(data, 'outdoor_drybulb_c', 'outdoor_temp_c');
  const rat = o10Num(data, 'return_drybulb_c', 'return_temp_c');
  const adv = o10Num(data, 'enthalpy_advantage_kj_kg');
  const oatGuide = oat == null ? 'UNKNOWN' : oat >= 10 && oat <= 20 ? 'PASS' : 'FAIL';
  const oatVsReturn = oat == null || rat == null ? 'UNKNOWN' : oat < rat ? 'PASS' : 'FAIL';
  const dew = o10Num(data, 'outdoor_dew_point_c', 'oa_dew_point_c');
  const dewCrit = dew == null ? 'UNKNOWN' : dew < 12 ? 'PASS' : 'FAIL';
  const cooling = o10Str(data, 'cooling_call', 'cooling_demand');
  const coolingCrit = cooling === '—' ? 'UNKNOWN' : /TRUE|ON|YES|1|CALL/i.test(cooling) ? 'PASS' : 'FAIL';
  const fire = o10Str(data, 'fire_mode', 'fire_alarm');
  const fireCrit = fire === '—' ? 'UNKNOWN' : /TRUE|ON|ALARM|ACTIVE/i.test(fire) ? 'LOCKED OUT' : 'CLEAR';
  const bms = prov === 'LIVE' ? 'CONNECTED' : 'OFFLINE';
  const q = (data.telemetry?.quality || '').toUpperCase();
  let telQ = 'MISSING';
  if (prov === 'STALE') telQ = 'STALE';
  else if (q === 'BAD') telQ = 'BAD';
  else if (q === 'GOOD' && (prov === 'LIVE' || prov === 'SIMULATED')) telQ = 'GOOD';
  else if (q) telQ = q;
  return [
    { id: 'cooling', label: 'CALL FOR COOLING', value: coolingCrit },
    { id: 'enthalpy', label: 'OUTDOOR ENTHALPY < RETURN ENTHALPY', value: triFromAdvantage(adv, true) },
    { id: 'oat_limit', label: 'OUTDOOR TEMPERATURE WITHIN LIMIT', value: oatGuide },
    { id: 'return', label: 'RETURN / SPACE CONDITIONS WITHIN LIMIT', value: oatVsReturn },
    { id: 'dew', label: 'DEW POINT / HUMIDITY CONDITION', value: dewCrit },
    { id: 'fire', label: 'FIRE MODE', value: fireCrit },
    { id: 'bms', label: 'BMS CONNECTIVITY', value: bms },
    { id: 'quality', label: 'TELEMETRY QUALITY', value: telQ },
    { id: 'safe', label: 'SAFE MODE', value: platform?.safeMode ? 'ON' : 'OFF' },
  ];
}

export function o10RecommendationLabel(data: VentilationOpportunity, prov: ProvenanceLabel): string {
  if (prov === 'NO DATA' || prov === 'STALE') return 'WAIT FOR TELEMETRY';
  const vis = o10VisualMode(data);
  if (vis === 'LOCKED OUT') return 'LOCK OUT';
  const act = (data.recommendation?.action || '').toUpperCase();
  if (act === 'INCREASE_OA' || act === 'ENABLE') return 'ENABLE ECONOMY CYCLE';
  if (act === 'TRIM_OA' || act === 'DISABLE') return 'DISABLE ECONOMY CYCLE';
  if (act === 'HOLD' || act === 'MAINTAIN_BASELINE') return 'MAINTAIN CURRENT STATE';
  if (act.includes('SENSOR') || act.includes('QUALITY')) return 'REVIEW SENSOR QUALITY';
  return formatDash(data.recommendation?.action);
}

export function o10CanApply(data: VentilationOpportunity, prov: ProvenanceLabel, platform?: PlatformGate | null): boolean {
  if (platform?.safeMode) return false;
  if (prov !== 'LIVE') return false;
  if (!data.dispatch?.eligible) return false;
  if ((data.safety?.status || '').toUpperCase() === 'FAIL' || data.safety?.passed === false) return false;
  const fire = o10Str(data, 'fire_mode', 'fire_alarm');
  if (fire !== '—' && /TRUE|ON|ALARM|ACTIVE/i.test(fire)) return false;
  return true;
}

export function o10ApplyBlock(data: VentilationOpportunity, prov: ProvenanceLabel, platform?: PlatformGate | null): string {
  if (platform?.safeMode) return 'SAFE_MODE';
  if (prov === 'SIMULATED') return 'SIMULATION_BLOCKED';
  if (prov === 'STALE') return 'STALE';
  if (prov === 'BMS OFFLINE') return 'BMS_OFFLINE';
  if (prov === 'NO DATA') return 'WAIT_FOR_TELEMETRY';
  const fire = o10Str(data, 'fire_mode', 'fire_alarm');
  if (fire !== '—' && /TRUE|ON|ALARM|ACTIVE/i.test(fire)) return 'FIRE_MODE';
  if (data.dispatch?.blockCode) return String(data.dispatch.blockCode);
  if (data.dispatch?.blockReason) return String(data.dispatch.blockReason);
  if (!data.dispatch?.eligible) return 'DISPATCH BLOCKED';
  return 'APPLY requires LIVE BMS, GOOD telemetry, safety PASS, and evaluate_dispatch.';
}

export function o10Temp(data: VentilationOpportunity, ...keys: string[]): string {
  return formatTemperature(o10Num(data, ...keys));
}

export function o10Enth(data: VentilationOpportunity, ...keys: string[]): string {
  return formatEnthalpy(o10Num(data, ...keys));
}

export function o10Pct(data: VentilationOpportunity, fallback: number | null, ...keys: string[]): string {
  const n = o10Num(data, ...keys);
  return formatPercent(n ?? fallback);
}

export function o10EngineLimit(data: VentilationOpportunity, key: string, guide: string): { guide: string; configured: string } {
  return { guide, configured: o10Str(data, key) };
}

export { formatDash };
