'use client';

import { EngineeringTable } from '@/components/hvac/EngineeringTable';
import { EmptyState } from '@/components/hvac/EmptyState';
import { StatusBadge, toneForStatus } from '@/components/hvac/StatusBadge';
import type { OmOpportunity } from '@/lib/hvac/omTypes';
import { formatDash } from '@/lib/hvac/formatters';
import { o20ControllerField, o20Counts, o20SecondsAgo } from '@/lib/hvac/o20Format';

export function OverridePanel({ data }: { data: OmOpportunity }) {
  const c = o20Counts(data);
  const state = o20ControllerField(data, 'override_state');
  const has = c.overrides != null && c.overrides > 0;
  const status = has ? 'ACTIVE' : state !== '—' && state !== 'NONE' && state !== 'OFF' && state !== 'AUTO' ? 'REVIEW_REQUIRED' : null;
  return (
    <section className="kpi-tile space-y-3" aria-label="Override management">
      <h2 className="text-[11px] uppercase tracking-wider text-slate-500">Override management</h2>
      <p className="text-[11px] text-slate-500">Overrides are not released from this UI. Automatic override clear is not supported.</p>
      {!has && !status ? (
        <EmptyState title="NO DATA AVAILABLE" detail="No per-point override list was returned. Aggregate override count is shown in KPIs when present." />
      ) : (
        <EngineeringTable>
          <thead>
            <tr>
              <th>Point</th>
              <th>Equipment</th>
              <th>Override Value</th>
              <th>Normal/Expected Value</th>
              <th>Duration</th>
              <th>Reason</th>
              <th>Status</th>
              <th>Last Updated</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="font-mono">—</td>
              <td className="font-mono">{o20ControllerField(data, 'controller_id')}</td>
              <td className="font-mono">{formatDash(c.overrides)} active</td>
              <td className="font-mono">AUTO</td>
              <td className="font-mono">—</td>
              <td>{formatDash(data.recommendation?.rationale)}</td>
              <td>
                <StatusBadge tone={toneForStatus(status)}>{status || '—'}</StatusBadge>
              </td>
              <td className="font-mono">{o20SecondsAgo(data.telemetry?.lastUpdated || data.timestamp)}</td>
            </tr>
          </tbody>
        </EngineeringTable>
      )}
    </section>
  );
}
