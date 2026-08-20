'use client';

import React from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { ArrowRight, Users } from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { StatusBadge, toneForStatus } from '@/components/hvac/StatusBadge';
import { hvacFetch } from '@/lib/api/client';
import { PLATFORM_POLL_MS } from '@/lib/hvac/poll';
import { useLiveTelemetry } from '@/lib/hvac/liveTelemetryStore';
import { getOpportunity } from '@/lib/hvac/opportunityConfig';

export default function AgentsPage() {
  const live = useLiveTelemetry();
  const { data } = useQuery({
    queryKey: ['agent-center'],
    queryFn: async () => (await hvacFetch('/api/agents')).json(),
    refetchInterval: PLATFORM_POLL_MS,
  });
  const groups = data?.groups || [];

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        icon={Users}
        title="Agent Control Center"
        subtitle="Shared canonical telemetry. Engineering recommendations only — writes stay disabled."
        badge="O1–O20"
      />
      <div className="flex flex-wrap gap-2">
        <StatusBadge tone={toneForStatus(live.bmsStatus)}>BMS {live.bmsStatus}</StatusBadge>
        <StatusBadge tone={toneForStatus(live.telemetryStatus)}>TELEMETRY {live.telemetryStatus}</StatusBadge>
        <StatusBadge tone="muted" pulse={false}>
          WRITE DISABLED
        </StatusBadge>
      </div>
      <div className="space-y-8">
        {groups.map(
          (g: {
            id: string;
            title: string;
            href: string;
            status: string;
            controlAvailability?: string;
            recommendation?: string;
            cards?: {
              id: string;
              status: string;
              telemetry: string;
              recommendation: string;
              control: string;
            }[];
          }) => (
            <section key={g.id} className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <Link href={g.href} className="text-[15px] font-semibold text-slate-50 hover:text-cyan-200">
                  {g.title}
                </Link>
                <div className="flex flex-wrap gap-1.5 justify-end">
                  <StatusBadge tone={toneForStatus(g.status)}>{g.status}</StatusBadge>
                  <StatusBadge tone="muted" pulse={false}>
                    REC {g.recommendation || 'UNAVAILABLE'}
                  </StatusBadge>
                  <StatusBadge tone="muted" pulse={false}>
                    {g.controlAvailability || 'WRITE DISABLED'}
                  </StatusBadge>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
                {(g.cards || []).map((card) => {
                  const def = getOpportunity(card.id);
                  const href = def?.route || g.href;
                  return (
                    <Link key={card.id} href={href} className="glass-card p-4 block space-y-3 group">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="text-[10px] font-mono font-bold text-cyan-300">{card.id}</div>
                          <div className="text-[13px] font-semibold text-slate-50 mt-1 group-hover:text-cyan-100">
                            {def?.shortLabel || def?.title || ''}
                          </div>
                        </div>
                        <ArrowRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-cyan-400 shrink-0 mt-0.5" />
                      </div>
                      <div className="space-y-1.5 text-[10px] font-mono text-slate-400">
                        <div className="flex justify-between gap-2">
                          <span>TELEMETRY</span>
                          <span className="text-slate-200">{card.telemetry}</span>
                        </div>
                        <div className="flex justify-between gap-2">
                          <span>AGENT</span>
                          <span className="text-slate-200">{card.status}</span>
                        </div>
                        <div className="flex justify-between gap-2">
                          <span>RECOMMENDATION</span>
                          <span className="text-slate-200 text-right">{card.recommendation}</span>
                        </div>
                        <div className="flex justify-between gap-2 text-rose-300">
                          <span>CONTROL</span>
                          <span>WRITE DISABLED</span>
                        </div>
                      </div>
                    </Link>
                  );
                })}
              </div>
            </section>
          )
        )}
      </div>
      {groups.length === 0 && <div className="panel-card p-6 text-sm text-slate-500">NO DATA</div>}
    </div>
  );
}
