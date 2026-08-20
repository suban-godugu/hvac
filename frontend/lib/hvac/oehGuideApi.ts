import { apiJson } from '@/lib/api/client';

export interface OehSlider {
  key: string;
  label: string;
  min: number;
  max: number;
  step: number;
  default: number;
  unit: string;
}

export interface OehCatalogItem {
  opportunity_id: string;
  id: number;
  title: string;
  cat: string;
  route: string;
  scope: string;
  pct: number;
  x_type: 'hour' | 'month';
  sim_label: string;
  summary: string;
  principle: string;
  practice: string;
  recommendation: string;
  equipment: string;
  scenario?: string;
  sliders: OehSlider[];
  prev_id: string | null;
  next_id: string | null;
  prev_route: string | null;
  next_route: string | null;
}

export interface OehEvaluate {
  opportunity_id: string;
  live: boolean;
  provenance: string;
  dispatch_allowed: boolean;
  dispatch_blocked_reason?: string;
  series: { x: number; baseline: number; optimized: number }[];
  metrics: { label: string; value: string }[];
  sliders: Record<string, number>;
  x_type: 'hour' | 'month';
  sim_label: string;
  pct: number;
  scope: string;
  title: string;
  route: string;
  agent: {
    opportunity_id: string;
    live: boolean;
    recommendation?: string | null;
    reason?: string | null;
  };
}

export function officialGuideId(opportunityId: string, resetMode?: string): string | null {
  const raw = (opportunityId || '').trim().toUpperCase().replace(/\s+/g, '');
  if (raw === 'O6-O8' || raw === 'O6_8' || raw === 'O6/O8') {
    const mode = (resetMode || '').toUpperCase();
    if (mode === 'HHW') return 'O6';
    if (mode === 'CW') return 'O8';
    return 'O7';
  }
  const m = /^O(\d+)$/.exec(raw);
  if (!m) return null;
  const n = Number(m[1]);
  if (n < 1 || n > 20) return null;
  return `O${n}`;
}

export async function fetchOehCatalog(oid: string): Promise<OehCatalogItem> {
  return apiJson(`/v1/oeh-guide/${oid}`) as Promise<OehCatalogItem>;
}

export async function evaluateOehGuide(oid: string, sliders: Record<string, number>): Promise<OehEvaluate> {
  return apiJson(`/v1/oeh-guide/${oid}/evaluate`, {
    method: 'POST',
    body: JSON.stringify({ sliders: sliders || {} }),
  }) as Promise<OehEvaluate>;
}
