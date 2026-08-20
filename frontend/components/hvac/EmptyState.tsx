'use client';

import React from 'react';

export const EmptyState: React.FC<{ title?: string; detail?: string }> = ({
  title = 'NO DATA',
  detail = 'Telemetry is not currently available for this opportunity.',
}) => (
  <div className="kpi-tile justify-center items-start">
    <div className="text-[11px] uppercase tracking-[0.14em] font-semibold text-amber-200">{title}</div>
    <p className="text-[12px] text-slate-500 mt-1.5 leading-relaxed">{detail}</p>
  </div>
);

export const emptyLabel = (value: unknown, fallback = 'NO DATA'): React.ReactNode =>
  value === null || value === undefined || value === '' ? fallback : (value as React.ReactNode);
