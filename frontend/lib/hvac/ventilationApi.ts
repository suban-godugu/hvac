import type { VentilationDashboardData, VentilationOpportunity } from './ventilationTypes';
import { ApiError, apiJson } from '../api/client';

async function getOrStatus<T>(path: string, signal?: AbortSignal): Promise<{ data: T | null; error: 'OK' | 'API ERROR' | 'NO DATA' }> {
  try {
    const data = (await apiJson(path, { signal })) as T;
    return { data, error: 'OK' };
  } catch (e) {
    if (signal?.aborted) return { data: null, error: 'API ERROR' };
    if (e instanceof ApiError && e.status >= 400 && e.status < 500) return { data: null, error: 'NO DATA' };
  }
  return { data: null, error: 'API ERROR' };
}

export async function fetchVentilationDashboard(
  signal?: AbortSignal
): Promise<{
  data: VentilationDashboardData | null;
  error: 'OK' | 'API ERROR' | 'NO DATA';
}> {
  return getOrStatus<VentilationDashboardData>('/hvac/ventilation/opportunities', signal);
}

export async function fetchVentilationOpportunity(
  id: string,
  signal?: AbortSignal
): Promise<{ data: VentilationOpportunity | null; error: 'OK' | 'API ERROR' | 'NO DATA' }> {
  return getOrStatus<VentilationOpportunity>(`/hvac/ventilation/${id.toUpperCase()}`, signal);
}

export async function postVentilationAction(
  id: string,
  action: 'dispatch' | 'rollback' | 'verify',
  body?: Record<string, unknown>
): Promise<unknown> {
  const oid = id.toUpperCase();
  return apiJson(`/hvac/ventilation/${oid}/${action}`, {
    method: 'POST',
    body: JSON.stringify(body || {}),
  });
}
