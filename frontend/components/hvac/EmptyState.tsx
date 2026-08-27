'use client';

import React from 'react';
import Link from 'next/link';

export const EmptyState: React.FC<{
  title?: string;
  detail?: string;
  href?: string;
  actionLabel?: string;
  onRetry?: () => void;
}> = ({
  title = 'NO DATA',
  detail = 'Telemetry is not currently available for this opportunity.',
  href,
  actionLabel,
  onRetry,
}) => (
  <div className="card-static p-6 space-y-3">
    <div className="text-[11px] uppercase tracking-[0.14em] font-semibold text-amber-700">{title}</div>
    <p className="text-[13px] text-slate-500 leading-relaxed max-w-xl">{detail}</p>
    <div className="flex flex-wrap gap-3 pt-1">
      {href && actionLabel ? (
        <Link href={href} className="btn-primary">
          {actionLabel}
        </Link>
      ) : null}
      {onRetry ? (
        <button type="button" className="btn-secondary" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </div>
  </div>
);

export const emptyLabel = (value: unknown, fallback = 'NO DATA'): React.ReactNode =>
  value === null || value === undefined || value === '' ? fallback : (value as React.ReactNode);
