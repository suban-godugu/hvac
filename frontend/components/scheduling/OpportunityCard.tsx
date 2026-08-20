'use client';

import React from 'react';
import { opportunitiesForSection } from '@/lib/hvac/opportunityConfig';
import { OpportunityKPICard, type OpportunityKpi } from './OpportunityKPICard';

export type SchedulingOpportunity = OpportunityKpi;

function matchOpp(opps: OpportunityKpi[] | undefined, code: string) {
  return opps?.find((o) => String(o.opportunityId || '').toUpperCase() === code);
}

interface OpportunityCardsProps {
  opportunities?: OpportunityKpi[];
  backendOffline?: boolean;
}

export const OpportunityCardGrid: React.FC<OpportunityCardsProps> = ({
  opportunities,
  backendOffline,
}) => {
  const defs = opportunitiesForSection('scheduling');

  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4">
      {defs.map((def) => {
        const live = matchOpp(opportunities, def.id);
        const opportunity: OpportunityKpi = live || {
          opportunityId: def.id,
          name: def.title,
          status: backendOffline ? 'ERROR' : 'AWAITING TELEMETRY',
          dataState: backendOffline ? 'ERROR' : 'AWAITING_TELEMETRY',
          primaryMetric: { label: 'Primary', value: null },
          secondaryMetrics: [],
        };
        if (!live) {
          opportunity.name = def.title;
          opportunity.opportunityId = def.id;
        }
        return (
          <OpportunityKPICard
            key={def.id}
            opportunity={opportunity}
            href={def.route}
            backendOffline={backendOffline}
          />
        );
      })}
    </div>
  );
};

export { OpportunityCardGrid as OpportunityCard };
