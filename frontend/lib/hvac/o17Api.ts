import { apiJson } from '@/lib/api/client';
import type { OmDashboardData, OmOpportunity } from '@/lib/hvac/omTypes';

const BASE = '/hvac/operations-maintenance';

export async function fetchO17Opportunity(): Promise<OmOpportunity> {
  return apiJson(`${BASE}/O17`);
}

export async function fetchOmDashboardTyped(): Promise<OmDashboardData> {
  return apiJson(`${BASE}/dashboard`);
}

export async function postO17PlanningAction(body?: Record<string, unknown>): Promise<unknown> {
  return apiJson(`${BASE}/O17/dispatch`, {
    method: 'POST',
    body: JSON.stringify(body || {}),
  });
}

export async function fetchPlatformBuildingName(): Promise<string | null> {
  const body = (await apiJson('/platform/status')) as { building?: { name?: string | null } };
  const name = body.building?.name;
  if (!name || name === 'undefined' || name === 'null') return null;
  return name;
}
