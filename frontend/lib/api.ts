import {
  SupervisoryCycleResponse,
  ActionRecord,
  EngineeringLimits
} from "./types";
import { API_BASE, apiJson } from "./api/client";

export async function fetchSchedulingDashboard(): Promise<any> {
  const res = await fetch(`${API_BASE}/scheduling/dashboard`, { cache: "no-store" });
  if (!res.ok) {
    const fallback = await fetch(`${API_BASE}/agents/scheduling/dashboard`, { cache: "no-store" });
    if (!fallback.ok) throw new Error("Failed to fetch scheduling dashboard");
    return fallback.json();
  }
  return res.json();
}

export async function fetchStatus(): Promise<SupervisoryCycleResponse> {
  const res = await fetch(`${API_BASE}/agents/scheduling/status`, { cache: "no-store" });
  if (!res.ok) {
    // Fallback to /status if needed
    const fallbackRes = await fetch(`${API_BASE}/status`, { cache: "no-store" });
    if (!fallbackRes.ok) throw new Error("Failed to fetch status");
    return fallbackRes.json();
  }
  return res.json();
}

export async function stepSimulation(minutes: number = 5): Promise<SupervisoryCycleResponse> {
  return apiJson(`/agents/scheduling/run?minutes=${minutes}`, { method: "POST" });
}

export async function fetchHistory(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/agents/scheduling/telemetry`, { cache: "no-store" });
  if (!res.ok) {
    const fallback = await fetch(`${API_BASE}/history`, { cache: "no-store" });
    if (!fallback.ok) return [];
    return fallback.json();
  }
  return res.json();
}

export async function setAgentMode(mode: string): Promise<any> {
  return apiJson("/agents/scheduling/mode", { method: "POST", body: JSON.stringify({ mode }) });
}

export async function fetchO1(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o1/state`, { cache: "no-store" });
  if (!res.ok) {
    const fallback = await fetch(`${API_BASE}/agents/scheduling/o1`, { cache: "no-store" });
    if (!fallback.ok) return null;
    return fallback.json();
  }
  return res.json();
}

export async function fetchO1ThermalModel(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o1/thermal-model`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchO1StartCandidates(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o1/start-candidates`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchO1CoastCandidates(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o1/coast-candidates`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchO1Decision(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o1/decision`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchO1Timeline(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o1/timeline`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchO1Safety(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o1/safety`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchO1Trajectory(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o1/trajectory`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchO1Energy(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o1/energy`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchO1BmsAction(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o1/bms-action`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchO1History(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o1/history`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchO1Activities(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o1/activity`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchO1Studio(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o1/studio`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function triggerO1Optimize(): Promise<any> {
  return apiJson("/agents/scheduling/o1/optimize", { method: "POST" });
}

export async function triggerO1Rollback(): Promise<any> {
  return apiJson("/agents/scheduling/o1/rollback", { method: "POST" });
}

export async function fetchO2(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o2/state`, { cache: "no-store" });
  if (!res.ok) {
    const fallback = await fetch(`${API_BASE}/agents/scheduling/o2`, { cache: "no-store" });
    if (!fallback.ok) return null;
    return fallback.json();
  }
  return res.json();
}

export async function fetchO2Zones(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o2/zones`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchO2ZoneDetail(zoneId: string = "VAV-101"): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o2/detail?zone_id=${zoneId}`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchO2Telemetry(zoneId: string = "VAV-101", hours: number = 1): Promise<any[]> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o2/telemetry?zone_id=${zoneId}&hours=${hours}`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchO2Decision(zoneId: string = "VAV-101"): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o2/decision?zone_id=${zoneId}`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchO2Safety(zoneId: string = "VAV-101"): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o2/safety?zone_id=${zoneId}`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchO2Energy(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o2/energy`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchO2BmsAction(zoneId: string = "VAV-101"): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o2/bms-action?zone_id=${zoneId}`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchO2History(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o2/history`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchO2Activities(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o2/activity`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchO2Studio(zoneId: string = "VAV-101", hours: number = 1): Promise<any> {
  const res = await fetch(
    `${API_BASE}/agents/scheduling/o2/studio?zone_id=${encodeURIComponent(zoneId)}&hours=${hours}`,
    { cache: "no-store" }
  );
  if (!res.ok) return null;
  return res.json();
}

export async function triggerO2Optimize(zoneId: string, setpoint: number): Promise<any> {
  return apiJson("/agents/scheduling/o2/optimize", { method: "POST", body: JSON.stringify({ zone_id: zoneId, setpoint }) });
}

export async function triggerO2Rollback(zoneId: string): Promise<any> {
  return apiJson("/agents/scheduling/o2/rollback", { method: "POST", body: JSON.stringify({ zone_id: zoneId }) });
}

export async function fetchO3(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o3/state`, { cache: "no-store" });
  if (!res.ok) {
    const fallback = await fetch(`${API_BASE}/agents/scheduling/o3`, { cache: "no-store" });
    if (!fallback.ok) return null;
    return fallback.json();
  }
  return res.json();
}

export async function fetchO3Zones(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o3/zones`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchO3Demand(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o3/demand`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchO3Exclusions(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o3/exclusions`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchO3Candidates(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o3/candidates`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchO3Decision(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o3/decision`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchO3Power(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o3/power`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchO3Safety(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o3/safety`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchO3BmsAction(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o3/bms-action`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchO3Telemetry(hours: number = 1): Promise<any[]> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o3/telemetry?hours=${hours}`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchO3ZoneResponse(hours: number = 1): Promise<any[]> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o3/zone-response?hours=${hours}`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchO3History(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o3/history`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchO3Activities(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o3/activity`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchO3Studio(hours: number = 1): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o3/studio?hours=${hours}`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function setO3Method(method: string): Promise<any> {
  return apiJson("/agents/scheduling/o3/method", { method: "POST", body: JSON.stringify({ method }) });
}

export async function triggerO3Optimize(sat: number): Promise<any> {
  return apiJson("/agents/scheduling/o3/optimize", { method: "POST", body: JSON.stringify({ sat }) });
}

export async function triggerO3Rollback(): Promise<any> {
  return apiJson("/agents/scheduling/o3/rollback", { method: "POST" });
}

export async function fetchO4(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o4/state`, { cache: "no-store" });
  if (!res.ok) {
    const fallback = await fetch(`${API_BASE}/agents/scheduling/o4`, { cache: "no-store" });
    if (!fallback.ok) return null;
    return fallback.json();
  }
  return res.json();
}

export async function fetchO4Load(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o4/load`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchO4Chillers(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o4/chillers`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchO4Compressors(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o4/compressors`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchO4StageCandidates(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o4/candidates`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchO4ChwsCandidates(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o4/chws`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchO4Decision(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o4/decision`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchO4Power(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o4/power`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchO4Safety(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o4/safety`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchO4BmsAction(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o4/bms-action`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchO4Telemetry(hours: number = 1): Promise<any[]> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o4/telemetry?hours=${hours}`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchO4PlantTrend(hours: number = 1): Promise<any[]> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o4/plant-trend?hours=${hours}`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchO4History(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o4/history`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchO4Activities(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o4/activity`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchO4Studio(hours: number = 1): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/o4/studio?hours=${hours}`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function triggerO4Optimize(chws: number, stages: number = 1): Promise<any> {
  return apiJson("/agents/scheduling/o4/optimize", { method: "POST", body: JSON.stringify({ chws, stages }) });
}

export async function triggerO4Rollback(): Promise<any> {
  return apiJson("/agents/scheduling/o4/rollback", { method: "POST" });
}

export async function fetchKpis(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/kpis`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchDecisions(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/scheduling/decisions`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchPendingApprovals(): Promise<ActionRecord[]> {
  const res = await fetch(`${API_BASE}/actions/pending`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function approveAction(actionId: string): Promise<any> {
  return apiJson("/actions/approve", { method: "POST", body: JSON.stringify({ action_id: actionId }) });
}

export async function rejectAction(actionId: string, reason: string = "Operator rejected"): Promise<any> {
  return apiJson("/actions/reject", { method: "POST", body: JSON.stringify({ action_id: actionId, reason }) });
}

export async function fetchAuditLogs(limit: number = 50): Promise<ActionRecord[]> {
  const res = await fetch(`${API_BASE}/actions/audit?limit=${limit}`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchLimits(): Promise<EngineeringLimits> {
  const res = await fetch(`${API_BASE}/limits`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch limits");
  return res.json();
}

export async function updateLimits(limits: EngineeringLimits): Promise<any> {
  return apiJson("/limits", { method: "POST", body: JSON.stringify({ limits }) });
}

export async function selectScenario(scenarioId: string): Promise<any> {
  return apiJson("/scenarios/select", { method: "POST", body: JSON.stringify({ scenario_id: scenarioId }) });
}

export async function applyRollback(actionId?: string, reason?: string): Promise<any> {
  return apiJson("/agents/scheduling/rollback", { method: "POST", body: JSON.stringify({ action_id: actionId, reason }) });
}
