'use client';

import { StatusBadge, toneForStatus } from '@/components/hvac/StatusBadge';
import { StudioBreadcrumb } from '@/components/hvac/StudioBreadcrumb';
import { getOpportunity } from '@/lib/hvac/opportunityConfig';
import type { PlatformGate } from '@/lib/hvac/o20Api';
import { formatAgeSeconds, formatDash, formatPercent } from '@/lib/hvac/formatters';
import { o10Enth, o10Provenance, o10Str, o10Temp, o10VisualMode } from '@/lib/hvac/o10Format';
import type { VentilationDashboardData, VentilationOpportunity } from '@/lib/hvac/ventilationTypes';

export function O10Header({
  data,
  dash,
  platform,
}: {
  data: VentilationOpportunity;
  dash?: VentilationDashboardData | null;
  platform?: PlatformGate | null;
}) {
  const def = getOpportunity('O10')!;
  const prov = o10Provenance(data);
  const bms = prov === 'LIVE' ? 'CONNECTED' : 'OFFLINE';
  const safety = formatDash(data.safety?.status || platform?.safety);
  const mode = platform?.safeMode ? 'SAFE_MODE' : formatDash(dash?.module?.mode || platform?.mode);
  const description = data.description || def.description;
  return (
    <header className="px-4 pt-4 pb-2 space-y-3">
      <StudioBreadcrumb def={def} />
      <div className="flex flex-col xl:flex-row xl:items-start xl:justify-between gap-4">
        <div>
          <div className="text-[11px] font-mono text-cyan-400">HVAC Fleet</div>
          <p className="text-[11px] font-mono text-slate-500 mt-0.5">Building {formatDash(platform?.buildingName)}</p>
        </div>
        <div className="flex flex-wrap gap-2 justify-end" aria-label="O10 system status">
          <StatusBadge tone={toneForStatus(bms)}>{`BMS ${bms}`}</StatusBadge>
          <StatusBadge tone={toneForStatus(prov)}>{`Telemetry ${prov}`}</StatusBadge>
          <StatusBadge tone="neutral">{`Mode ${mode}`}</StatusBadge>
          <StatusBadge tone={platform?.safeMode ? 'danger' : 'muted'}>{`SAFE MODE ${platform?.safeMode ? 'ON' : 'OFF'}`}</StatusBadge>
          <StatusBadge tone={toneForStatus(safety)}>{`Safety ${safety}`}</StatusBadge>
          <StatusBadge tone={toneForStatus(data.status)}>{`Opportunity ${formatDash(data.status)}`}</StatusBadge>
          <StatusBadge tone="muted">
            {data.telemetry?.ageSeconds != null ? `TEL ${formatAgeSeconds(data.telemetry.ageSeconds)}` : 'TEL —'}
          </StatusBadge>
        </div>
      </div>
      {prov === 'SIMULATED' ? (
        <div className="kpi-tile" role="status">
          <div className="text-[11px] uppercase tracking-wider font-semibold text-amber-300">SIMULATED DATA</div>
          <p className="text-[11px] text-slate-500 mt-1">Demo / simulation telemetry is never labeled LIVE. BMS writes are not implied.</p>
        </div>
      ) : null}
      <div className="kpi-tile">
        <div className="text-[11px] font-mono text-cyan-400">O10</div>
        <h1 className="text-xl font-semibold text-slate-100 tracking-tight mt-1">Economy Cycle</h1>
        <p className="text-sm text-slate-400 mt-2 max-w-4xl leading-relaxed">{description}</p>
        <dl className="mt-4 grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3 text-[11px]">
          <div>
            <dt className="uppercase tracking-wider text-slate-500">Economy mode</dt>
            <dd className="font-mono text-slate-200 mt-1">{o10VisualMode(data)}</dd>
          </div>
          <div>
            <dt className="uppercase tracking-wider text-slate-500">OA damper</dt>
            <dd className="font-mono text-slate-200 mt-1">{formatPercent(data.current?.damperPct)}</dd>
          </div>
          <div>
            <dt className="uppercase tracking-wider text-slate-500">Recommended damper</dt>
            <dd className="font-mono text-slate-200 mt-1">{formatPercent(data.optimized?.damperPct)}</dd>
          </div>
          <div>
            <dt className="uppercase tracking-wider text-slate-500">Outdoor enthalpy</dt>
            <dd className="font-mono text-slate-200 mt-1">{o10Enth(data, 'outdoor_enthalpy_kj_kg', 'outdoor_enthalpy_kjkg')}</dd>
          </div>
          <div>
            <dt className="uppercase tracking-wider text-slate-500">Outdoor temperature</dt>
            <dd className="font-mono text-slate-200 mt-1">{o10Temp(data, 'outdoor_drybulb_c', 'outdoor_temp_c')}</dd>
          </div>
          <div>
            <dt className="uppercase tracking-wider text-slate-500">Economizer</dt>
            <dd className="font-mono text-slate-200 mt-1">{o10Str(data, 'economizer_status')}</dd>
          </div>
        </dl>
      </div>
    </header>
  );
}
