'use client';

import { EngineeringTable } from '@/components/hvac/EngineeringTable';
import { EmptyState } from '@/components/hvac/EmptyState';
import { StatusBadge, toneForStatus } from '@/components/hvac/StatusBadge';
import type { OmOpportunity } from '@/lib/hvac/omTypes';
import { formatDash, formatPercent } from '@/lib/hvac/formatters';
import { o18Bucket, o18Completions } from '@/lib/hvac/o18Format';

export function AffectedUsersTable({ data }: { data: OmOpportunity }) {
  const completions = o18Completions(data);
  const rows: Array<{ role: string; count: number; completion: number | null; pending: number; status: string }> = [];
  if (completions) {
    const byRole = new Map<string, { count: number; pct: number[]; pending: number; statuses: string[] }>();
    for (const c of completions) {
      if (!c.roleLabel) continue;
      const cur = byRole.get(c.roleLabel) || { count: 0, pct: [], pending: 0, statuses: [] };
      cur.count += 1;
      if (c.completionPct != null) cur.pct.push(c.completionPct);
      const bucket = o18Bucket(c.status);
      if (bucket !== 'Completed') cur.pending += 1;
      if (c.status) cur.statuses.push(c.status);
      byRole.set(c.roleLabel, cur);
    }
    for (const [role, v] of byRole) {
      const avg = v.pct.length ? v.pct.reduce((a, b) => a + b, 0) / v.pct.length : null;
      rows.push({
        role,
        count: v.count,
        completion: avg,
        pending: v.pending,
        status: v.pending > 0 ? 'PENDING' : 'COMPLETE',
      });
    }
  }

  return (
    <section className="kpi-tile space-y-3" aria-label="Affected users">
      <h2 className="text-[11px] uppercase tracking-wider text-slate-500">Affected users</h2>
      <p className="text-[11px] text-slate-500">Role-level completion records only. No login or account management.</p>
      {!completions || rows.length === 0 ? (
        <EmptyState title="NO DATA AVAILABLE" detail="No role_label completion records were returned. User counts are not invented." />
      ) : (
        <EngineeringTable>
          <thead>
            <tr>
              <th>Role</th>
              <th>Affected Count</th>
              <th>Completion</th>
              <th>Pending</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.role}>
                <td className="font-mono">{r.role}</td>
                <td className="font-mono">{r.count}</td>
                <td className="font-mono">{formatPercent(r.completion)}</td>
                <td className="font-mono">{r.pending}</td>
                <td>
                  <StatusBadge tone={toneForStatus(r.status)}>{r.status}</StatusBadge>
                </td>
              </tr>
            ))}
          </tbody>
        </EngineeringTable>
      )}
      <p className="text-[10px] font-mono text-slate-600">Reported affected users {formatDash(data.current?.affectedUsers)}</p>
    </section>
  );
}
