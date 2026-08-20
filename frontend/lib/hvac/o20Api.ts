import { apiJson } from '@/lib/api/client';
import type { OmDashboardData, OmOpportunity } from '@/lib/hvac/omTypes';

const BASE = '/hvac/operations-maintenance';

export interface PlatformGate {
  buildingName: string | null;
  safeMode: boolean;
  safety: string | null;
  bms: string | null;
  telemetry: string | null;
  mode: string | null;
}

/** Control software is official O20. O19 is equipment maintenance. */
export async function fetchO20Opportunity(): Promise<OmOpportunity> {
  return apiJson(`${BASE}/O20`);
}

export async function fetchOmDashboardTyped(): Promise<OmDashboardData> {
  return apiJson(`${BASE}/dashboard`);
}

export async function fetchPlatformGate(): Promise<PlatformGate> {
  const body = (await apiJson('/platform/status')) as {
    building?: { name?: string | null };
    safeMode?: boolean;
    safety?: string | null;
    bms?: string | null;
    telemetry?: string | null;
    mode?: string | null;
  };
  const name = body.building?.name;
  return {
    buildingName: !name || name === 'undefined' || name === 'null' ? null : name,
    safeMode: Boolean(body.safeMode),
    safety: body.safety ? String(body.safety) : null,
    bms: body.bms ? String(body.bms) : null,
    telemetry: body.telemetry ? String(body.telemetry) : null,
    mode: body.mode ? String(body.mode) : null,
  };
}

export async function postO20ChangeRequest(details: Record<string, unknown>): Promise<unknown> {
  return apiJson(`${BASE}/O20/change-request`, {
    method: 'POST',
    body: JSON.stringify({ details: { status: 'REVIEW_REQUIRED', ...details } }),
  });
}
