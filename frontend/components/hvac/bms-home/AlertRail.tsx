'use client';

import React from 'react';
import Link from 'next/link';
import { mappingHref, type DashboardAlert } from '@/lib/hvac/dashboardHome';

function ageLabel(age?: number | null) {
  if (age == null) return '';
  if (age < 60) return `${Math.round(age)}s`;
  if (age < 3600) return `${Math.round(age / 60)}m`;
  return `${Math.round(age / 3600)}h`;
}

export function AlertRail({ alerts }: { alerts?: DashboardAlert[] }) {
  const rows = alerts || [];
  return (
    <section className="glass-card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">Alerts</div>
        <span className="text-[10px] font-mono text-slate-500">{rows.length}</span>
      </div>
      {rows.length === 0 ? (
        <p className="text-[12px] text-slate-500">No stale, bad, BMS, or maintenance alerts.</p>
      ) : (
        <ul className="space-y-2 max-h-56 overflow-y-auto">
          {rows.map((a, i) => {
            const href = a.equipment_id ? mappingHref(a.equipment_id, a.point_id?.includes('.') ? a.point_id.split('.').slice(1).join('.') : undefined) : '/platform/bms';
            return (
              <li key={`${a.severity}-${a.point_id || a.equipment_id || i}`}>
                <Link href={href} className="flex items-start justify-between gap-2 text-[11px] hover:text-cyan-200">
                  <span>
                    <span className="font-mono text-amber-200/90">{a.severity}</span>{' '}
                    <span className="text-slate-300">{a.point_id || a.equipment_id || a.message}</span>
                    {a.message && a.point_id ? <span className="block text-slate-500 mt-0.5">{a.message}</span> : null}
                  </span>
                  <span className="font-mono text-slate-600 shrink-0">{ageLabel(a.age_seconds)}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
