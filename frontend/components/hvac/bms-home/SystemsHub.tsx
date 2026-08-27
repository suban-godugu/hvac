'use client';

import React from 'react';
import Link from 'next/link';
import { HUB_RAIL, type DashboardChapter } from '@/lib/hvac/dashboardHome';

export function SystemsHub({
  chapters,
  variant = 'compact',
}: {
  chapters?: DashboardChapter[];
  variant?: 'compact' | 'full';
}) {
  const rows = chapters || [];
  if (rows.length === 0) return null;

  return (
    <div className={variant === 'full' ? 'grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4' : 'grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-3'}>
      {rows.map((ch) => {
        const practice = ch.opportunities.find((o) => o.practice)?.practice;
        const color = HUB_RAIL[ch.id] || 'var(--accent-cyan)';
        return (
          <Link
            key={ch.id}
            href={ch.href}
            className="glass-card p-4 hover:border-cyan-400/30 transition-colors"
            style={{ borderTopWidth: 3, borderTopColor: color }}
          >
            <div className="text-[11px] font-semibold text-slate-100">{ch.title}</div>
            <div className="text-[10px] text-slate-500 mt-1 line-clamp-2">{ch.section}</div>
            <div className="mt-3 text-[10px] font-mono text-slate-400">
              {ch.counts.live} LIVE · {ch.counts.simulated} SIM · {ch.counts.awaiting} AWAITING
            </div>
            {variant === 'full' && practice ? (
              <p className="text-[11px] text-slate-500 mt-2 line-clamp-3">{practice}</p>
            ) : null}
            <div className="mt-2 flex flex-wrap gap-1">
              {ch.opportunities.slice(0, variant === 'full' ? 5 : 4).map((o) => (
                <span key={o.id} className="text-[9px] font-mono px-1 py-0.5 rounded border border-white/10 text-slate-400">
                  {o.id}
                </span>
              ))}
            </div>
            {variant === 'full' ? (
              <p className="text-[9px] font-mono text-slate-600 mt-2">GUIDE_POTENTIAL · non-cumulative</p>
            ) : null}
          </Link>
        );
      })}
    </div>
  );
}
