'use client';

import React from 'react';
import { OpportunityDef } from '@/lib/hvac/opportunityConfig';
import { StatusBadge, toneForStatus } from './StatusBadge';
import { StudioBreadcrumb } from './StudioBreadcrumb';

interface OpportunityHeaderProps {
  def: OpportunityDef;
  live?: string | null;
  model?: string | null;
  bms?: string | null;
  ml?: string | null;
  mlModel?: string | null;
  mlConfidence?: string | null;
  actions?: React.ReactNode;
}

export const OpportunityHeader: React.FC<OpportunityHeaderProps> = ({
  def,
  live,
  model,
  bms,
  ml,
  mlModel,
  mlConfidence,
  actions,
}) => (
  <div className="px-5 pt-5 pb-4">
    <StudioBreadcrumb def={def} />
    <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4 mt-3">
      <div className="min-w-0">
        <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-cyan-400/80 mb-1.5">{def.id}</div>
        <h1 className="text-[1.7rem] font-semibold text-white tracking-tight leading-tight">{def.title}</h1>
        <p className="text-[13px] text-slate-400 mt-1.5 max-w-3xl leading-relaxed">{def.description}</p>
        <div className="flex flex-wrap gap-1.5 mt-3.5">
          <StatusBadge tone={toneForStatus(live)}>Telemetry {live || 'NO DATA'}</StatusBadge>
          <StatusBadge tone="neutral" pulse={false}>
            ML {ml && ml !== 'LIVE' ? ml : ml || 'NO DATA'}
          </StatusBadge>
          {mlModel && (
            <StatusBadge tone="neutral" pulse={false}>
              {mlModel}
            </StatusBadge>
          )}
          {mlConfidence && (
            <StatusBadge tone="neutral" pulse={false}>
              {mlConfidence}
            </StatusBadge>
          )}
          {model && (
            <StatusBadge tone="neutral" pulse={false}>
              {model}
            </StatusBadge>
          )}
          {bms && <StatusBadge tone={toneForStatus(bms)}>{bms}</StatusBadge>}
        </div>
      </div>
      {actions && <div className="flex flex-wrap gap-2 shrink-0">{actions}</div>}
    </div>
  </div>
);
