export type PlantTone = 'good' | 'stale' | 'bad' | 'missing' | 'unmapped';

export type PlantPoint = {
  value?: unknown;
  unit?: string | null;
  quality?: string | null;
  display?: unknown;
};

export type PlantEquipment = {
  equipment_id: string;
  tone?: PlantTone;
  points: Record<string, PlantPoint>;
};

export type DashboardAlert = {
  severity: string;
  point_id?: string | null;
  equipment_id?: string | null;
  message: string;
  age_seconds?: number | null;
};

export type DashboardOpportunity = {
  id: string;
  title?: string;
  href?: string | null;
  guide_page?: number;
  section?: string;
  guide_savings_potential?: string | null;
  energy_impact_class?: string;
  applicability?: string;
  practice?: string | null;
  telemetry?: string;
  kind?: string;
  control?: string;
  missing_features?: string[];
};

export type DashboardChapter = {
  id: string;
  title: string;
  section: string;
  href: string;
  counts: { live: number; simulated: number; awaiting: number };
  opportunities: DashboardOpportunity[];
};

export type DashboardHome = {
  plantMode?: string;
  bms?: { status?: string; last_error?: string; lastError?: string; protocol?: string };
  telemetry?: { status?: string; source?: string; quality?: string; ageSeconds?: number | null };
  building?: { id?: string; name?: string; location?: string };
  kpis?: {
    coolingTons?: number | null;
    comfortPct?: number | null;
    verifiedKw?: number | null;
    alertCount?: number;
  };
  layers?: Record<string, PlantEquipment[]>;
  alerts?: DashboardAlert[];
  chapters?: DashboardChapter[];
  energy?: { unit?: string; points?: { t?: string; v?: number; point_id?: string }[] };
  guide?: { document?: string; note?: string };
  controlLabel?: string;
  provenance?: string;
  hasCoPoints?: boolean;
};

export const LAYER_GROUPS: { key: string; title: string }[] = [
  { key: 'chillers', title: 'Chillers' },
  { key: 'ahus', title: 'AHUs' },
  { key: 'pumps', title: 'Pumps' },
  { key: 'vfds', title: 'VFDs' },
  { key: 'condenser_water', title: 'Condenser water' },
  { key: 'hot_water', title: 'Hot water' },
  { key: 'zones', title: 'Zones' },
  { key: 'vavs', title: 'VAVs' },
];

export const HUB_RAIL: Record<string, string> = {
  scheduling: 'var(--cat-scheduling)',
  'plant-control': 'var(--cat-plant)',
  ventilation: 'var(--cat-ventilation)',
  'variable-speed': 'var(--cat-variablespeed)',
  operations: 'var(--cat-om)',
};

export function mappingHref(equipmentId?: string | null, point?: string | null) {
  const q = new URLSearchParams();
  q.set('tab', 'mapping');
  if (equipmentId) q.set('equipment', equipmentId);
  if (point) q.set('point', point);
  return `/platform/bms?${q.toString()}`;
}
