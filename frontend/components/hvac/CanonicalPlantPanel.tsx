'use client';

import { useQuery } from '@tanstack/react-query';
import { hvacFetch } from '@/lib/api/client';
import { StatusBadge, toneForStatus } from '@/components/hvac/StatusBadge';
import { displayValue } from '@/lib/hvac/liveTelemetryStore';

export function CanonicalPlantPanel({ opportunityId }: { opportunityId: string }) {
  const ctx = useQuery({
    queryKey: ['agent-context', opportunityId],
    queryFn: async () => (await hvacFetch(`/api/agents/${opportunityId}/context`)).json(),
    refetchInterval: 10000,
    enabled: /^O\d+$/i.test(opportunityId),
  });
  const rec = useQuery({
    queryKey: ['agent-recommendation', opportunityId],
    queryFn: async () => (await hvacFetch(`/api/agents/${opportunityId}/recommendation`)).json(),
    refetchInterval: 10000,
    enabled: /^O\d+$/i.test(opportunityId),
  });
  const c = ctx.data || {};
  const r = rec.data || {};
  const features = (c.features || {}) as Record<string, { value?: unknown; unit?: string; quality?: string; source?: string; age_seconds?: number }>;

  return (
    <section className="kpi-tile space-y-3" aria-label="Canonical plant inputs">
      <div className="flex flex-wrap items-center gap-2">
        <div className="text-[11px] uppercase tracking-wider text-slate-500">Live plant inputs</div>
        <StatusBadge tone={toneForStatus(c.telemetry?.classified || c.status)}>{c.status || 'WAITING FOR TELEMETRY'}</StatusBadge>
        <StatusBadge tone="muted" pulse={false}>
          Engineering recommendation
        </StatusBadge>
        <StatusBadge tone="muted" pulse={false}>
          WRITE DISABLED
        </StatusBadge>
      </div>
      <div className="text-[11px] font-mono text-slate-500">
        SOURCE {c.telemetry?.source || '—'} · QUALITY {c.telemetry?.quality || '—'} · AGE{' '}
        {c.telemetry?.age_seconds == null ? '—' : `${Math.round(c.telemetry.age_seconds)}s`}
      </div>
      {Object.keys(features).length === 0 ? (
        <div className="text-[12px] font-mono text-slate-500">NO DATA</div>
      ) : (
        <table className="w-full text-[12px] font-mono">
          <thead className="text-slate-500 text-[10px]">
            <tr>
              <th className="text-left py-1">Point</th>
              <th className="text-left">Value</th>
              <th className="text-left">Quality</th>
              <th className="text-left">Source</th>
              <th className="text-left">Age</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(features).map(([name, f]) => (
              <tr key={name} className="border-t border-white/[0.06]">
                <td className="py-1 text-slate-300">{name}</td>
                <td>{f.value == null ? '—' : `${displayValue(f.value)}${f.unit ? ` ${f.unit}` : ''}`}</td>
                <td>{f.quality || '—'}</td>
                <td>{f.source || '—'}</td>
                <td>{f.age_seconds == null ? '—' : `${Math.round(f.age_seconds)}s`}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {(c.missing_features || []).length > 0 && (
        <div className="text-[11px] text-amber-300">Missing: {(c.missing_features || []).join(', ')}</div>
      )}
      <div className="border-t border-white/[0.06] pt-3 space-y-1">
        <div className="text-[11px] uppercase tracking-wider text-slate-500">Engine recommendation</div>
        <div className="text-[12px] font-mono text-slate-200">
          Current {r.current?.value == null ? 'NO DATA' : `${r.current.value}${r.current.unit ? ` ${r.current.unit}` : ''}`}
          {' → '}
          Recommended {r.recommended?.value == null ? 'NO DATA' : `${r.recommended.value}${r.recommended.unit ? ` ${r.recommended.unit}` : ''}`}
        </div>
        <div className="text-[11px] text-slate-400">{r.rationale || '—'}</div>
        <div className="text-[11px] font-mono text-slate-500">
          Confidence {r.confidence == null ? '—' : r.confidence} · Energy {r.energy_impact == null ? 'NO DATA' : r.energy_impact}
        </div>
        {r.ml && (
          <div className="text-[11px] font-mono text-slate-500">
            MODEL PREDICTION {r.ml.status} · never LIVE
          </div>
        )}
        <div className="text-[11px] text-rose-300">CONTROL {r.dispatch?.reason || 'WRITE_DISABLED'}</div>
      </div>
    </section>
  );
}
