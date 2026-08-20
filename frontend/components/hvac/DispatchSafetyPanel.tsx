'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { hvacFetch } from '@/lib/api/client';
import { useLiveTelemetry } from '@/lib/hvac/liveTelemetryStore';

const CHECKS: { key: string; okLabel: string; failLabel: string }[] = [
  { key: 'bms_connected', okLabel: 'BMS CONNECTED', failLabel: 'BMS DISCONNECTED' },
  { key: 'telemetry_live', okLabel: 'LIVE_BMS', failLabel: 'TELEMETRY NOT LIVE' },
  { key: 'quality_good', okLabel: 'QUALITY GOOD', failLabel: 'QUALITY NOT GOOD' },
  { key: 'fresh', okLabel: 'TELEMETRY FRESH', failLabel: 'TELEMETRY STALE' },
];

export function DispatchSafetyPanel({
  opportunityId,
  currentValue,
  targetValue,
  confidence,
  decision = 'OPTIMIZE',
}: {
  opportunityId: string;
  currentValue?: number | null;
  targetValue?: number | null;
  confidence?: number | null;
  decision?: string;
}) {
  const live = useLiveTelemetry();
  const q = useQuery({
    queryKey: ['dispatch-safety', opportunityId, currentValue, targetValue, confidence],
    queryFn: async () => {
      const res = await hvacFetch('/api/platform/safety/evaluate', {
        method: 'POST',
        body: JSON.stringify({
          opportunity_id: opportunityId,
          current_value: currentValue ?? undefined,
          target_value: targetValue ?? undefined,
          confidence: confidence ?? undefined,
          decision,
        }),
      });
      return res.json();
    },
    refetchInterval: 15000,
  });
  const data = q.data || {};
  const checks = (data.checks || {}) as Record<string, boolean>;
  const code = String(data.code || (live.controlEnabled ? '' : 'WRITE_DISABLED'));
  const oid = opportunityId.toUpperCase();
  const special =
    oid === 'O18' ? 'ADVISORY' : oid === 'O19' ? 'MAINTENANCE_ONLY' : oid === 'O20' ? 'REVIEW_REQUIRED' : code;
  const reason = String(data.reason || 'BMS writes are disabled during read-only commissioning.');

  return (
    <section className="kpi-tile space-y-3" aria-label="Dispatch safety">
      <div className="text-[11px] uppercase tracking-wider text-slate-500">Dispatch readiness</div>
      <ul className="space-y-1 text-[12px] font-mono">
        {CHECKS.map((c) => {
          const ok = Boolean(checks[c.key]);
          return (
            <li key={c.key} className={ok ? 'text-emerald-400' : 'text-slate-500'}>
              {ok ? '✓' : '✕'} {ok ? c.okLabel : c.failLabel}
            </li>
          );
        })}
        <li className={live.safeMode ? 'text-rose-300' : 'text-emerald-400'}>
          {live.safeMode ? '✕ SAFE MODE ON' : '✓ SAFE MODE OFF'}
        </li>
        <li className="text-slate-400">SAFETY {String(data.safety || (live.safeMode ? 'HOLD' : 'PASS'))}</li>
        <li className="text-emerald-400">✓ DECISION {decision}</li>
        <li className={confidence != null && confidence >= 0.65 ? 'text-emerald-400' : 'text-slate-500'}>
          {confidence != null && confidence >= 0.65 ? '✓' : '✕'} CONFIDENCE {confidence == null ? '—' : confidence.toFixed(2)}
        </li>
        <li className={currentValue != null ? 'text-emerald-400' : 'text-slate-500'}>
          {currentValue != null ? '✓' : '✕'} CURRENT {currentValue == null ? '—' : currentValue}
        </li>
        <li className={targetValue != null ? 'text-emerald-400' : 'text-slate-500'}>
          {targetValue != null ? '✓' : '✕'} TARGET {targetValue == null ? '—' : targetValue}
        </li>
        <li className="text-rose-300">✕ WRITE DISABLED</li>
      </ul>
      <div className="border border-rose-500/30 bg-rose-950/30 px-3 py-2" role="status">
        <div className="text-[11px] font-semibold text-rose-300">CONTROL BLOCKED</div>
        <div className="text-[11px] font-mono text-rose-200 mt-1">{special || 'WRITE_DISABLED'}</div>
        <p className="text-[11px] text-slate-400 mt-1">{reason}</p>
        {oid === 'O18' && <p className="text-[11px] text-slate-500 mt-1">ADVISORY ONLY</p>}
        {oid === 'O19' && <p className="text-[11px] text-slate-500 mt-1">MAINTENANCE RECORD ONLY</p>}
        {oid === 'O20' && <p className="text-[11px] text-slate-500 mt-1">REVIEW REQUIRED</p>}
      </div>
      <div className="flex flex-wrap gap-2">
        <button type="button" className="btn-secondary text-xs" onClick={() => q.refetch()} title="Refresh dispatch evaluation">
          OPTIMIZE
        </button>
        <button type="button" className="btn-primary text-xs opacity-40" disabled title="WRITE_DISABLED — read-only commissioning mode.">
          APPLY
        </button>
        <button type="button" className="btn-secondary text-xs opacity-40" disabled title="WRITE_DISABLED — read-only commissioning mode.">
          VERIFY
        </button>
        <button type="button" className="btn-danger text-xs opacity-40" disabled title="WRITE_DISABLED — read-only commissioning mode.">
          ROLLBACK
        </button>
      </div>
    </section>
  );
}
