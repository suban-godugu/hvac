'use client';

import React from 'react';
import { KPIGrid } from '@/components/hvac/KPIGrid';
import { SavingsSummary } from '@/lib/types';
import { Zap, DollarSign, ShieldCheck, Award } from 'lucide-react';

interface KPIOverviewProps {
  savings?: SavingsSummary;
}

export const KPIOverview: React.FC<KPIOverviewProps> = ({ savings }) => (
  <KPIGrid
    items={[
      {
        label: 'Verified Energy Saved',
        value: savings?.verified_kw != null ? `${Number(savings.verified_kw).toFixed(1)} kW` : null,
        detail: savings?.verified_kwh_today != null ? `${Number(savings.verified_kwh_today).toFixed(1)} kWh today` : null,
        icon: Award,
      },
      {
        label: 'Applied Control Shed',
        value: savings?.applied_kw != null ? `${Number(savings.applied_kw).toFixed(1)} kW` : null,
        icon: Zap,
      },
      {
        label: 'Verified Cost Saved',
        value: savings?.verified_cost_saved_usd != null ? `$${Number(savings.verified_cost_saved_usd).toFixed(2)}` : null,
        detail: savings?.predicted_kw != null ? `Predicted ${Number(savings.predicted_kw).toFixed(1)} kW` : null,
        icon: DollarSign,
      },
      {
        label: 'Comfort Compliance',
        value: savings?.comfort_compliance_pct != null ? `${Number(savings.comfort_compliance_pct).toFixed(1)}%` : null,
        icon: ShieldCheck,
      },
    ]}
  />
);
