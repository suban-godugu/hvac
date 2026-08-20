'use client';

import { EngineeringTable } from '@/components/hvac/EngineeringTable';
import { EmptyState } from '@/components/hvac/EmptyState';
import { StatusBadge, toneForStatus } from '@/components/hvac/StatusBadge';
import type { OmOpportunity } from '@/lib/hvac/omTypes';
import { formatDash, formatPercent } from '@/lib/hvac/formatters';
import { o20ControllerField, o20Counts } from '@/lib/hvac/o20Format';

export function ControlDriftPanel({ data }: { data: OmOpportunity }) {
  const c = o20Counts(data);
  if (c.driftPct == null && c.drift == null) {
    return (
      <section className="kpi-tile" aria-label="Control drift">
        <h2 className="text-[11px] uppercase tracking-wider text-slate-500 mb-2">Control drift</h2>
        <EmptyState title="NO DATA AVAILABLE" detail="Configuration drift percentage and drift count were not returned." />
      </section>
    );
  }
  const rec = (data.recommendation?.action || '').toUpperCase();
  const severity =
    rec === 'MAINTAIN_BASELINE'
      ? 'NORMAL'
      : rec.includes('INVESTIGATE')
        ? 'MONITOR'
        : rec === 'OPEN_CHANGE_REQUEST' || rec === 'RESTORE_FAILED_POINTS' || rec === 'RESTORE_COMMUNICATION'
          ? 'CORRECTION_REQUIRED'
          : rec
            ? 'REVIEW_REQUIRED'
            : 'REVIEW_REQUIRED';
  return (
    <section className="kpi-tile space-y-3" aria-label="Control drift">
      <h2 className="text-[11px] uppercase tracking-wider text-slate-500">Control drift</h2>
      <EngineeringTable>
        <thead>
          <tr>
            <th>Point</th>
            <th>Observed behavior</th>
            <th>Expected behavior</th>
            <th>Deviation</th>
            <th>Duration</th>
            <th>Severity</th>
            <th>Recommendation</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td className="font-mono">{o20ControllerField(data, 'controller_id')} config</td>
            <td className="font-mono">{c.driftPct == null ? `${formatDash(c.drift)} drifted pts` : formatPercent(c.driftPct)}</td>
            <td>Approved baseline configuration</td>
            <td className="font-mono">{c.driftPct == null ? '—' : formatPercent(c.driftPct)}</td>
            <td className="font-mono">—</td>
            <td>
              <StatusBadge tone={toneForStatus(severity)}>{severity}</StatusBadge>
            </td>
            <td>{formatDash(data.recommendation?.action)}</td>
          </tr>
        </tbody>
      </EngineeringTable>
    </section>
  );
}
