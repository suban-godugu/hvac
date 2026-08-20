import { apiJson } from '@/lib/api/client';
import type { OmDashboardData, OmOpportunity } from '@/lib/hvac/omTypes';

const BASE = '/hvac/operations-maintenance';

/** Equipment maintenance is official O19. O18 is training & awareness. */
export async function fetchO19Opportunity(): Promise<OmOpportunity> {
  return apiJson(`${BASE}/O19`);
}

export async function fetchOmDashboardTyped(): Promise<OmDashboardData> {
  return apiJson(`${BASE}/dashboard`);
}

export async function postO19MaintenanceAction(details: Record<string, unknown>): Promise<unknown> {
  return apiJson(`${BASE}/O19/maintenance-action`, {
    method: 'POST',
    body: JSON.stringify({ details }),
  });
}
