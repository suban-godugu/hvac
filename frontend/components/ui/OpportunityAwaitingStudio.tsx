'use client';

import React from 'react';
import { OpportunityWorkspace } from '@/components/hvac/guide/OpportunityWorkspace';
import { KPIGrid } from '@/components/hvac/KPIGrid';
import { EmptyState } from '@/components/hvac/EmptyState';
import { getOpportunity } from '@/lib/hvac/opportunityConfig';

interface OpportunityAwaitingStudioProps {
  opportunityId: string;
}

export const OpportunityAwaitingStudio: React.FC<OpportunityAwaitingStudioProps> = ({
  opportunityId,
}) => {
  const def = getOpportunity(opportunityId);
  if (!def) {
    return <EmptyState title="UNKNOWN OPPORTUNITY" detail={`No configuration for ${opportunityId}.`} />;
  }

  return (
    <OpportunityWorkspace def={def} live={null}>
      <KPIGrid
        items={[
          { label: 'Current', value: null },
          { label: 'Optimized', value: null },
          { label: 'Energy', value: null },
          { label: 'Confidence', value: null },
          { label: 'Status', value: 'AWAITING TELEMETRY' },
        ]}
      />
      <EmptyState />
    </OpportunityWorkspace>
  );
};
