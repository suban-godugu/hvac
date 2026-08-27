'use client';

import React, { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Activity, LayoutDashboard, Server, ShieldCheck, Zap } from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { StatusBadge, toneForStatus } from '@/components/hvac/StatusBadge';
import { OpportunityCard } from '@/components/hvac/OpportunityCard';
import { AlertRail, AssetRail, AssetRailEmpty, KpiRow, PlantCanvas, SystemsHub } from '@/components/hvac/bms-home';
import { hvacFetch } from '@/lib/api/client';
import { PLATFORM_POLL_MS } from '@/lib/hvac/poll';
import { getOpportunity } from '@/lib/hvac/opportunityConfig';
import type { DashboardHome, DashboardOpportunity, PlantEquipment } from '@/lib/hvac/dashboardHome';

export default function FleetOverviewPage() {
  const home = useQuery({
    queryKey: ['dashboard-home'],
    queryFn: async () => {
      const res = await hvacFetch('/api/platform/dashboard/home');
      if (!res.ok) throw new Error('DATA SOURCE ERROR');
      return res.json() as Promise<DashboardHome>;
    },
    refetchInterval: PLATFORM_POLL_MS,
  });
  const data = home.data;
  const layers = data?.layers;
  const allOpps: DashboardOpportunity[] = useMemo(
    () => (data?.chapters || []).flatMap((c) => c.opportunities),
    [data?.chapters]
  );
  const firstRow = useMemo(() => {
    for (const rows of Object.values(layers || {})) {
      if (rows?.[0]) return rows[0];
    }
    return null;
  }, [layers]);
  const [selected, setSelected] = useState<PlantEquipment | null>(null);
  const active = selected || firstRow;
  const plantEmpty = !layers || Object.values(layers).every((rows) => !rows?.length);
  const tel = String(data?.telemetry?.status || data?.provenance || 'NO DATA');
  const kpis = data?.kpis || {};
  const energy = data?.energy?.points || [];

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        icon={LayoutDashboard}
        title="Building operations"
        subtitle={`${data?.building?.name || 'NO BUILDING IN DATABASE'} · OEH / AIRAH O1–O20 Table 1`}
        badge={tel}
        actions={
          <div className="flex flex-wrap gap-2">
            <StatusBadge tone={toneForStatus(data?.bms?.status)}>BMS {data?.bms?.status || 'DISCONNECTED'}</StatusBadge>
            <StatusBadge tone={toneForStatus(tel)}>TEL {tel}</StatusBadge>
          </div>
        }
      />

      <KpiRow
        items={[
          {
            label: 'Plant / HVAC load',
            value: kpis.coolingTons != null ? `${Number(kpis.coolingTons).toFixed(1)} Tons` : null,
            detail: tel === 'SIMULATED' ? 'DATASET — not LIVE BMS' : 'From supervisory plant telemetry',
            icon: Server,
          },
          {
            label: 'Comfort',
            value: kpis.comfortPct != null ? `${Number(kpis.comfortPct).toFixed(1)}%` : null,
            detail: 'Measured comfort envelope',
            icon: ShieldCheck,
          },
          {
            label: 'Verified kW',
            value: kpis.verifiedKw != null ? `+${Number(kpis.verifiedKw).toFixed(1)} kW` : null,
            detail: 'Supervisory M&V only — not GUIDE_POTENTIAL',
            icon: Zap,
          },
          {
            label: 'Issues',
            value: kpis.alertCount != null ? String(kpis.alertCount) : null,
            detail: 'Stale / BAD / BMS / O19',
            icon: Activity,
          },
        ]}
      />

      {plantEmpty ? (
        <AssetRailEmpty />
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
          <div className="xl:col-span-7">
            <PlantCanvas layers={layers} selectedId={active?.equipment_id} onSelect={setSelected} />
          </div>
          <div className="xl:col-span-5">
            <AssetRail selected={active} opportunities={allOpps} telStatus={tel} />
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        <section className="glass-card p-4 xl:col-span-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">Energy</div>
          {energy.length === 0 ? (
            <p className="text-[12px] text-slate-500 mt-3">AWAITING TELEMETRY — no energy series yet.</p>
          ) : (
            <ul className="mt-3 space-y-1 font-mono text-[11px] text-slate-400 max-h-40 overflow-y-auto">
              {energy.slice(-12).map((p, i) => (
                <li key={`${p.t}-${i}`} className="flex justify-between gap-2">
                  <span className="truncate">{String(p.t || '')}</span>
                  <span className="text-slate-200">
                    {p.v} {data?.energy?.unit}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
        <div className="xl:col-span-4">
          <AlertRail alerts={data?.alerts} />
        </div>
        <div className="xl:col-span-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500 mb-3">Guide chapters</div>
          <SystemsHub chapters={data?.chapters} variant="compact" />
          <p className="text-[9px] font-mono text-slate-600 mt-2">GUIDE_POTENTIAL · non-cumulative · not measured LIVE</p>
        </div>
      </div>

      <details className="glass-card p-4">
        <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">
          All opportunities
        </summary>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mt-4">
          {allOpps.map((o) => {
            const def = getOpportunity(o.id);
            return (
              <OpportunityCard
                key={o.id}
                code={o.id}
                title={def?.title || o.title || o.id}
                href={o.href || def?.route || '/agents'}
                telemetryLabel={o.telemetry}
                emptyTitle="AWAITING TELEMETRY"
                emptyDetail={o.practice || def?.description}
                fields={[
                  { label: 'Table 1', value: o.applicability || 'Unmapped' },
                  { label: 'Guide', value: o.guide_savings_potential || 'GUIDE_POTENTIAL' },
                ]}
                maxFields={4}
              />
            );
          })}
        </div>
      </details>
    </div>
  );
}
