'use client';

import React from 'react';
import Link from 'next/link';

export const EmptyState: React.FC<{
  title?: string;
  detail?: string;
  href?: string;
  actionLabel?: string;
}> = ({
  title = 'NO DATA',
  detail = 'Telemetry is not currently available for this opportunity.',
  href,
  actionLabel,
}) => (
  <div className="glass-card p-6 space-y-2">
    <div className="text-[11px] uppercase tracking-[0.14em] font-semibold text-amber-200">{title}</div>
    <p className="text-[13px] text-slate-400 leading-relaxed max-w-xl">{detail}</p>
    {href && actionLabel ? (
      <Link href={href} className="inline-flex text-[12px] font-semibold text-cyan-300 hover:text-cyan-200 pt-1">
        {actionLabel} →
      </Link>
    ) : null}
  </div>
);

export const emptyLabel = (value: unknown, fallback = 'NO DATA'): React.ReactNode =>
  value === null || value === undefined || value === '' ? fallback : (value as React.ReactNode);
