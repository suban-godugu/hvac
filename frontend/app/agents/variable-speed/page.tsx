'use client';

import React, { useEffect, useState } from 'react';
import { Zap } from 'lucide-react';
import { SectionDashboard } from '@/components/hvac/SectionDashboard';
import { getOpportunity } from '@/lib/hvac/opportunityConfig';
import { fetchO14Dashboard } from '@/lib/hvac/o14Api';
import { fetchO15Dashboard } from '@/lib/hvac/o15Api';
import { fetchO16Dashboard } from '@/lib/hvac/o16Api';
import { provenanceFromAgent } from '@/lib/hvac/provenance';
import { MlSectionStrip } from '@/components/hvac/MlSectionStrip';
import { fmtDash, fmtUnit } from '@/lib/hvac/o15Format';

export default function VariableSpeedDashboardPage() {
  const [o14, setO14] = useState<Record<string, unknown> | null>(null);
  const [o15, setO15] = useState<Record<string, unknown> | null>(null);
  const [o16, setO16] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [a, b, c] = await Promise.all([
          fetchO14Dashboard().catch(() => null),
          fetchO15Dashboard().catch(() => null),
          fetchO16Dashboard().catch(() => null),
        ]);
        if (cancelled) return;
        setO14(a as Record<string, unknown> | null);
        setO15(b as Record<string, unknown> | null);
        setO16(c as Record<string, unknown> | null);
        setError(!a && !b && !c);
      } catch {
        if (!cancelled) setError(true);
      }
    };
    load();
    const interval = setInterval(load, 8000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const p14 = provenanceFromAgent(o14);
  const p15 = provenanceFromAgent(o15);
  const p16 = provenanceFromAgent(o16);
  const liveCount = [p14, p15, p16].filter((p) => p === 'LIVE').length;
  const o14cs = (o14?.current_state as Record<string, unknown> | undefined) || {};
  const o14os = (o14?.optimized_state as Record<string, unknown> | undefined) || {};
  const o15cs = (o15?.current_state as Record<string, unknown> | undefined) || {};
  const o16cs = (o16?.current_state as Record<string, unknown> | undefined) || {};

  return (
    <SectionDashboard
      title="Variable Speed Systems"
      subtitle="Secondary chilled water pumping and condenser head-pressure control."
      icon={Zap}
      badge="O14–O16"
      kpiEmptyText={error ? 'DATA SOURCE ERROR' : 'NO DATA'}
      kpis={[
        { label: 'LIVE opportunities', value: `${liveCount} / 3` },
        { label: 'O14 provenance', value: p14 },
        { label: 'O15 provenance', value: p15 },
        { label: 'O16 provenance', value: p16 },
      ]}
      cards={[
        {
          def: getOpportunity('O14')!,
          status: (o14?.recommendation_state as string) || (o14?.status as string),
          telemetryLabel: p14,
          fields: [
            { label: 'Current DP', value: fmtDash(o14cs.dp_setpoint) },
            { label: 'Recommended DP', value: fmtDash(o14os.recommended_dp_setpoint) },
            { label: 'Eligible', value: o14?.dispatchable == null ? 'NO DATA' : o14.dispatchable ? 'YES' : 'NO' },
          ],
        },
        {
          def: getOpportunity('O15')!,
          status: (o15?.recommendation_state as string) || (o15?.status as string),
          telemetryLabel: p15,
          fields: [
            { label: 'Head pressure', value: fmtUnit(o15cs.head_pressure, 'psig') },
            { label: 'Fan speed', value: fmtUnit(o15cs.fan_speed_pct, '%') },
            { label: 'Eligible', value: o15?.dispatchable == null ? 'NO DATA' : o15.dispatchable ? 'YES' : 'NO' },
          ],
        },
        {
          def: getOpportunity('O16')!,
          status: (o16?.recommendation_state as string) || (o16?.status as string),
          telemetryLabel: p16,
          fields: [
            { label: 'Head pressure', value: fmtUnit(o16cs.head_pressure, 'psig') },
            { label: 'Pump speed', value: fmtUnit(o16cs.pump_speed_pct, '%') },
            { label: 'Eligible', value: o16?.dispatchable == null ? 'NO DATA' : o16.dispatchable ? 'YES' : 'NO' },
          ],
        },
      ]}
    >
      <MlSectionStrip opportunityIds={['O14', 'O15', 'O16']} />
    </SectionDashboard>
  );
}
