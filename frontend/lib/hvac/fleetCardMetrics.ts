import type { ReactNode } from 'react';
import type { OpportunityCardField } from '@/components/hvac/OpportunityCard';
import type { PlantControlDashboardState } from '@/lib/plantControlApi';
import type { VentilationDashboardData, VentilationOpportunity } from '@/lib/hvac/ventilationTypes';
import type { OmDashboardData, OmOpportunity } from '@/lib/hvac/omTypes';
import { formatCfm, formatKw, formatKwh, formatPercent, formatPpm, formatDash } from '@/lib/hvac/formatters';
import { metricStr } from '@/lib/hvac/ventilationTypes';
import { provenanceFromAgent } from '@/lib/hvac/provenance';
import { fmtDash, fmtUnit } from '@/lib/hvac/o15Format';

export type FleetCardMetrics = {
  status?: string | null;
  fields: OpportunityCardField[];
  telemetryLabel?: string | null;
  impactLabel?: string;
  impactValue?: ReactNode | null;
};

function field(label: string, value: unknown): OpportunityCardField | null {
  if (value === null || value === undefined || value === '' || value === '—') return null;
  return { label, value: value as ReactNode };
}

function pack(fields: (OpportunityCardField | null)[], extra?: Partial<FleetCardMetrics>): FleetCardMetrics {
  return {
    fields: fields.filter((f): f is OpportunityCardField => Boolean(f)),
    ...extra,
  };
}

function ventOpp(data: VentilationDashboardData | null | undefined, id: string): VentilationOpportunity | undefined {
  return data?.opportunities?.find((o) => o.id === id || o.opportunityId === id);
}

function omOpp(data: OmDashboardData | null | undefined, id: string): OmOpportunity | undefined {
  return data?.opportunities?.find((o) => o.id === id || o.opportunityId === id);
}

export function fleetCardFor(
  id: string,
  sources: {
    scheduling?: Record<string, unknown> | null;
    plant?: PlantControlDashboardState | null;
    vent?: VentilationDashboardData | null;
    o14?: Record<string, unknown> | null;
    o15?: Record<string, unknown> | null;
    o16?: Record<string, unknown> | null;
    om?: OmDashboardData | null;
  }
): FleetCardMetrics {
  if (id === 'O1' || id === 'O2' || id === 'O3' || id === 'O4') {
    const live = sources.scheduling;
    if (!live) return pack([]);
    const primary = live.primaryMetric as { label?: string; value?: unknown; unit?: string | null } | undefined;
    const secondaries = (live.secondaryMetrics as { label?: string; value?: unknown; unit?: string | null }[]) || [];
    const pVal = primary?.value != null && primary.value !== '' ? `${primary.value}${primary.unit ? ` ${primary.unit}` : ''}` : null;
    const impact = (live.impact as { energy?: unknown } | undefined)?.energy ?? live.energyImpact;
    return pack(
      [
        field(primary?.label || 'Using', pVal),
        ...secondaries.slice(0, 2).map((m) =>
          field(m.label || 'Metric', m.value != null && m.value !== '' ? `${m.value}${m.unit ? ` ${m.unit}` : ''}` : null)
        ),
      ],
      {
        status: (live.status as string) || null,
        telemetryLabel: ((live.telemetry as { label?: string } | undefined)?.label as string) || (live.dataState as string) || null,
        impactLabel: impact != null && impact !== '' ? 'Save' : undefined,
        impactValue: impact != null && impact !== '' ? String(impact) : null,
      }
    );
  }

  const plant = sources.plant;
  const plantOpp = (code: string) =>
    (plant as { opportunities?: { code?: string; current?: string; optimized?: string; status?: string; shed_kw?: number }[] } | null)?.opportunities?.find(
      (o) => String(o.code || '').toUpperCase().startsWith(code)
    );

  if (id === 'O5' && (plant?.o5_summary || plantOpp('O5'))) {
    const s = plant?.o5_summary || {
      current: plantOpp('O5')?.current,
      optimized: plantOpp('O5')?.optimized,
      status: plantOpp('O5')?.status,
      power_shed_kw: plantOpp('O5')?.shed_kw,
    };
    return pack([field('Using', s.current), field('Optimized', s.optimized)], {
      status: s.status,
      impactLabel: 'Save',
      impactValue: s.power_shed_kw != null ? formatKw(s.power_shed_kw, true) : null,
    });
  }
  if (id === 'O6' && (plant?.o6_summary || plantOpp('O6'))) {
    const s = plant?.o6_summary || {
      current: plantOpp('O6')?.current,
      optimized: plantOpp('O6')?.optimized,
      status: plantOpp('O6')?.status,
      power_shed_kw: plantOpp('O6')?.shed_kw,
    };
    return pack([field('Using', s.current), field('Optimized', s.optimized)], {
      status: s.status,
      impactLabel: 'Save',
      impactValue: s.power_shed_kw != null ? formatKw(s.power_shed_kw, true) : null,
    });
  }
  if (id === 'O7' && (plant?.o7_summary || plantOpp('O7'))) {
    const s = plant?.o7_summary || {
      current: plantOpp('O7')?.current,
      optimized: plantOpp('O7')?.optimized,
      status: plantOpp('O7')?.status,
      power_shed_kw: plantOpp('O7')?.shed_kw,
    };
    return pack([field('Using', s.current), field('Optimized', s.optimized)], {
      status: s.status,
      impactLabel: 'Save',
      impactValue: s.power_shed_kw != null ? formatKw(s.power_shed_kw, true) : null,
    });
  }
  if (id === 'O8' && (plant?.o8_summary || plantOpp('O8'))) {
    const s = plant?.o8_summary || {
      current: plantOpp('O8')?.current,
      optimized: plantOpp('O8')?.optimized,
      status: plantOpp('O8')?.status,
      power_shed_kw: plantOpp('O8')?.shed_kw,
    };
    return pack([field('Using', s.current), field('Optimized', s.optimized)], {
      status: s.status,
      impactLabel: 'Save',
      impactValue: s.power_shed_kw != null ? formatKw(s.power_shed_kw, true) : null,
    });
  }
  if (id === 'O9' && (plant?.o9_summary || plantOpp('O9'))) {
    const s = plant?.o9_summary;
    const opp = plantOpp('O9');
    return pack(
      [
        field('Payback', s?.payback_years != null ? `${s.payback_years} yr` : null),
        field('ROI', s?.roi_pct != null ? `${s.roi_pct}%` : null),
        field('Using', !s ? opp?.current : null),
        field('Recommended', !s ? opp?.optimized : null),
      ],
      {
        status: s?.status || opp?.status,
        impactLabel: 'Save',
        impactValue: s?.annual_savings_usd != null ? `$${s.annual_savings_usd}` : null,
      }
    );
  }

  const vo = ventOpp(sources.vent, id);
  if (id === 'O10' && vo) {
    return pack(
      [
        field('Using', formatPercent(vo.current?.damperPct)),
        field('Optimized', formatPercent(vo.optimized?.damperPct)),
        field('Economizer', metricStr(vo.metrics, 'economizer_status')),
      ],
      {
        status: vo.status,
        telemetryLabel: provenanceFromAgent(vo as unknown as Record<string, unknown>),
        impactLabel: 'Save',
        impactValue: formatKw(vo.energy?.savingKw ?? vo.energy?.instantaneousKw),
      }
    );
  }
  if (id === 'O11' && vo) {
    return pack(
      [
        field('Using', formatCfm(vo.current?.airflowCfm)),
        field('Optimized', formatCfm(vo.optimized?.airflowCfm)),
        field('Eligibility', metricStr(vo.metrics, 'eligibility')),
      ],
      {
        status: vo.status,
        telemetryLabel: provenanceFromAgent(vo as unknown as Record<string, unknown>),
        impactLabel: 'Save',
        impactValue: formatKw(vo.energy?.savingKw ?? vo.energy?.instantaneousKw),
      }
    );
  }
  if (id === 'O12' && vo) {
    return pack(
      [
        field('Using', formatCfm(vo.current?.airflowCfm)),
        field('Optimized', formatCfm(vo.optimized?.airflowCfm)),
        field('CO₂', formatPpm(vo.current?.co2Ppm)),
      ],
      {
        status: vo.status,
        telemetryLabel: provenanceFromAgent(vo as unknown as Record<string, unknown>),
        impactLabel: 'Save',
        impactValue: formatKw(vo.energy?.savingKw ?? vo.energy?.instantaneousKw),
      }
    );
  }
  if (id === 'O13' && vo) {
    return pack(
      [
        field('Using', formatCfm(vo.current?.airflowCfm)),
        field('Optimized', formatCfm(vo.optimized?.airflowCfm)),
        field('CO', formatPpm(vo.current?.coPpm)),
      ],
      {
        status: vo.status,
        telemetryLabel: provenanceFromAgent(vo as unknown as Record<string, unknown>),
        impactLabel: 'Save',
        impactValue: formatKw(vo.energy?.savingKw ?? vo.energy?.instantaneousKw),
      }
    );
  }

  if (id === 'O14' && sources.o14) {
    const d = sources.o14;
    const cur = (d.current_state as Record<string, unknown> | undefined) || {};
    const opt = (d.optimized_state as Record<string, unknown> | undefined) || {};
    return pack(
      [
        field('Using', fmtDash(cur.dp_setpoint)),
        field('Optimized', fmtDash(opt.recommended_dp_setpoint)),
      ],
      {
        status: (d.recommendation_state as string) || (d.status as string),
        telemetryLabel: provenanceFromAgent(d),
        impactLabel: 'Save',
        impactValue: formatKw(d.energySavingKw ?? (d.energy as { instantaneousKw?: unknown } | undefined)?.instantaneousKw),
      }
    );
  }
  if (id === 'O15' && sources.o15) {
    const d = sources.o15;
    const cur = (d.current_state as Record<string, unknown> | undefined) || {};
    return pack(
      [
        field('Using', fmtUnit(cur.head_pressure, 'psig')),
        field('Fan', fmtUnit(cur.fan_speed_pct, '%')),
      ],
      {
        status: (d.recommendation_state as string) || (d.status as string),
        telemetryLabel: provenanceFromAgent(d),
        impactLabel: 'Save',
        impactValue: formatKw(d.energySavingKw ?? (d.energy as { instantaneousKw?: unknown } | undefined)?.instantaneousKw),
      }
    );
  }
  if (id === 'O16' && sources.o16) {
    const d = sources.o16;
    const cur = (d.current_state as Record<string, unknown> | undefined) || {};
    return pack(
      [
        field('Using', fmtUnit(cur.head_pressure, 'psig')),
        field('Pump', fmtUnit(cur.pump_speed_pct, '%')),
      ],
      {
        status: (d.recommendation_state as string) || (d.status as string),
        telemetryLabel: provenanceFromAgent(d),
        impactLabel: 'Save',
        impactValue: formatKw(d.energySavingKw ?? (d.energy as { instantaneousKw?: unknown } | undefined)?.instantaneousKw),
      }
    );
  }

  const om = omOpp(sources.om, id);
  if (id === 'O17' && om) {
    return pack(
      [
        field('Using', formatKw(om.energy?.currentKw ?? om.current?.kw)),
        field('Baseline', formatKw(om.energy?.baselineKw ?? om.current?.baselineKw)),
        field('Target', formatKw(om.energy?.targetKw ?? om.current?.targetKw)),
      ],
      {
        status: om.status,
        telemetryLabel: provenanceFromAgent(om as unknown as Record<string, unknown>),
        impactLabel: 'Save',
        impactValue: formatKw(om.energy?.savingKw),
      }
    );
  }
  if (id === 'O18' && om) {
    return pack(
      [
        field('Using', formatPercent(om.current?.trainingCoveragePct)),
        field('Readiness', formatDash(om.current?.operatorReadiness)),
        field('Items', formatDash(om.current?.trainingItems)),
      ],
      {
        status: om.status,
        telemetryLabel: provenanceFromAgent(om as unknown as Record<string, unknown>),
        impactLabel: 'Save',
        impactValue: formatKwh(om.energy?.impactKwhDay ?? om.energy?.dailyKwh),
      }
    );
  }
  if (id === 'O19' && om) {
    return pack(
      [
        field('Health', formatPercent(om.current?.equipmentHealthPct)),
        field('At risk', formatDash(om.current?.assetsAtRisk)),
        field('Risk', formatDash(om.current?.maintenanceRisk)),
      ],
      {
        status: om.status,
        telemetryLabel: provenanceFromAgent(om as unknown as Record<string, unknown>),
        impactLabel: 'Loss',
        impactValue: formatKw(om.energy?.impactKw),
      }
    );
  }
  if (id === 'O20' && om) {
    return pack(
      [
        field('Health', formatPercent(om.current?.controlHealthPct)),
        field('Overrides', formatDash(om.current?.overrides)),
        field('Drift', formatDash(om.current?.driftCount)),
      ],
      {
        status: om.status,
        telemetryLabel: provenanceFromAgent(om as unknown as Record<string, unknown>),
      }
    );
  }

  return pack([]);
}
