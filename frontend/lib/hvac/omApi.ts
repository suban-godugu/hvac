import type { OmDashboardData, OmOpportunity } from './omTypes';
import { ApiError, apiJson } from '../api/client';

async function getOrStatus<T>(path: string, signal?: AbortSignal): Promise<{ data: T | null; error: 'OK' | 'API ERROR' | 'NO DATA' }> {
  try {
    const data = (await apiJson(path, { signal })) as T;
    return { data, error: 'OK' };
  } catch (e) {
    if (signal?.aborted) return { data: null, error: 'API ERROR' };
    if (e instanceof ApiError && e.status >= 400 && e.status < 500) return { data: null, error: 'NO DATA' };
    return { data: null, error: 'API ERROR' };
  }
}

export async function fetchOmDashboard(signal?: AbortSignal) {
  return getOrStatus<OmDashboardData>('/hvac/operations-maintenance/dashboard', signal);
}

export async function fetchOmOpportunity(id: string, signal?: AbortSignal) {
  return getOrStatus<OmOpportunity>(`/hvac/operations-maintenance/${id.toUpperCase()}`, signal);
}

export async function postOmAction(id: string, action: string, body?: Record<string, unknown>): Promise<unknown> {
  const oid = id.toUpperCase();
  return apiJson(`/hvac/operations-maintenance/${oid}/${action}`, {
    method: 'POST',
    body: JSON.stringify(body || {}),
  });
}
