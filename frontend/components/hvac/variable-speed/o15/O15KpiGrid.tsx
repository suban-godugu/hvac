'use client';

import { KPIGrid } from '@/components/hvac/KPIGrid';
import type { O15Dashboard } from '@/lib/hvac/o15Types';
import type { O15HistoryPoint } from '@/lib/hvac/o15Types';
import { confidencePct, fmtDash, fmtUnit, numericTrend } from '@/lib/hvac/o15Format';

export function O15KpiGrid({ data, history }: { data: O15Dashboard; history: O15HistoryPoint[] }) {
  const cs = data.current_state || {};
  const os = data.optimized_state || {};
  const prev = history.length >= 2 ? history[history.length - 2]?.head_pressure : null;
  const current = cs.head_pressure;
  const recommended = os.recommended_head_pressure;
  const delta =
    current != null && recommended != null && Number.isFinite(Number(current)) && Number.isFinite(Number(recommended))
      ? Number(recommended) - Number(current)
      : null;
  const conf = confidencePct(data.confidence);
  const items = [
    {
      label: 'Current Head Pressure',
      value: current == null ? null : fmtDash(current),
      detail: `Current operating value  ${numericTrend(current, prev)}`,
    },
    {
      label: 'Target Head Pressure',
      value: cs.head_pressure_setpoint == null ? null : fmtDash(cs.head_pressure_setpoint),
      detail: 'Current control target',
    },
    {
      label: 'Recommended Target',
      value: recommended == null ? null : fmtDash(recommended),
      detail: 'O15 optimization recommendation',
    },
    {
      label: 'Head Pressure Delta',
      value: delta == null ? null : `${delta > 0 ? '+' : ''}${fmtDash(delta)}`,
      detail: 'Current vs recommended',
    },
    {
      label: 'Outdoor Air Temp',
      value: cs.outdoor_temperature_c == null ? null : fmtUnit(cs.outdoor_temperature_c, '°C'),
      detail: 'Condenser ambient condition',
    },
    {
      label: 'Condenser Approach',
      value: cs.observed_approach_c == null ? null : fmtUnit(cs.observed_approach_c, '°C'),
      detail: 'Current approach',
    },
    {
      label: 'Condenser Fan Power',
      value: cs.fan_power_kw == null ? null : fmtUnit(cs.fan_power_kw, 'kW'),
      detail: 'Current fan consumption',
    },
    {
      label: 'Optimization Confidence',
      value: conf === 'NO DATA' ? null : conf,
      detail: 'Recommendation confidence',
    },
  ];
  return (
    <div className="col-span-12">
      <KPIGrid emptyText="NO DATA" className="grid grid-cols-2 md:grid-cols-4 gap-3" items={items} />
    </div>
  );
}
