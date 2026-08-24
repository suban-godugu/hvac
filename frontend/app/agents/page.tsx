'use client';

import React from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { ArrowRight, Users } from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { StatusBadge, toneForStatus } from '@/components/hvac/StatusBadge';
import { EmptyState } from '@/components/hvac/EmptyState';
import { hvacFetch } from '@/lib/api/client';
import { PLATFORM_POLL_MS } from '@/lib/hvac/poll';
import { useLiveTelemetry } from '@/lib/hvac/liveTelemetryStore';
import { getOpportunity } from '@/lib/hvac/opportunityConfig';

const RAIL: Record<string, string> = {
  scheduling: 'var(--cat-scheduling)',
  'plant-control': 'var(--cat-plant)',
  ventilation: 'var(--cat-ventilation)',
  'variable-speed': 'var(--cat-variablespeed)',
  operations: 'var(--cat-om)',
};

function telDot(label?: string) {
  const v = String(label || '').toUpperCase();
  if (v === 'LIVE') return 'bg-emerald-400';
  if (v === 'SIMULATED' || v === 'STALE') return 'bg-amber-400';
  if (v.includes('BAD') || v.includes('OFF')) return 'bg-rose-400';
  return 'bg-slate-500';
}

function controlLabel(raw?: string | null) {
  const v = String(raw || '').trim().toUpperCase();
  if (v.includes('ENABLED') && !v.includes('DISABLED')) return 'WRITE ENABLED';
  return 'WRITE DISABLED';
}

export default function AgentsPage() {
  const live = useLiveTelemetry();
  const { data } = useQuery({
    queryKey: ['agent-center'],
    queryFn: async () => (await hvacFetch('/api/agents')).json(),
    refetchInterval: PLATFORM_POLL_MS,
  });
  const groups = data?.groups || [];
  const pageControl = groups.some(
    (g: { controlAvailability?: string; cards?: { control?: string }[] }) =>
      controlLabel(g.controlAvailability) === 'WRITE ENABLED' ||
      (g.cards || []).some((c) => controlLabel(c.control) === 'WRITE ENABLED')
  )
    ? 'WRITE ENABLED'
    : 'WRITE DISABLED';

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        icon={Users}
        title="Agent Control Center"
        subtitle="ENGINE is the decision method; MODEL is the ML registry label. Simulation allows WRITE ENABLED on the synthetic plant only — live BMS writes stay gated."
        badge="O1–O20"
      />
      <div className="flex flex-wrap gap-2">
        <StatusBadge tone={toneForStatus(live.bmsStatus)}>BMS {live.bmsStatus}</StatusBadge>
        <StatusBadge tone={toneForStatus(live.telemetryStatus)}>TELEMETRY {live.telemetryStatus}</StatusBadge>
        <StatusBadge tone={pageControl === 'WRITE ENABLED' ? 'live' : 'muted'} pulse={false}>
          {pageControl}
        </StatusBadge>
      </div>
      <div className="space-y-6">
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
              engine?: string;
              model?: string;
              kind?: string;
            }[];
          }) => {
            const groupControl = controlLabel(g.controlAvailability);
            return (
            <section key={g.id} className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <Link href={g.href} className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500 hover:text-cyan-200">
                  <span className="w-1.5 h-5 rounded-full" style={{ background: RAIL[g.id] || 'var(--accent-cyan)' }} />
                  {g.title}
                </Link>
                <div className="flex flex-wrap gap-1.5 justify-end">
                  <StatusBadge tone={toneForStatus(g.status)}>{g.status}</StatusBadge>
                  <StatusBadge tone="muted" pulse={false}>
                    REC {g.recommendation || 'UNAVAILABLE'}
                  </StatusBadge>
                  <StatusBadge tone={groupControl === 'WRITE ENABLED' ? 'live' : 'muted'} pulse={false}>
                    {groupControl}
                  </StatusBadge>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                {(g.cards || []).map((card) => {
                  const def = getOpportunity(card.id);
                  const href = def?.route || g.href;
                  const waiting = String(card.status || '').includes('WAITING');
                  const ctrl = controlLabel(card.control);
                  return (
                    <Link
                      key={card.id}
                      href={href}
                      className="glass-card flex flex-col justify-between p-4 group relative overflow-hidden"
                      style={{ borderLeft: `3px solid ${RAIL[g.id] || 'rgba(34,211,238,0.4)'}` }}
                    >
                      <div>
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-md border border-cyan-400/25 bg-cyan-500/10 text-cyan-300 tracking-wide">
                            {card.id}
                          </span>
                          <ArrowRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-cyan-400 shrink-0" />
                        </div>
                        <h3 className="text-[15px] font-semibold text-slate-50 mt-3 tracking-tight leading-snug group-hover:text-cyan-100 transition-colors">
                          {def?.shortLabel || def?.title || ''}
                        </h3>
                      </div>
                      <div className="my-3 space-y-1.5 py-3 border-y border-white/[0.06] text-xs font-mono">
                        <div className="flex justify-between gap-2 items-center">
                          <span>TELEMETRY</span>
                          <span className="text-slate-200 inline-flex items-center gap-1.5">
                            <span className={`w-1.5 h-1.5 rounded-full ${telDot(card.telemetry)}`} />
                            {card.telemetry}
                          </span>
                        </div>
                        <div className="flex justify-between gap-2">
                          <span>AGENT</span>
                          <span className="text-slate-200">{card.status}</span>
                        </div>
                        <div className="flex justify-between gap-2">
                          <span>KIND</span>
                          <span className="text-slate-200 text-right">{card.kind || 'CONTROL'}</span>
                        </div>
                        <div className="flex justify-between gap-2">
                          <span>RECOMMENDATION</span>
                          <span className="text-slate-200 text-right">{card.recommendation}</span>
                        </div>
                        <div className="flex justify-between gap-2">
                          <span>ENGINE</span>
                          <span className="text-slate-200 text-right">{card.engine || '—'}</span>
                        </div>
                        <div className="flex justify-between gap-2">
                          <span>MODEL</span>
                          <span className="text-slate-200 text-right">{card.model || '—'}</span>
                        </div>
                        <div
                          className={`flex justify-between gap-2 ${
                            ctrl === 'WRITE DISABLED' ? 'text-rose-300' : 'text-emerald-300'
                          }`}
                        >
                          <span>CONTROL</span>
                          <span>{ctrl}</span>
                        </div>
                      </div>
                      {waiting ? (
                        <div className="text-[10px] text-amber-200/80">Waiting for mapped telemetry</div>
                      ) : null}
                    </Link>
                  );
                })}
              </div>
            </section>
            );
          }
        )}
      </div>
      {groups.length === 0 && (
        <EmptyState title="NO DATA" detail="Agent groups did not load from the backend." />
      )}
    </div>
  );
}
