'use client';

import React from 'react';
import { KPIGrid } from '@/components/hvac/KPIGrid';
import type { LucideIcon } from 'lucide-react';

export function KpiRow({
  items,
}: {
  items: {
    label: string;
    value?: React.ReactNode | null;
    detail?: React.ReactNode | null;
    icon?: LucideIcon;
  }[];
}) {
  return <KPIGrid className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4" emptyText="AWAITING TELEMETRY" items={items} />;
}
