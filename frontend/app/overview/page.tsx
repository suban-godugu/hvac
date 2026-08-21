'use client';

import React from 'react';
import Link from 'next/link';
import { PageHeader } from '@/components/ui/PageHeader';
import { KPIGrid } from '@/components/hvac/KPIGrid';
import { OpportunityCard } from '@/components/hvac/OpportunityCard';
import { StatusBadge } from '@/components/hvac/StatusBadge';
import { EmptyState } from '@/components/hvac/EmptyState';
import {
  HVAC_SECTIONS,
  fleetOpportunityCards,
  type HvacSectionId,
} from '@/lib/hvac/opportunityConfig';
import {
  LayoutDashboard,
  CalendarClock,
  Gauge,
  Wind,
  Zap,
  Wrench,
  Activity,
  ShieldCheck,
  ArrowRight,
  Server,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { LIVE_POLL_MS, PLATFORM_POLL_MS } from '@/lib/hvac/poll';
import { fetchSchedulingDashboard, fetchStatus } from '@/lib/api';
import { hvacFetch } from '@/lib/api/client';
import { fetchPlantControlDashboard } from '@/lib/plantControlApi';
import { fetchVentilationDashboard } from '@/lib/hvac/ventilationApi';
import { fetchO14Dashboard } from '@/lib/hvac/o14Api';
import { fetchO15Dashboard } from '@/lib/hvac/o15Api';
import { fetchO16Dashboard } from '@/lib/hvac/o16Api';
import { fetchOmDashboard } from '@/lib/hvac/omApi';
import { fleetCardFor } from '@/lib/hvac/fleetCardMetrics';

const SECTION_ICON: Record<HvacSectionId, typeof CalendarClock> = {
  scheduling: CalendarClock,
  'plant-control': Gauge,
  ventilation: Wind,
  'variable-speed': Zap,
  operations: Wrench,
};

function livePointText(p?: { value?: unknown; unit?: string; quality?: string } | null, telStatus?: string) {
  if (!p || p.value == null || p.value === '') return 'NO DATA';
  if (String(p.quality || '').toUpperCase() === 'BAD') return 'NO DATA';
  if (String(telStatus || '').toUpperCase() === 'STALE') return `STALE ${p.value}${p.unit ? ` ${p.unit}` : ''}`;
  return `${p.value}${p.unit ? ` ${p.unit}` : ''}`;
}

function LivePlant({
  plant,
  telStatus,
}: {
  plant?: { chillers?: { equipment_id: string; points: Record<string, { value?: unknown; unit?: string; quality?: string }> }[]; ahus?: { equipment_id: string; points: Record<string, { value?: unknown; unit?: string; quality?: string }> }[]; pumps?: { equipment_id: string; points: Record<string, { value?: unknown; unit?: string; quality?: string }> }[]; vfds?: { equipment_id: string; points: Record<string, { value?: unknown; unit?: string; quality?: string }> }[] };
  telStatus?: string;
}) {
  const groups = [
    { title: 'Chillers', rows: plant?.chillers || [] },
    { title: 'AHUs', rows: plant?.ahus || [] },
    { title: 'Pumps', rows: plant?.pumps || [] },
    { title: 'VFDs', rows: plant?.vfds || [] },
  ];
  const empty = groups.every((g) => g.rows.length === 0);
  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Live plant</h2>
        <span className="text-[11px] font-mono text-slate-600">{telStatus || 'NO DATA'}</span>
      </div>
      {empty ? (
        <EmptyState
          title="NO DATA"
          detail="No mapped plant equipment yet. Discover the BMS and map canonical points — missing sensors stay empty."
          href="/platform/bms"
          actionLabel="Open BMS mapping"
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {groups.map((g) =>
            g.rows.map((row) => (
              <div key={row.equipment_id} className="panel-card p-4 space-y-2.5">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-[10px] font-semibold tracking-[0.14em] uppercase text-slate-500">{g.title}</div>
                  <div className="text-[10px] font-mono text-slate-600">{row.equipment_id}</div>
                </div>
                <div className="text-sm font-semibold text-slate-50">{row.equipment_id}</div>
                <div className="text-[11px] font-mono text-slate-400 space-y-1.5">
                  {Object.keys(row.points || {}).length === 0 ? (
                    <div className="text-amber-200/80">NO DATA</div>
                  ) : (
                    Object.entries(row.points).map(([k, p]) => (
                      <div key={k} className="flex justify-between gap-2">
                        <span className="text-slate-500 truncate">{k}</span>
                        <span className="text-slate-100">{livePointText(p, telStatus)}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </section>
  );
}

export default function FleetOverviewPage() {
  const buildings = useQuery({
    queryKey: ['buildings'],
    queryFn: async () => {
      const res = await hvacFetch('/api/v1/buildings');
      if (!res.ok) throw new Error('DATA SOURCE ERROR');
      return res.json();
    },
    retry: 1,
  });
  const platform = useQuery({
    queryKey: ['platform-status'],
    queryFn: async () => {
      const res = await fetch('/api/platform/status', { cache: 'no-store' });
      if (!res.ok) throw new Error('DATA SOURCE ERROR');
      return res.json();
    },
    refetchInterval: PLATFORM_POLL_MS,
  });
  const { data: cycleData } = useQuery({
    queryKey: ['supervisory-status'],
    queryFn: fetchStatus,
    refetchInterval: LIVE_POLL_MS,
  });
  const scheduling = useQuery({
    queryKey: ['scheduling-dashboard'],
    queryFn: fetchSchedulingDashboard,
    retry: 1,
    refetchInterval: LIVE_POLL_MS,
  });
  const plantDash = useQuery({
    queryKey: ['plant-control-dashboard'],
    queryFn: fetchPlantControlDashboard,
    retry: 1,
    refetchInterval: LIVE_POLL_MS,
  });
  const ventDash = useQuery({
    queryKey: ['ventilation-dashboard'],
    queryFn: async () => (await fetchVentilationDashboard()).data,
    retry: 1,
    refetchInterval: LIVE_POLL_MS,
  });
  const o14Dash = useQuery({
    queryKey: ['o14-dashboard'],
    queryFn: () => fetchO14Dashboard().catch(() => null),
    retry: 1,
    refetchInterval: LIVE_POLL_MS,
  });
  const o15Dash = useQuery({
    queryKey: ['o15-dashboard'],
    queryFn: () => fetchO15Dashboard().catch(() => null),
    retry: 1,
    refetchInterval: LIVE_POLL_MS,
  });
  const o16Dash = useQuery({
    queryKey: ['o16-dashboard'],
    queryFn: () => fetchO16Dashboard().catch(() => null),
    retry: 1,
    refetchInterval: LIVE_POLL_MS,
  });
  const omDash = useQuery({
    queryKey: ['om-dashboard'],
    queryFn: async () => (await fetchOmDashboard()).data,
    retry: 1,
    refetchInterval: LIVE_POLL_MS,
  });

  const plant = useQuery({
    queryKey: ['bms-plant'],
    queryFn: async () => {
      const res = await fetch('/api/platform/bms/plant', { cache: 'no-store' });
      if (!res.ok) return { chillers: [], ahus: [], pumps: [], vfds: [] };
      return res.json();
    },
    refetchInterval: LIVE_POLL_MS,
  });

  const buildingName = platform.data?.building?.name || buildings.data?.buildings?.[0]?.name;
  const verifiedKw = cycleData?.savings_summary?.verified_kw;
  const comfortPct = cycleData?.savings_summary?.comfort_compliance_pct;
  const totalPlantTons = cycleData?.plant?.total_tons;
  const cards = fleetOpportunityCards();
  const fleetSources = {
    plant: plantDash.data,
    vent: ventDash.data,
    o14: o14Dash.data as Record<string, unknown> | null,
    o15: o15Dash.data as Record<string, unknown> | null,
    o16: o16Dash.data as Record<string, unknown> | null,
    om: omDash.data,
  };

  return (
    <div className="space-y-8 pb-12">
      <PageHeader
        icon={LayoutDashboard}
        title="HVAC Central Optimization Platform"
        subtitle={`${buildingName || 'NO BUILDING IN DATABASE'} · O1–O20 fleet overview`}
        badge="FLEET"
      />

      <KPIGrid
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
        emptyText="NO DATA"
        items={[
          {
            label: 'Cooling Demand',
            value: totalPlantTons != null ? `${Number(totalPlantTons).toFixed(1)} Tons` : null,
            detail: platform.data?.bmsConnected ? 'From supervisory plant telemetry' : 'BMS DISCONNECTED — not LIVE',
            icon: Server,
          },
          {
            label: 'Verified Energy Shed',
            value: verifiedKw != null ? `+${Number(verifiedKw).toFixed(1)} kW` : null,
            detail: 'Verified supervisory energy impact',
            icon: Zap,
          },
          {
            label: 'Comfort Standard',
            value: comfortPct != null ? `${Number(comfortPct).toFixed(1)}%` : null,
            detail: 'ASHRAE 55 envelope',
            icon: ShieldCheck,
          },
          {
            label: 'Supervisory State',
            value: platform.data?.bmsConnected ? 'BMS CONNECTED' : 'BMS DISCONNECTED',
            detail: `Worker ${platform.data?.watchdog?.alive ? 'OK' : 'HOLD'}`,
            icon: Activity,
          },
        ]}
      />

      <LivePlant plant={plant.data} telStatus={platform.data?.telemetry?.status} />

      {HVAC_SECTIONS.map((section) => {
        const Icon = SECTION_ICON[section.id];
        const sectionCards = cards.filter((o) => o.section === section.id);
        return (
          <section key={section.id} className="space-y-3">
            <div className="panel-card p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div className="space-y-1 min-w-0">
                <div className="flex items-center gap-2.5 flex-wrap">
                  <span className="w-8 h-8 rounded-lg border border-cyan-400/20 bg-cyan-500/10 text-cyan-300 flex items-center justify-center">
                    <Icon className="w-4 h-4" />
                  </span>
                  <h2 className="text-[15px] font-semibold text-white">{section.title}</h2>
                  <StatusBadge tone="neutral" pulse={false}>
                    {sectionCards.map((c) => c.id).join(' · ')}
                  </StatusBadge>
                </div>
              </div>
              <Link href={section.href} className="btn-primary shrink-0">
                <span>Open dashboard</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
              {sectionCards.map((def) => {
                const sched =
                  section.id === 'scheduling'
                    ? scheduling.data?.opportunities?.find(
                        (o: { opportunityId?: string }) => String(o.opportunityId || '').toUpperCase() === def.id
                      )
                    : null;
                const metrics = fleetCardFor(def.id, { ...fleetSources, scheduling: sched || null });
                return (
                  <OpportunityCard
                    key={def.id}
                    code={def.id}
                    title={def.title}
                    href={def.route}
                    status={metrics.status}
                    fields={metrics.fields}
                    impactLabel={metrics.impactLabel}
                    impactValue={metrics.impactValue}
                    telemetryLabel={metrics.telemetryLabel}
                    emptyTitle="AWAITING TELEMETRY"
                    emptyDetail={def.description}
                    maxFields={4}
                  />
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}
