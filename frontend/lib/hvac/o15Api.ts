import { apiJson } from '@/lib/api/client';
import type { O15Dashboard, O15HistoryResponse } from '@/lib/hvac/o15Types';
import type { O15Command, O15EquipmentRow, O15Safety } from '@/lib/hvac/o15Types';

const BASE = '/agents/variable-speed/o15';

export async function fetchO15Dashboard(): Promise<O15Dashboard> {
  return apiJson(`${BASE}/dashboard`);
}

export async function fetchO15State(): Promise<O15Dashboard> {
  return apiJson(`${BASE}/state`);
}

export async function fetchO15Telemetry(): Promise<Record<string, unknown>> {
  return apiJson(`${BASE}/telemetry`);
}

export async function fetchO15Condensers(): Promise<{ condensers: O15EquipmentRow[] }> {
  return apiJson(`${BASE}/condensers`);
}

export async function fetchO15Fans(): Promise<{ fans: O15EquipmentRow[] }> {
  return apiJson(`${BASE}/fans`);
}

export async function fetchO15Recommendation(): Promise<O15Dashboard> {
  return apiJson(`${BASE}/recommendation`);
}

export async function fetchO15Safety(): Promise<O15Safety> {
  return apiJson(`${BASE}/safety`);
}

export async function fetchO15History(hours: number): Promise<O15HistoryResponse> {
  return apiJson(`${BASE}/history?hours=${hours}`);
}

export async function fetchO15Commands(): Promise<{ commands: O15Command[] }> {
  return apiJson(`${BASE}/commands`);
}

export async function fetchO15Config(): Promise<Record<string, unknown>> {
  return apiJson(`${BASE}/config`);
}

export async function postO15Optimize(): Promise<O15Dashboard> {
  return apiJson(`${BASE}/optimize`, { method: 'POST', body: JSON.stringify({}) });
}

export async function postO15Apply(commandId: string, confirm: boolean): Promise<O15Command> {
  return apiJson(`${BASE}/commands/${commandId}/apply`, {
    method: 'POST',
    body: JSON.stringify({ confirm }),
  });
}

export async function postO15Verify(commandId: string): Promise<{ ok?: boolean; command?: O15Command }> {
  return apiJson(`${BASE}/commands/${commandId}/verify`, { method: 'POST', body: '{}' });
}

export async function postO15Rollback(commandId: string): Promise<{ ok?: boolean; command?: O15Command }> {
  return apiJson(`${BASE}/commands/${commandId}/rollback`, { method: 'POST', body: '{}' });
}

export async function postO15SafeMode(reason?: string): Promise<{ safeMode?: boolean }> {
  return apiJson(`${BASE}/safe-mode`, { method: 'POST', body: JSON.stringify({ reason }) });
}

export function o15HistoryCsvUrl(hours: number) {
  return `${BASE}/history?hours=${hours}&format=csv`;
}
