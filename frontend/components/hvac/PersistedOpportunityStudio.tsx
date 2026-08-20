'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { RotateCcw } from 'lucide-react';
import { OpportunityWorkspace } from '@/components/hvac/guide/OpportunityWorkspace';
import { KPIGrid } from '@/components/hvac/KPIGrid';
import { EmptyState } from '@/components/hvac/EmptyState';
import { getOpportunity } from '@/lib/hvac/opportunityConfig';

interface PersistedOpportunityStudioProps {
  opportunityId: string;
  stateUrl: string;
  dispatchUrl?: string;
  rollbackUrl?: string;
}

export const PersistedOpportunityStudio: React.FC<PersistedOpportunityStudioProps> = ({
  opportunityId,
  stateUrl,
  dispatchUrl,
  rollbackUrl,
}) => {
  const def = getOpportunity(opportunityId)!;
  const [data, setData] = useState<any>(null);
  const [status, setStatus] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch(stateUrl);
      if (res.ok) setData(await res.json());
      else setData(null);
    } catch {
      setData(null);
    }
  }, [stateUrl]);

  useEffect(() => {
    load();
    const id = window.setInterval(load, 5000);
    return () => window.clearInterval(id);
  }, [load]);

  const live = data?.live ? 'LIVE' : undefined;
  const current = data?.current_value ?? data?.co?.co_ppm ?? null;
  const optimized = data?.optimized_value ?? null;
  const energy = data?.energy_impact ?? null;
  const confidence = data?.confidence ?? null;
  const oppStatus = data?.status ?? null;
  const hasLive = Boolean(data?.live);

  return (
    <OpportunityWorkspace
      def={def}
      live={live}
      actions={
        rollbackUrl ? (
          <button
            className="btn-danger"
            onClick={async () => {
              await fetch(rollbackUrl, { method: 'POST' });
              load();
            }}
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Fail-Safe Rollback
          </button>
        ) : undefined
      }
    >
      <KPIGrid
        items={[
          { label: 'Current', value: current == null ? null : String(current) },
          { label: 'Optimized', value: optimized == null ? null : String(optimized) },
          { label: 'Energy', value: energy == null ? null : String(energy) },
          { label: 'Confidence', value: confidence == null ? null : String(confidence) },
          { label: 'Status', value: oppStatus },
        ]}
      />
      {!hasLive && <EmptyState />}
      {hasLive && data?.optimization?.reason && (
        <div className="kpi-tile">
          <div className="text-[11px] uppercase tracking-wider text-slate-500">Recommendation</div>
          <p className="text-sm text-slate-200 mt-2">{data.optimization.reason}</p>
        </div>
      )}
      {dispatchUrl && (
        <button
          className="btn-primary"
          disabled={optimized == null}
          onClick={async () => {
            if (optimized == null) return;
            setStatus('DISPATCHING');
            const res = await fetch(dispatchUrl, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ target_value: Number(optimized), target_speed_pct: Number(optimized), equipment_id: 'EQ-01' }),
            });
            setStatus(res.ok ? 'ACKNOWLEDGED' : 'FAILED');
            setTimeout(() => setStatus(null), 4000);
          }}
        >
          {status || 'Dispatch'}
        </button>
      )}
    </OpportunityWorkspace>
  );
};
