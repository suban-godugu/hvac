'use client';

import { Cpu } from 'lucide-react';
import { StatusBadge, toneForStatus } from '@/components/hvac/StatusBadge';
import type { OmDashboardData, OmOpportunity } from '@/lib/hvac/omTypes';
import type { PlatformGate } from '@/lib/hvac/o20Api';
import { StudioBreadcrumb } from '@/components/hvac/StudioBreadcrumb';
import { getOpportunity } from '@/lib/hvac/opportunityConfig';
import { formatDash } from '@/lib/hvac/formatters';
import {
  O20_GUIDE_DESCRIPTION,
  isO20Simulation,
  o20Bms,
  o20ControllerField,
  o20Freshness,
  o20Mode,
  o20QualityLabel,
  o20SecondsAgo,
  o20TelemetryBadge,
} from '@/lib/hvac/o20Format';

export function ControlSoftwareHeader({
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
  const catalog = getOpportunity('O20');
  const description = data.description || catalog?.description || O20_GUIDE_DESCRIPTION;
  const health = formatDash(data.current?.controllerHealth);
  const mode = platform?.safeMode ? 'SAFE_MODE' : o20Mode(dash);
  return (
    <header className="px-4 pt-4 pb-2 space-y-3">
      <StudioBreadcrumb def={catalog || getOpportunity('O20')!} />
      <div className="flex flex-col xl:flex-row xl:items-start xl:justify-between gap-4">
        <div>
          <div className="text-[11px] font-mono text-cyan-400 flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5" aria-hidden />
            HVAC Fleet
          </div>
          <p className="text-[11px] font-mono text-slate-500 mt-0.5">Building {formatDash(buildingName)}</p>
        </div>
        <div className="flex flex-wrap gap-2 justify-end" aria-label="O20 system status">
          <StatusBadge tone={toneForStatus(o20Bms(dash, data))}>{`BMS ${o20Bms(dash, data)}`}</StatusBadge>
          <StatusBadge tone={toneForStatus(o20TelemetryBadge(data))}>{`Telemetry ${o20TelemetryBadge(data)}`}</StatusBadge>
          <StatusBadge tone={toneForStatus(health)}>{`Control Health ${health}`}</StatusBadge>
          <StatusBadge tone="neutral">{`Mode ${mode}`}</StatusBadge>
          <StatusBadge tone={platform?.safeMode ? 'danger' : 'muted'}>{`SAFE MODE ${platform?.safeMode ? 'ON' : 'OFF'}`}</StatusBadge>
          <StatusBadge tone={toneForStatus(data.safety?.status)}>{`Safety ${formatDash(data.safety?.status)}`}</StatusBadge>
          <StatusBadge tone={toneForStatus(o20Freshness(data))}>{`Freshness ${o20Freshness(data)}`}</StatusBadge>
        </div>
      </div>
      {isO20Simulation(data) ? (
        <div className="kpi-tile" role="status">
          <div className="text-[11px] uppercase tracking-wider font-semibold text-amber-300">SIMULATED</div>
          <p className="text-[11px] text-slate-500 mt-1">Demo / simulation is never LIVE. Automatic software deploy is prohibited.</p>
        </div>
      ) : null}
      <div className="kpi-tile">
        <div className="text-[11px] font-mono text-cyan-400">O20</div>
        <h1 className="text-xl font-semibold text-slate-100 tracking-tight mt-1">Management of System Control Software</h1>
        <p className="text-sm text-slate-400 mt-2 max-w-4xl leading-relaxed">{description}</p>
        <dl className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px] font-mono text-slate-500">
          <div>Controller {o20ControllerField(data, 'controller_id')}</div>
          <div>Software {formatDash(data.current?.softwareVersion)}</div>
          <div>Quality {o20QualityLabel(data)}</div>
          <div>Evaluated {o20SecondsAgo(data.telemetry?.lastUpdated || data.timestamp)}</div>
        </dl>
      </div>
    </header>
  );
}
