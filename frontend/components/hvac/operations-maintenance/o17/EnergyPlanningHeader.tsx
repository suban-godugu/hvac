'use client';

import { StatusBadge, toneForStatus } from '@/components/hvac/StatusBadge';
import type { OmDashboardData, OmOpportunity } from '@/lib/hvac/omTypes';
import type { PlatformGate } from '@/lib/hvac/o20Api';
import { StudioBreadcrumb } from '@/components/hvac/StudioBreadcrumb';
import { getOpportunity } from '@/lib/hvac/opportunityConfig';
import {
  O17_GUIDE_DESCRIPTION,
  isO17Simulation,
  o17Bms,
  o17ConfidencePct,
  o17Freshness,
  o17ImpactKw,
  o17Kw,
  o17Mode,
  o17PlanningPeriod,
  o17Safety,
  o17SecondsAgo,
  o17TelemetryBadge,
} from '@/lib/hvac/o17Format';
import { formatDash } from '@/lib/hvac/formatters';

function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

export function EnergyPlanningHeader({
  data,
  dash,
  buildingName,
  platform,
}: {
  data: OmOpportunity;
  dash?: OmDashboardData;
  buildingName?: string | null;
  platform?: PlatformGate | null;
}) {
  const sim = isO17Simulation(data);
  const bms = o17Bms(dash, data);
  const tel = o17TelemetryBadge(data);
  const fresh = o17Freshness(data);
  const safety = o17Safety(data);
  const mode = platform?.safeMode ? 'SAFE_MODE' : o17Mode(dash);
  const catalog = getOpportunity('O17');
  const description = data.description || catalog?.description || O17_GUIDE_DESCRIPTION;
  const ts = data.telemetry?.lastUpdated || data.timestamp || null;

  return (
    <header className="px-4 pt-4 pb-2 space-y-3">
      <StudioBreadcrumb def={catalog || getOpportunity('O17')!} />
      <div className="flex flex-col xl:flex-row xl:items-start xl:justify-between gap-4">
        <div>
          <div className="text-[11px] font-mono text-cyan-400">HVAC Fleet</div>
          <p className="text-[11px] font-mono text-slate-500 mt-0.5">Building {formatDash(buildingName)}</p>
        </div>
        <div className="flex flex-wrap gap-2 justify-end" aria-label="O17 system status">
          <StatusBadge tone={toneForStatus(bms)}>{`BMS ${bms}`}</StatusBadge>
          <StatusBadge tone={toneForStatus(tel)}>{`Telemetry ${tel}`}</StatusBadge>
          <StatusBadge tone="neutral">{`Mode ${mode}`}</StatusBadge>
          <StatusBadge tone={toneForStatus(safety)}>{`Safety ${safety}`}</StatusBadge>
          <StatusBadge tone={platform?.safeMode ? 'danger' : 'muted'}>{`SAFE MODE ${platform?.safeMode ? 'ON' : 'OFF'}`}</StatusBadge>
          <StatusBadge tone={toneForStatus(fresh)}>{`Freshness ${fresh}`}</StatusBadge>
          <StatusBadge tone={toneForStatus(data.status)}>{`Opportunity ${formatDash(data.status)}`}</StatusBadge>
        </div>
      </div>
      {sim ? (
        <div className="kpi-tile" role="status">
          <div className="text-[11px] uppercase tracking-wider font-semibold text-amber-300">SIMULATED DATA</div>
          <p className="text-[11px] text-slate-500 mt-1">Demo / simulation telemetry is never labeled LIVE. BMS writes are not implied.</p>
        </div>
      ) : null}
      <div className="kpi-tile">
        <div className="text-[11px] font-mono text-cyan-400">O17</div>
        <h1 className="text-xl font-semibold text-slate-100 tracking-tight mt-1">Energy Management Planning</h1>
        <p className="text-sm text-slate-400 mt-2 max-w-4xl leading-relaxed">{description}</p>
        <dl className="mt-4 grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3 text-[11px]">
          <div>
            <dt className="uppercase tracking-wider text-slate-500">Opportunity status</dt>
            <dd className="font-mono text-slate-200 mt-1">{formatDash(data.status)}</dd>
          </div>
          <div>
            <dt className="uppercase tracking-wider text-slate-500">Current recommendation</dt>
            <dd className="font-mono text-slate-200 mt-1">{formatDash(data.recommendation?.action)}</dd>
          </div>
          <div>
            <dt className="uppercase tracking-wider text-slate-500">Potential energy impact</dt>
            <dd className="font-mono text-slate-200 mt-1">{o17Kw(o17ImpactKw(data, dash))}</dd>
          </div>
          <div>
            <dt className="uppercase tracking-wider text-slate-500">Planning period</dt>
            <dd className="font-mono text-slate-200 mt-1">{o17PlanningPeriod(data)}</dd>
          </div>
          <div>
            <dt className="uppercase tracking-wider text-slate-500">Confidence</dt>
            <dd className="font-mono text-slate-200 mt-1">{o17ConfidencePct(data.recommendation?.confidence ?? data.confidence)}</dd>
          </div>
          <div>
            <dt className="uppercase tracking-wider text-slate-500">Last evaluation</dt>
            <dd className="font-mono text-slate-200 mt-1">{o17SecondsAgo(ts)}</dd>
          </div>
        </dl>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            className="btn-primary focus-visible:ring-2 focus-visible:ring-cyan-400"
            onClick={() => scrollTo('o17-recommendation')}
          >
            View Planning Recommendation
          </button>
          <button
            type="button"
            className="px-3 py-1.5 border border-white/15 text-xs text-slate-200 focus-visible:ring-2 focus-visible:ring-cyan-400"
            onClick={() => scrollTo('o17-engineering')}
          >
            View Engineering Details
          </button>
        </div>
      </div>
    </header>
  );
}
