'use client';

import React, { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Brain } from 'lucide-react';
import { apiJson } from '@/lib/api/client';
import { StatusBadge } from '@/components/hvac/StatusBadge';
import { PageHeader } from '@/components/ui/PageHeader';
import { EmptyState } from '@/components/hvac/EmptyState';

type Filter =
  | 'all'
  | 'MODEL_READY'
  | 'MODEL_NOT_AVAILABLE'
  | 'MODEL_NOT_TRAINABLE'
  | 'TRAINING'
  | 'TRAINING_FAILED'
  | 'DATASET_INVALID';

interface HealthRow {
  opportunity_id: string;
  agent_id?: string | null;
  dataset_id?: string | null;
  dataset_name?: string | null;
  dataset_status?: string | null;
  dataset_quality?: { missing_pct?: number | null; files?: number; sample_rows?: number } | null;
  feature_map?: Record<string, string>;
  target?: string | null;
  model_id?: string | null;
  model_version?: string | null;
  status: string;
  validation_status?: string | null;
  metrics?: { validation?: Record<string, number | null>; test?: Record<string, number | null> } | null;
  last_trained?: string | null;
  prediction_availability?: string | null;
  provenance?: string | null;
  notes?: string | null;
  missing_dataset?: string | null;
  last_prediction?: { provenance?: string; source?: string; status?: string; created_at?: string } | null;
  training_run?: { status?: string; reason?: string; algorithm?: string; metrics?: unknown } | null;
}

function fmtMetrics(m: Record<string, number | null> | undefined) {
  if (!m) return '—';
  return Object.entries(m)
    .filter(([, v]) => v != null)
    .map(([k, v]) => `${k}=${typeof v === 'number' ? v.toFixed(3) : v}`)
    .join(' ') || '—';
}

export default function MlRegistryPage() {
  const [filter, setFilter] = useState<Filter>('all');
  const [selected, setSelected] = useState<string>('O1');
  const q = useQuery({
    queryKey: ['ml-health'],
    queryFn: () => apiJson('/ml/health') as Promise<{ opportunities: HealthRow[]; source: string; datasets: unknown[] }>,
    staleTime: 15_000,
    retry: 2,
  });

  const rows = useMemo(() => q.data?.opportunities || [], [q.data]);
  const filtered = useMemo(() => {
    if (filter === 'all') return rows;
    if (filter === 'TRAINING') return rows.filter((r) => r.status === 'TRAINING');
    return rows.filter((r) => r.status === filter);
  }, [rows, filter]);
  const detail = rows.find((r) => r.opportunity_id === selected) || filtered[0];

  const filters: { id: Filter; label: string }[] = [
    { id: 'all', label: 'All' },
    { id: 'MODEL_READY', label: 'Model Ready' },
    { id: 'MODEL_NOT_AVAILABLE', label: 'Not Available' },
    { id: 'MODEL_NOT_TRAINABLE', label: 'Not Trainable' },
    { id: 'TRAINING', label: 'Training' },
    { id: 'TRAINING_FAILED', label: 'Failed' },
    { id: 'DATASET_INVALID', label: 'Dataset Invalid' },
  ];

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        icon={Brain}
        title="HVAC ML Registry & Model Health"
        subtitle="Training/reference models for O1–O20. Provenance is MODEL PREDICTION only — never LIVE BMS."
        badge="MODEL PREDICTION"
      />

      <div className="flex flex-wrap gap-2">
        {filters.map((f) => (
          <button
            key={f.id}
            type="button"
            onClick={() => setFilter(f.id)}
            className={`chip-filter ${filter === f.id ? 'chip-filter-on' : ''}`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {rows.some((r) => r.missing_dataset) ? (
        <section className="glass-card p-4 space-y-2">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-amber-300">MISSING DATASETS</div>
          <ul className="text-[12px] space-y-1 text-slate-300">
            {rows
              .filter((r) => r.missing_dataset)
              .map((r) => (
                <li key={r.opportunity_id}>
                  <span className="text-cyan-400 font-mono">{r.opportunity_id}</span> {r.missing_dataset}
                </li>
              ))}
          </ul>
        </section>
      ) : null}
      {q.isError && rows.length === 0 ? (
        <EmptyState
          title="DATA SOURCE ERROR"
          detail="ML registry unavailable."
          onRetry={() => q.refetch()}
        />
      ) : null}

      <div className="overflow-x-auto glass-card">
        <table className="bms-table">
          <thead className="text-slate-500 text-left">
            <tr className="border-b border-white/10">
              <th className="p-2">Opportunity</th>
              <th className="p-2">Agent</th>
              <th className="p-2">Dataset</th>
              <th className="p-2">Dataset quality</th>
              <th className="p-2">Feature map</th>
              <th className="p-2">Target</th>
              <th className="p-2">Model</th>
              <th className="p-2">Model version</th>
              <th className="p-2">Status</th>
              <th className="p-2">Validation status</th>
              <th className="p-2">Confidence/metrics</th>
              <th className="p-2">Last trained</th>
              <th className="p-2">Prediction availability</th>
              <th className="p-2">Provenance</th>
              <th className="p-2">Missing dataset</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => (
              <tr
                key={r.opportunity_id}
                onClick={() => setSelected(r.opportunity_id)}
                className={`border-b border-white/[0.04] cursor-pointer ${
                  selected === r.opportunity_id ? 'bg-cyan-500/[0.08]' : 'hover:bg-white/[0.03]'
                }`}
              >
                <td className="p-2 text-cyan-400">{r.opportunity_id}</td>
                <td className="p-2 text-slate-300">{r.agent_id || '—'}</td>
                <td className="p-2 text-slate-300">{r.dataset_id || '—'}</td>
                <td className="p-2 text-slate-400">
                  {r.dataset_quality?.missing_pct == null ? '—' : `miss ${r.dataset_quality.missing_pct}%`}
                </td>
                <td className="p-2 text-slate-400 max-w-[9rem] truncate" title={JSON.stringify(r.feature_map || {})}>
                  {r.feature_map && Object.keys(r.feature_map).length ? Object.keys(r.feature_map).join(', ') : '—'}
                </td>
                <td className="p-2 text-slate-400 max-w-[10rem] truncate">{r.target || '—'}</td>
                <td className="p-2 text-slate-300">{r.model_id || '—'}</td>
                <td className="p-2 text-slate-300">{r.model_version || '—'}</td>
                <td className="p-2">
                  <StatusBadge tone={r.status === 'MODEL_READY' ? 'live' : 'muted'} pulse={false}>
                    {r.status}
                  </StatusBadge>
                </td>
                <td className="p-2 text-slate-400">{r.validation_status || '—'}</td>
                <td className="p-2 text-slate-400">{fmtMetrics(r.metrics?.validation)}</td>
                <td className="p-2 text-slate-400">{r.last_trained || '—'}</td>
                <td className="p-2 text-slate-400">{r.prediction_availability || '—'}</td>
                <td className="p-2 text-violet-300">
                  {r.provenance === 'LIVE' || r.provenance === 'LIVE_BMS' ? 'TRAINING DATA' : r.provenance}
                </td>
                <td className="p-2 text-amber-300 max-w-[14rem] truncate" title={r.missing_dataset || ''}>
                  {r.missing_dataset || '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!q.isLoading && filtered.length === 0 ? (
          <EmptyState
            title="NO DATA"
            detail={
              rows.length === 0
                ? 'No ML registry rows were returned.'
                : `No opportunities in this filter (${rows.length} in registry). Switch to All.`
            }
          />
        ) : null}
      </div>

      {detail ? (
        <section className="glass-card p-4 space-y-3">
          <div className="text-[10px] font-mono tracking-[0.18em] text-violet-300">OPPORTUNITY DETAIL · {detail.opportunity_id}</div>
          <dl className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[12px]">
            <div>
              <dt className="text-slate-500">Dataset provenance</dt>
              <dd className="text-slate-200">
                TRAINING_DATASET · {detail.dataset_id || '—'} · {detail.dataset_status || '—'}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Target</dt>
              <dd className="text-slate-200">{detail.target || 'MODEL NOT TRAINABLE'}</dd>
            </div>
            <div className="md:col-span-2">
              <dt className="text-slate-500">Feature map</dt>
              <dd className="text-slate-300 font-mono text-[11px]">
                {detail.feature_map && Object.keys(detail.feature_map).length
                  ? JSON.stringify(detail.feature_map)
                  : '—'}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Training run</dt>
              <dd className="text-slate-200">
                {detail.training_run?.status || '—'} {detail.training_run?.algorithm ? `· ${detail.training_run.algorithm}` : ''}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Validation</dt>
              <dd className="text-slate-200">{detail.validation_status} · {fmtMetrics(detail.metrics?.validation)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Prediction status</dt>
              <dd className="text-slate-200">{detail.prediction_availability}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Last prediction</dt>
              <dd className="text-slate-200">
                {detail.last_prediction
                  ? `${
                      detail.last_prediction.provenance === 'LIVE' || detail.last_prediction.provenance === 'LIVE_BMS'
                        ? 'MODEL PREDICTION'
                        : detail.last_prediction.provenance
                    } · ${detail.last_prediction.created_at || ''}`
                  : '—'}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">ML provenance</dt>
              <dd className="text-slate-200">TRAINING DATA · never LIVE BMS</dd>
            </div>
            <div className="md:col-span-2">
              <dt className="text-slate-500">Model metrics</dt>
              <dd className="text-slate-300 font-mono text-[11px]">
                val {fmtMetrics(detail.metrics?.validation)} · test {fmtMetrics(detail.metrics?.test)}
              </dd>
            </div>
            <div className="md:col-span-2">
              <dt className="text-slate-500">Notes</dt>
              <dd className="text-slate-400">{detail.notes || '—'}</dd>
            </div>
            <div className="md:col-span-2">
              <dt className="text-slate-500">Missing dataset</dt>
              <dd className="text-amber-200">{detail.missing_dataset || '—'}</dd>
            </div>
          </dl>
          <p className="text-[11px] text-slate-500">
            ML is advisory. Engineering agents remain responsible for recommendations. evaluate_dispatch() remains the write gate.
          </p>
        </section>
      ) : null}
    </div>
  );
}
