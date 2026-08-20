'use client';

import { Activity, AlertTriangle, GitBranch, Shield } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { OmOpportunity } from '@/lib/hvac/omTypes';
import { formatDash, formatPercent } from '@/lib/hvac/formatters';
import { o20Counts, o20QualityLabel, o20SecondsAgo } from '@/lib/hvac/o20Format';

function Card({
  label,
  value,
  unit,
  icon: Icon,
  timestamp,
}: {
  label: string;
  value: string;
  unit: string;
  icon: LucideIcon;
  timestamp: string;
}) {
  return (
    <article className="kpi-tile min-h-[104px]" aria-label={label}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] uppercase font-semibold text-slate-500 tracking-wider">{label}</span>
        <Icon className="w-3.5 h-3.5 text-slate-500" aria-hidden />
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-lg font-bold font-mono text-slate-100">{value}</span>
        <span className="text-[11px] font-mono text-slate-500">{unit}</span>
      </div>
      <div className="mt-2 text-[10px] font-mono text-slate-500">{timestamp}</div>
    </article>
  );
}

export function ControlSoftwareKPIGrid({ data }: { data: OmOpportunity }) {
  const ts = o20SecondsAgo(data.telemetry?.lastUpdated || data.timestamp);
  const c = o20Counts(data);
  const recs = data.recommendation?.action ? 1 : null;
  const items = [
    { label: 'Control Points', value: formatDash(c.points), unit: 'pts', icon: Activity },
    { label: 'Healthy Points', value: formatDash(c.healthy), unit: 'pts', icon: Shield },
    { label: 'Override Points', value: formatDash(c.overrides), unit: 'pts', icon: GitBranch },
    { label: 'Drifted Points', value: formatDash(c.drift), unit: 'pts', icon: AlertTriangle },
    { label: 'Stale Points', value: formatDash(c.stale), unit: 'pts', icon: AlertTriangle },
    { label: 'Failed Points', value: formatDash(c.failed), unit: 'pts', icon: AlertTriangle },
    { label: 'Control Health %', value: formatPercent(c.healthPct), unit: '', icon: Shield },
    { label: 'Software', value: formatDash(data.current?.softwareVersion), unit: '', icon: Activity },
    { label: 'Recommendations', value: recs == null ? '—' : String(recs), unit: 'items', icon: Activity },
  ];
  return (
    <section className="col-span-12" aria-label="Control software KPIs">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {items.map((item) => (
          <Card key={item.label} {...item} timestamp={`${o20QualityLabel(data)} · ${ts}`} />
        ))}
      </div>
    </section>
  );
}
