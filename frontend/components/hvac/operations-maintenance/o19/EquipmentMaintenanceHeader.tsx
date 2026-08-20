'use client';

import { Wrench } from 'lucide-react';
import { StatusBadge, toneForStatus } from '@/components/hvac/StatusBadge';
import type { OmDashboardData, OmOpportunity } from '@/lib/hvac/omTypes';
import type { PlatformGate } from '@/lib/hvac/o20Api';
import { StudioBreadcrumb } from '@/components/hvac/StudioBreadcrumb';
import { getOpportunity } from '@/lib/hvac/opportunityConfig';
import { formatDash, formatPercent, formatKw } from '@/lib/hvac/formatters';
import {
  O19_GUIDE_DESCRIPTION,
  isO19Simulation,
  o19Bms,
  o19FleetStatus,
  o19Freshness,
  o19Mode,
  o19QualityLabel,
  o19SecondsAgo,
  o19TelemetryBadge,
} from '@/lib/hvac/o19Format';

export function EquipmentMaintenanceHeader({
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
  const fleet = o19FleetStatus(data);
  const catalog = getOpportunity('O19');
  const description = data.description || catalog?.description || O19_GUIDE_DESCRIPTION;
  const mode = platform?.safeMode ? 'SAFE_MODE' : o19Mode(dash);
  return (
    <header className="px-4 pt-4 pb-2 space-y-3">
      <StudioBreadcrumb def={catalog || getOpportunity('O19')!} />
      <div className="flex flex-col xl:flex-row xl:items-start xl:justify-between gap-4">
        <div>
          <div className="text-[11px] font-mono text-cyan-400 flex items-center gap-1.5">
            <Wrench className="w-3.5 h-3.5" aria-hidden />
            HVAC Fleet
          </div>
          <p className="text-[11px] font-mono text-slate-500 mt-0.5">Building {formatDash(buildingName)}</p>
        </div>
        <div className="flex flex-wrap gap-2 justify-end" aria-label="O19 system status">
          <StatusBadge tone={toneForStatus(o19Bms(dash, data))}>{`BMS ${o19Bms(dash, data)}`}</StatusBadge>
          <StatusBadge tone={toneForStatus(o19TelemetryBadge(data))}>{`Telemetry ${o19TelemetryBadge(data)}`}</StatusBadge>
          <StatusBadge tone="neutral">{`Mode ${mode}`}</StatusBadge>
          <StatusBadge tone={platform?.safeMode ? 'danger' : 'muted'}>{`SAFE MODE ${platform?.safeMode ? 'ON' : 'OFF'}`}</StatusBadge>
          <StatusBadge tone={toneForStatus(data.safety?.status)}>{`Safety ${formatDash(data.safety?.status)}`}</StatusBadge>
          <StatusBadge tone={toneForStatus(o19Freshness(data))}>{`Freshness ${o19Freshness(data)}`}</StatusBadge>
          <StatusBadge tone={toneForStatus(o19QualityLabel(data))}>{`Quality ${o19QualityLabel(data)}`}</StatusBadge>
        </div>
      </div>
      {isO19Simulation(data) ? (
        <div className="kpi-tile" role="status">
          <div className="text-[11px] uppercase tracking-wider font-semibold text-amber-300">SIMULATED</div>
          <p className="text-[11px] text-slate-500 mt-1">Demo / simulation records are never labeled LIVE. This page does not write HVAC setpoints.</p>
        </div>
      ) : null}
      <div className="kpi-tile">
        <div className="text-[11px] font-mono text-cyan-400">O19</div>
        <h1 className="text-xl font-semibold text-slate-100 tracking-tight mt-1">Energy Efficiency Maintenance</h1>
        <p className="text-sm text-slate-400 mt-2 max-w-4xl leading-relaxed">{description}</p>
        <div className="mt-3">
          <StatusBadge tone={toneForStatus(fleet)}>{fleet}</StatusBadge>
        </div>
        <dl className="mt-4 grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3 text-[11px]">
          <div>
            <dt className="uppercase tracking-wider text-slate-500">Equipment health</dt>
            <dd className="font-mono text-slate-200 mt-1">{formatPercent(data.current?.equipmentHealthPct)}</dd>
          </div>
          <div>
            <dt className="uppercase tracking-wider text-slate-500">Assets at risk</dt>
            <dd className="font-mono text-slate-200 mt-1">{formatDash(data.current?.assetsAtRisk)}</dd>
          </div>
          <div>
            <dt className="uppercase tracking-wider text-slate-500">Findings</dt>
            <dd className="font-mono text-slate-200 mt-1">{formatDash(data.current?.maintenanceAlerts)}</dd>
          </div>
          <div>
            <dt className="uppercase tracking-wider text-slate-500">Energy loss</dt>
            <dd className="font-mono text-slate-200 mt-1">{formatKw(data.energy?.impactKw)}</dd>
          </div>
          <div>
            <dt className="uppercase tracking-wider text-slate-500">Recommendation</dt>
            <dd className="font-mono text-slate-200 mt-1">{formatDash(data.recommendation?.action)}</dd>
          </div>
          <div>
            <dt className="uppercase tracking-wider text-slate-500">Last evaluation</dt>
            <dd className="font-mono text-slate-200 mt-1">{o19SecondsAgo(data.telemetry?.lastUpdated || data.timestamp)}</dd>
          </div>
        </dl>
      </div>
    </header>
  );
}
