'use client';

import { formatPercent } from '@/lib/hvac/formatters';
import { o10Num, o10Str, o10Temp, o10VisualMode } from '@/lib/hvac/o10Format';
import type { VentilationOpportunity } from '@/lib/hvac/ventilationTypes';

function Node({ title, value }: { title: string; value: string }) {
  return (
    <div className="border border-cyan-500/20 bg-[#0a101c] px-3 py-2 min-w-[7.5rem] text-center">
      <div className="text-[10px] uppercase tracking-wider text-slate-500">{title}</div>
      <div className="text-[11px] font-mono text-cyan-200 mt-1">{value}</div>
    </div>
  );
}

export function O10AhuDiagram({ data }: { data: VentilationOpportunity }) {
  const vis = o10VisualMode(data);
  const oa = formatPercent(data.current?.damperPct);
  const ra = formatPercent(o10Num(data, 'return_damper_pct'));
  const relief = formatPercent(o10Num(data, 'relief_damper_pct'));
  const cooling = o10Str(data, 'mechanical_cooling_stage', 'cooling_valve_percent', 'cooling_call');
  return (
    <section className="col-span-12 kpi-tile space-y-3" aria-label="AHU airflow diagram">
      <h2 className="text-[11px] uppercase tracking-wider text-slate-500">AHU airflow sequence</h2>
      <p className="text-[11px] text-slate-500">Conceptual sequence (guide Figure 12). Damper percentages shown only when telemetry exists.</p>
      <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono text-slate-400">
        <Node title="Outdoor air" value={vis} />
        <span>↓</span>
        <Node title="OA damper" value={oa} />
        <span>↓</span>
        <Node title="Mixed air" value={o10Temp(data, 'mixed_air_temp_c')} />
        <span>↓</span>
        <Node title="Cooling coil" value={cooling} />
        <span>↓</span>
        <Node title="Supply fan" value={o10Str(data, 'fan_status', 'fan_state')} />
        <span>↓</span>
        <Node title="Space" value="—" />
      </div>
      <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono text-slate-400">
        <Node title="Space" value="—" />
        <span>↓</span>
        <Node title="Return air" value="—" />
        <span>↓</span>
        <Node title="Return damper" value={ra} />
        <span>↓</span>
        <Node title="Relief / exhaust" value={relief} />
      </div>
    </section>
  );
}
