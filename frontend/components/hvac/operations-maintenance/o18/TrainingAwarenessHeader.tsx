'use client';

import { GraduationCap } from 'lucide-react';
import { StatusBadge, toneForStatus } from '@/components/hvac/StatusBadge';
import type { OmDashboardData, OmOpportunity } from '@/lib/hvac/omTypes';
import type { PlatformGate } from '@/lib/hvac/o20Api';
import { StudioBreadcrumb } from '@/components/hvac/StudioBreadcrumb';
import { getOpportunity } from '@/lib/hvac/opportunityConfig';
import { formatDash, formatPercent } from '@/lib/hvac/formatters';
import {
  O18_GUIDE_DESCRIPTION,
  isO18Simulation,
  o18Affected,
  o18Bms,
  o18Coverage,
  o18Freshness,
  o18Mode,
  o18SecondsAgo,
  o18TelemetryBadge,
} from '@/lib/hvac/o18Format';

export function TrainingAwarenessHeader({
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
  const sim = isO18Simulation(data);
  const catalog = getOpportunity('O18');
  const description = data.description || catalog?.description || O18_GUIDE_DESCRIPTION;
  const ts = data.telemetry?.lastUpdated || data.timestamp;

  return (
    <header className="px-4 pt-4 pb-2 space-y-3">
      <StudioBreadcrumb def={catalog || getOpportunity('O18')!} />
      <div className="flex flex-col xl:flex-row xl:items-start xl:justify-between gap-4">
        <div>
          <div className="text-[11px] font-mono text-cyan-400 flex items-center gap-1.5">
            <GraduationCap className="w-3.5 h-3.5" aria-hidden />
            HVAC Fleet
          </div>
          <p className="text-[11px] font-mono text-slate-500 mt-0.5">Building {formatDash(buildingName)}</p>
        </div>
        <div className="flex flex-wrap gap-2 justify-end" aria-label="O18 system status">
          <StatusBadge tone={toneForStatus(o18Bms(dash, data))}>{`BMS ${o18Bms(dash, data)}`}</StatusBadge>
          <StatusBadge tone={toneForStatus(o18TelemetryBadge(data))}>{`Telemetry ${o18TelemetryBadge(data)}`}</StatusBadge>
          <StatusBadge tone="neutral">{`Mode ${platform?.safeMode ? 'SAFE_MODE' : o18Mode(dash)}`}</StatusBadge>
          <StatusBadge tone={platform?.safeMode ? 'danger' : 'muted'}>{`SAFE MODE ${platform?.safeMode ? 'ON' : 'OFF'}`}</StatusBadge>
          <StatusBadge tone={toneForStatus(data.safety?.status)}>{`Safety ${formatDash(data.safety?.status)}`}</StatusBadge>
          <StatusBadge tone={toneForStatus(o18Freshness(data))}>{`Freshness ${o18Freshness(data)}`}</StatusBadge>
          <StatusBadge tone={toneForStatus(data.status)}>{`Opportunity ${formatDash(data.status)}`}</StatusBadge>
        </div>
      </div>
      {sim ? (
        <div className="kpi-tile" role="status">
          <div className="text-[11px] uppercase tracking-wider font-semibold text-amber-300">SIMULATED</div>
          <p className="text-[11px] text-slate-500 mt-1">Demo / simulation records are never labeled LIVE. This page does not dispatch HVAC equipment.</p>
        </div>
      ) : null}
      <div className="kpi-tile">
        <div className="text-[11px] font-mono text-cyan-400">O18</div>
        <h1 className="text-xl font-semibold text-slate-100 tracking-tight mt-1">Energy Management Training &amp; Awareness</h1>
        <p className="text-sm text-slate-400 mt-2 max-w-4xl leading-relaxed">{description}</p>
        <dl className="mt-4 grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3 text-[11px]">
          <div>
            <dt className="uppercase tracking-wider text-slate-500">Training Status</dt>
            <dd className="font-mono text-slate-200 mt-1">{formatDash(data.current?.operatorReadiness || data.status)}</dd>
          </div>
          <div>
            <dt className="uppercase tracking-wider text-slate-500">Completion</dt>
            <dd className="font-mono text-slate-200 mt-1">{formatPercent(o18Coverage(data))}</dd>
          </div>
          <div>
            <dt className="uppercase tracking-wider text-slate-500">Affected Users</dt>
            <dd className="font-mono text-slate-200 mt-1">{formatDash(o18Affected(data))}</dd>
          </div>
          <div>
            <dt className="uppercase tracking-wider text-slate-500">Training items</dt>
            <dd className="font-mono text-slate-200 mt-1">{formatDash(data.current?.trainingItems)}</dd>
          </div>
          <div>
            <dt className="uppercase tracking-wider text-slate-500">Last Evaluation</dt>
            <dd className="font-mono text-slate-200 mt-1">{o18SecondsAgo(ts)}</dd>
          </div>
          <div>
            <dt className="uppercase tracking-wider text-slate-500">Recommendation Status</dt>
            <dd className="font-mono text-slate-200 mt-1">{formatDash(data.recommendation?.action)}</dd>
          </div>
        </dl>
        <div className="mt-4">
          <button
            type="button"
            className="btn-primary focus-visible:ring-2 focus-visible:ring-cyan-400"
            onClick={() => document.getElementById('o18-recommendations')?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
          >
            View Training Recommendations
          </button>
        </div>
      </div>
    </header>
  );
}
