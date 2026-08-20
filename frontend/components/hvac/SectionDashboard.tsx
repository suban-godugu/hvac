'use client';

import React from 'react';
import { OpportunityCard, OpportunityCardField } from './OpportunityCard';
import { KPIGrid } from './KPIGrid';
import { StatusBadge } from './StatusBadge';
import { OpportunityDef } from '@/lib/hvac/opportunityConfig';
import { LucideIcon } from 'lucide-react';

export interface SectionDashboardProps {
  title: string;
  subtitle: string;
  icon: LucideIcon;
  badge?: string;
  kpis?: {
    label: string;
    value?: React.ReactNode | null;
    detail?: React.ReactNode | null;
    unit?: string | null;
    status?: string | null;
    source?: string | null;
    quality?: string | null;
    icon?: LucideIcon;
  }[];
  kpiEmptyText?: string;
  cards: {
    def: OpportunityDef;
    status?: string | null;
    fields?: OpportunityCardField[];
    impactLabel?: string;
    impactValue?: React.ReactNode | null;
    emptyTitle?: string;
    emptyDetail?: string;
    telemetryLabel?: string | null;
    href?: string;
    maxFields?: number;
  }[];
  children?: React.ReactNode;
}

export const SectionDashboard: React.FC<SectionDashboardProps> = ({
  title,
  subtitle,
  icon: Icon,
  badge,
  kpis,
  kpiEmptyText,
  cards,
  children,
}) => (
  <div className="space-y-6 pb-12">
    <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 pb-6">
      <div className="flex items-start gap-3.5">
        <div className="w-11 h-11 rounded-xl border border-cyan-400/25 bg-gradient-to-br from-cyan-400/18 to-cyan-500/5 text-cyan-300 flex items-center justify-center shrink-0 shadow-[0_0_24px_rgba(34,211,238,0.08)]">
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-[1.65rem] font-semibold text-white tracking-tight leading-tight">{title}</h1>
            {badge && (
              <StatusBadge tone="neutral" pulse={false}>
                {badge}
              </StatusBadge>
            )}
          </div>
          <p className="text-[13px] text-slate-400 mt-1.5">{subtitle}</p>
        </div>
      </div>
    </div>

    {kpis && kpis.length > 0 && <KPIGrid items={kpis} emptyText={kpiEmptyText} />}

    <div>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Opportunities</h2>
        <span className="text-[11px] font-mono text-slate-600">{cards.length} modules</span>
      </div>
      <div className={`grid grid-cols-1 md:grid-cols-2 ${cards.length >= 5 ? 'xl:grid-cols-3' : cards.length >= 4 ? 'lg:grid-cols-4' : 'lg:grid-cols-3'} gap-4`}>
        {cards.map((c) => (
          <OpportunityCard
            key={c.def.id}
            code={c.def.id}
            title={c.def.title}
            href={c.href || c.def.route}
            status={c.status}
            fields={c.fields}
            emptyTitle={c.emptyTitle}
            emptyDetail={c.emptyDetail}
            telemetryLabel={c.telemetryLabel}
            maxFields={c.maxFields}
          />
        ))}
      </div>
    </div>
    {children}
  </div>
);
