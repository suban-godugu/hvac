'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { RotateCcw, ShieldCheck, Zap } from 'lucide-react';
import { OpportunityWorkspace } from '@/components/hvac/guide/OpportunityWorkspace';
import { KPIGrid } from '@/components/hvac/KPIGrid';
import { EmptyState } from '@/components/hvac/EmptyState';
import { StatusBadge, toneForStatus } from '@/components/hvac/StatusBadge';
import {
  EngineeringChart,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  EngineeringTooltip,
  CHART_COLORS,
} from '@/components/hvac/EngineeringChart';
import { getOpportunity } from '@/lib/hvac/opportunityConfig';
import {
  formatKw,
  formatKwh,
  formatPercent,
  formatDash,
  formatConfidence,
  formatHours,
  formatTemperature,
  formatAgeSeconds,
  formatDateTime,
  formatNumber,
} from '@/lib/hvac/formatters';
import { fetchOmOpportunity, postOmAction } from '@/lib/hvac/omApi';
import type { OmOpportunity, OperationsOpportunityId } from '@/lib/hvac/omTypes';
import { metricNum, metricStr } from '@/lib/hvac/omTypes';
import { provenanceFromAgent } from '@/lib/hvac/provenance';
import { actionErrorText } from '@/lib/hvac/actionError';

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-3 py-1.5 text-xs font-mono border-b border-white/[0.04]">
      <span className="text-slate-500">{label}</span>
      <span className="text-slate-100 text-right">{value}</span>
    </div>
  );
}

function finite(n: unknown): number | null {
  if (n === null || n === undefined || n === '') return null;
  const v = typeof n === 'number' ? n : Number(n);
  return Number.isFinite(v) ? v : null;
}

export function OMDetailView({ opportunityId }: { opportunityId: OperationsOpportunityId }) {
  const def = getOpportunity(opportunityId)!;
  const [data, setData] = useState<OmOpportunity | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState<string | null>(null);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      const r = await fetchOmOpportunity(opportunityId, signal);
      if (signal?.aborted) return;
      if (r.data) {
        setData(r.data);
        setError(null);
      } else {
        setData(null);
        setError(r.error === 'API ERROR' ? 'DATA SOURCE ERROR' : r.error === 'NO DATA' ? 'NO DATA' : 'AGENT UNAVAILABLE');
      }
      setLoading(false);
    },
    [opportunityId]
  );

  useEffect(() => {
    let cancelled = false;
    let inFlight: AbortController | null = null;
    const tick = async () => {
      inFlight?.abort();
      const ac = new AbortController();
      inFlight = ac;
      await load(ac.signal);
      if (cancelled) return;
    };
    tick();
    const id = window.setInterval(tick, 5000);
    return () => {
      cancelled = true;
      inFlight?.abort();
      window.clearInterval(id);
    };
  }, [load]);

  const m = data?.metrics;
  const kpis =
    opportunityId === 'O17'
      ? [
          { label: 'Current', value: data ? formatKw(data.current?.kw) : null },
          { label: 'Optimized / Target', value: data ? formatKw(data.current?.targetKw) : null },
          { label: 'Energy Impact', value: data ? formatKwh(data.energy?.dailyKwh) : null },
          { label: 'Confidence', value: data ? formatConfidence(data.confidence) : null },
          { label: 'Status', value: data ? formatDash(data.status) : null },
        ]
      : opportunityId === 'O18'
        ? [
            { label: 'Current', value: data ? formatPercent(data.current?.trainingCoveragePct) : null },
            { label: 'Optimized / Target', value: data ? formatDash(data.current?.operatorReadiness) : null },
            { label: 'Energy Impact', value: data ? formatKwh(data.energy?.impactKwhDay) : null },
            { label: 'Confidence', value: data ? formatConfidence(data.confidence) : null },
            { label: 'Status', value: data ? formatDash(data.status) : null },
          ]
        : opportunityId === 'O19'
          ? [
              { label: 'Current', value: data ? formatPercent(data.current?.equipmentHealthPct) : null },
              { label: 'Optimized / Target', value: data ? formatDash(data.current?.maintenanceRisk) : null },
              { label: 'Energy Impact', value: data ? formatKw(data.energy?.impactKw) : null },
              { label: 'Confidence', value: data ? formatConfidence(data.confidence) : null },
              { label: 'Status', value: data ? formatDash(data.status) : null },
            ]
          : [
              { label: 'Current', value: data ? formatPercent(data.current?.controlHealthPct) : null },
              { label: 'Optimized / Target', value: data ? formatDash(data.current?.controllerHealth) : null },
              { label: 'Energy Impact', value: data ? formatDash(data.current?.criticalIssues) : null },
              { label: 'Confidence', value: data ? formatConfidence(data.confidence) : null },
              { label: 'Status', value: data ? formatDash(data.status) : null },
            ];

  const engineering =
    opportunityId === 'O17'
      ? [
          ['Energy baseline', formatKw(data?.energy?.baselineKw)],
          ['Operating occupancy', formatDash(data?.current?.occupancy)],
          ['Demand / peak', formatKw(data?.energy?.peakDemandKw)],
          ['Runtime energy', formatKwh(metricNum(m, 'daily_energy_kwh'), false)],
          ['Setpoint / target', formatKw(data?.energy?.targetKw)],
          ['Outdoor temperature', formatTemperature(metricNum(m, 'outdoor_temp_c'))],
          ['Telemetry age', formatAgeSeconds(data?.telemetry?.ageSeconds)],
        ]
      : opportunityId === 'O18'
        ? [
            ['Training topics / items', formatDash(data?.current?.trainingItems)],
            ['Operator groups / users', formatDash(data?.current?.affectedUsers)],
            ['Awareness / coverage', formatPercent(data?.current?.trainingCoveragePct)],
            ['Operational behavior (overrides)', formatDash(metricNum(m, 'manual_override_count'))],
            ['Training completion', formatPercent(data?.current?.trainingCoveragePct)],
            ['Energy impact', formatKwh(data?.energy?.impactKwhDay)],
            ['Telemetry age', formatAgeSeconds(data?.telemetry?.ageSeconds)],
          ]
        : opportunityId === 'O19'
          ? [
              ['Equipment', formatDash(metricStr(m, 'equipment_id') || metricStr(m, 'equipmentId'))],
              ['Runtime', formatHours(metricNum(m, 'runtime_hours'))],
              ['Differential pressure', formatPercent(metricNum(m, 'filter_dp_rise_pct'))],
              ['Filter / fan', formatKw(metricNum(m, 'fan_power_kw'))],
              ['Sensor drift', formatPercent(metricNum(m, 'sensor_drift_pct'))],
              ['Coil / valve / damper', formatDash(metricStr(m, 'maintenance_risk'))],
              ['Telemetry age', formatAgeSeconds(data?.telemetry?.ageSeconds)],
            ]
          : [
              ['Controller', formatDash(metricStr(m, 'controller_id'))],
              ['Control points', formatNumber(data?.current?.controlPoints, 0)],
              ['Override count', formatDash(data?.current?.overrides)],
              ['Configuration version', formatDash(data?.current?.softwareVersion)],
              ['Alarms', formatDash(metricStr(m, 'alarm_status'))],
              ['Software state', formatDash(data?.current?.controllerHealth)],
              ['Configuration drift', formatPercent(metricNum(m, 'config_drift_pct'))],
              ['Telemetry age', formatAgeSeconds(data?.telemetry?.ageSeconds)],
            ];

  const chartRows =
    opportunityId === 'O17'
      ? [
          { name: 'Actual', value: finite(data?.charts?.currentKw ?? data?.current?.kw) },
          { name: 'Baseline', value: finite(data?.charts?.baselineKw ?? data?.current?.baselineKw) },
          { name: 'Target', value: finite(data?.charts?.targetKw ?? data?.current?.targetKw) },
        ]
      : opportunityId === 'O18'
        ? [
            { name: 'Completion', value: finite(data?.charts?.trainingCompletion ?? data?.current?.trainingCoveragePct) },
            { name: 'Items', value: finite(data?.charts?.trainingItems ?? data?.current?.trainingItems) },
          ]
        : opportunityId === 'O19'
          ? [
              { name: 'Health', value: finite(data?.charts?.equipmentHealthPct ?? data?.current?.equipmentHealthPct) },
              { name: 'Findings', value: finite(data?.charts?.maintenanceAlerts ?? data?.current?.maintenanceAlerts) },
              { name: 'Loss kW', value: finite(data?.charts?.energyLossKw ?? data?.energy?.impactKw) },
            ]
          : [
              { name: 'Healthy', value: finite(data?.charts?.healthyPoints ?? data?.current?.healthyPoints) },
              { name: 'Degraded', value: finite(data?.charts?.degradedPoints ?? data?.current?.degradedPoints) },
              { name: 'Overrides', value: finite(data?.charts?.overrides ?? data?.current?.overrides) },
              { name: 'Drift', value: finite(data?.charts?.driftCount ?? data?.current?.driftCount) },
            ];
  const chartData = chartRows.filter((r) => r.value !== null) as { name: string; value: number }[];

  const primaryAction =
    opportunityId === 'O17' ? 'dispatch' : opportunityId === 'O18' ? 'training-action' : opportunityId === 'O19' ? 'maintenance-action' : 'change-request';
  const primaryLabel =
    opportunityId === 'O17'
      ? 'Dispatch Plan'
      : opportunityId === 'O18'
        ? 'Create Training Action'
        : opportunityId === 'O19'
          ? 'Create Maintenance Action'
          : 'Submit Change Request';

  const agentState = data?.metadata?.agent || (error === 'AGENT UNAVAILABLE' ? 'DEGRADED' : loading ? 'WAITING' : 'ACTIVE');

  return (
    <OpportunityWorkspace
      def={def}
      live={provenanceFromAgent(data as unknown as Record<string, unknown>)}
      bms={data?.bmsConnected ? 'CONNECTED' : 'OFFLINE'}
      actions={
        data?.failSafe?.available ? (
          <button
            className="btn-danger"
            onClick={async () => {
              try {
                await postOmAction(opportunityId, 'rollback');
                load();
              } catch {
                /* 409 surfaces via reload */
              }
            }}
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Fail-Safe Rollback
          </button>
        ) : undefined
      }
    >
      {data && (
        <div className="flex flex-wrap gap-2 text-[11px] font-mono -mt-2">
          <StatusBadge tone={toneForStatus(data.status)}>{formatDash(data.status)}</StatusBadge>
          <StatusBadge tone={toneForStatus(data.telemetry?.state)}>TEL {formatDash(data.telemetry?.state)}</StatusBadge>
          <StatusBadge tone="muted">UPDATED {formatAgeSeconds(data.telemetry?.ageSeconds)}</StatusBadge>
          <StatusBadge tone={toneForStatus(data.supervisory?.decision)}>{formatDash(data.supervisory?.decision)}</StatusBadge>
          <StatusBadge tone={toneForStatus(data.safety?.status)}>SAFETY {formatDash(data.safety?.status)}</StatusBadge>
        </div>
      )}

      {loading && !data && <EmptyState title="LOADING TELEMETRY..." detail="Requesting O17–O20 state from the Operations & Maintenance API." />}
      {error && !data && !loading && (
        <EmptyState title={error} detail="No fabricated Current/Optimized values are shown while the data source is unavailable." />
      )}

      {data && <KPIGrid emptyText={loading ? 'LOADING TELEMETRY...' : '—'} items={kpis} />}

      {data && (
        <div className="kpi-tile">
          <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-3">Safety / Data Quality</div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
            <div>
              <div className="text-slate-500">Telemetry</div>
              <div className="text-slate-100">{formatDash(data.telemetry?.state)}</div>
            </div>
            <div>
              <div className="text-slate-500">Data Quality</div>
              <div className="text-slate-100">{formatDash(data.telemetry?.quality || data.metadata?.dataQuality)}</div>
            </div>
            <div>
              <div className="text-slate-500">Safety</div>
              <div className="text-slate-100">{formatDash(data.safety?.status)}</div>
            </div>
            <div>
              <div className="text-slate-500">Agent</div>
              <div className="text-slate-100">{formatDash(agentState)}</div>
            </div>
          </div>
        </div>
      )}

      {data && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="kpi-tile">
            <div className="text-[11px] uppercase tracking-wider text-slate-500">AI Agent Recommendation</div>
            <div className="text-lg font-mono text-cyan-300 mt-2">{formatDash(data.recommendation?.action)}</div>
            <p className="text-sm text-slate-300 mt-2">{formatDash(data.recommendation?.rationale)}</p>
            <div className="mt-3 space-y-0">
              <Row label="Expected impact" value={opportunityId === 'O18' ? formatKwh(data.energy?.impactKwhDay) : formatKw(data.recommendation?.expectedImpactKw ?? data.energy?.savingKw ?? data.energy?.impactKw)} />
              <Row label="Confidence" value={formatConfidence(data.recommendation?.confidence)} />
              <Row label="Priority" value={formatDash(data.recommendation?.priority || data.priority)} />
              <Row label="Timestamp" value={formatDash(data.recommendation?.timestamp)} />
            </div>
          </div>
          <div className="kpi-tile">
            <div className="text-[11px] uppercase tracking-wider text-slate-500 flex items-center gap-2">
              <ShieldCheck className="w-3.5 h-3.5" /> Supervisory Decision
            </div>
            <div className="text-lg font-mono text-emerald-300 mt-2">{formatDash(data.supervisory?.decision)}</div>
            <p className="text-sm text-slate-300 mt-2">{formatDash(data.supervisory?.reason)}</p>
            <div className="mt-3 space-y-0">
              <Row label="Current state" value={formatDash(data.supervisory?.currentState || data.status)} />
              <Row label="Recommended state" value={formatDash(data.supervisory?.recommendedState)} />
              <Row label="Confidence" value={formatConfidence(data.supervisory?.confidence)} />
              <Row label="Safety guardrail" value={formatDash(data.supervisory?.safety)} />
              <Row label="Dispatch eligibility" value={formatDash(data.dispatch?.eligible ? 'ELIGIBLE' : data.dispatch?.blockReason)} />
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                className="btn-primary"
                disabled={opportunityId === 'O17' ? !data.dispatch?.eligible : false}
                onClick={async () => {
                  setAction('WORKING');
                  try {
                    await postOmAction(opportunityId, primaryAction, { topic: data.recommendation?.action });
                    setAction('RECORDED');
                  } catch (e) {
                    setAction(actionErrorText(e, 'BLOCKED'));
                  }
                  setTimeout(() => setAction(null), 4000);
                  load();
                }}
              >
                <Zap className="w-3.5 h-3.5" />
                {action || primaryLabel}
              </button>
              <button
                className="btn-ghost"
                onClick={async () => {
                  try {
                    await postOmAction(opportunityId, 'verify');
                    load();
                  } catch {
                    /* ignore */
                  }
                }}
              >
                Verify
              </button>
            </div>
          </div>
        </div>
      )}

      {data && (
        <div className="kpi-tile">
          <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-2">Trend / Snapshot</div>
          {chartData.length === 0 ? (
            <div className="text-xs font-mono text-amber-300/90">NO DATA</div>
          ) : (
            <EngineeringChart height={200}>
              <BarChart data={chartData}>
                <CartesianGrid stroke={CHART_COLORS.grid} vertical={false} />
                <XAxis dataKey="name" stroke={CHART_COLORS.axis} tick={{ fontSize: 10 }} />
                <YAxis stroke={CHART_COLORS.axis} tick={{ fontSize: 10 }} width={40} />
                <Tooltip content={<EngineeringTooltip />} />
                <Bar dataKey="value" fill={CHART_COLORS.current} radius={[2, 2, 0, 0]} />
              </BarChart>
            </EngineeringChart>
          )}
        </div>
      )}

      {data && (
        <div className="kpi-tile">
          <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-3">Engineering Inputs</div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8">
            {engineering.map(([label, value]) => (
              <Row key={label} label={label} value={value} />
            ))}
          </div>
        </div>
      )}

      {data && data.failSafe?.available && (
        <div className="kpi-tile">
          <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-3">Fail-Safe Rollback</div>
          <Row label="Policy" value={formatDash(data.failSafe.policy)} />
          <Row label="Requested state" value={formatDash(data.failSafe.requestedState)} />
          <Row label="Rollback state" value={formatDash(data.failSafe.rollbackState)} />
        </div>
      )}

      {data && (
        <div className="kpi-tile">
          <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-3">Audit History</div>
          {(data.audit || []).length === 0 ? (
            <div className="text-xs font-mono text-slate-500">—</div>
          ) : (
            <div className="space-y-2">
              {data.audit!.slice(0, 8).map((a, i) => (
                <div key={`${a.timestamp}-${i}`} className="text-[11px] font-mono border-b border-white/[0.04] pb-2">
                  <div className="text-cyan-300">{formatDash(a.event_type)} · {formatDateTime(a.timestamp)}</div>
                  <div className="text-slate-400">{formatDash(a.message)}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </OpportunityWorkspace>
  );
}
