import { apiJson } from '@/lib/api/client';
import type { OmDashboardData, OmOpportunity } from '@/lib/hvac/omTypes';

const BASE = '/hvac/operations-maintenance';

/** Training & awareness is official O18. OM API does not expose O16 (water-cooled HP). */
export async function fetchO18Opportunity(): Promise<OmOpportunity> {
  return apiJson(`${BASE}/O18`);
}

export async function fetchOmDashboardTyped(): Promise<OmDashboardData> {
  return apiJson(`${BASE}/dashboard`);
}
