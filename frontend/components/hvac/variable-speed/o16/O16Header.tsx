'use client';

import { StatusBadge, toneForStatus } from '@/components/hvac/StatusBadge';
import type { O16Dashboard, O16EquipmentRow } from '@/lib/hvac/o16Types';
import { bmsBadge, fmtDash, freshnessBadge, isSimulation, secondsAgo, telemetryBadge } from '@/lib/hvac/o16Format';
import { StudioBreadcrumb } from '@/components/hvac/StudioBreadcrumb';
import { getOpportunity } from '@/lib/hvac/opportunityConfig';

export function O16Header({
  data,
  equipment,
  selectedId,
  onSelect,
}: {
  data?: O16Dashboard | null;
  equipment: O16EquipmentRow[];
  selectedId: string | 'all';
  onSelect: (id: string | 'all') => void;
}) {
  const def = getOpportunity('O16')!;
  const sim = data ? isSimulation(data) : false;
  const bms = data ? bmsBadge(data) : 'OFFLINE';
  const tel = data ? telemetryBadge(data) : 'NO DATA';
  const fresh = data ? freshnessBadge(data) : 'NO DATA';
  const mode = data
    ? (data.header?.control_mode || data.config?.control_mode || 'ADVISORY').toUpperCase()
    : 'NO DATA';
  const safetyRaw = (data?.header?.safety || data?.safety_status || '').toUpperCase();
  const safety = safetyRaw || 'NO DATA';
  const building = data?.config?.building_id;
  return (
    <header className="px-4 pt-4 pb-2 space-y-3">
      <StudioBreadcrumb def={def} />
      <div className="flex flex-col xl:flex-row xl:items-start xl:justify-between gap-4">
        <div>
          <div className="text-[11px] font-mono text-cyan-400">O16</div>
          <h1 className="text-xl font-semibold text-slate-100 tracking-tight">{def.title}</h1>
          <p className="text-sm text-slate-400">{def.description}</p>
          <p className="text-[11px] font-mono text-slate-500 mt-1">Building {fmtDash(building)}</p>
        </div>
        <div className="flex flex-col items-stretch xl:items-end gap-2">
          <label className="text-[11px] font-mono text-slate-500">
            Condenser plant
            <select
              className="ml-2 bg-[#0c1220] border border-white/10 text-slate-200 px-2 py-1 focus-visible:ring-2 focus-visible:ring-cyan-400"
              aria-label="Condenser plant"
              value={selectedId}
              onChange={(e) => onSelect(e.target.value)}
            >
              <option value="all">All registered equipment</option>
              {equipment.map((e) => (
                <option key={e.equipment_id || e.name || ''} value={String(e.equipment_id || e.name)}>
                  {e.name || e.equipment_id}
                </option>
              ))}
            </select>
          </label>
          <div className="flex flex-wrap gap-2 justify-end" aria-label="O16 operating status">
            <StatusBadge tone={toneForStatus(bms)}>{`BMS ${bms}`}</StatusBadge>
            <StatusBadge tone={toneForStatus(tel)}>{`Telemetry ${tel}`}</StatusBadge>
            <StatusBadge tone={toneForStatus(fresh)}>{`Data ${fresh}`}</StatusBadge>
            <StatusBadge tone="neutral">{`Mode ${mode}`}</StatusBadge>
            <StatusBadge tone={toneForStatus(safety)}>{`Safety ${safety === 'REJECT' ? 'BLOCK' : safety}`}</StatusBadge>
            <StatusBadge tone={data?.header?.safe_mode || data?.safe_mode ? 'warn' : 'muted'}>
              SAFE MODE {data?.header?.safe_mode || data?.safe_mode ? 'ON' : 'OFF'}
            </StatusBadge>
            <StatusBadge tone="muted">Last update {secondsAgo(data?.header?.last_telemetry || data?.evaluated_at)}</StatusBadge>
          </div>
        </div>
      </div>
      {sim && (
        <div className="kpi-tile min-h-0 border-amber-500/40" role="status">
          <div className="text-[11px] font-semibold tracking-wider text-amber-300">BMS OFFLINE — SIMULATED TELEMETRY</div>
          <div className="text-[11px] text-slate-400 mt-1">Simulation is never LIVE. BMS writes are disabled.</div>
        </div>
      )}
    </header>
  );
}
