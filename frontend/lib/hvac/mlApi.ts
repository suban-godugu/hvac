import { apiJson } from '@/lib/api/client';

export interface MlModelRow {
  opportunity_id: string;
  agent_id?: string | null;
  status: string;
  model_id?: string | null;
  model_version?: string | null;
  training_dataset_id?: string | null;
}

export interface MlPredictResponse {
  status: string;
  opportunity_id: string;
  model_id?: string | null;
  model_version?: string | null;
  prediction?: Record<string, unknown> | null;
  confidence?: number | null;
  provenance?: string | null;
  training_dataset?: string | null;
  engineering_validation?: string | null;
  source?: string | null;
  top_features?: { feature: string; value?: number; importance?: number }[];
  missing_features?: string[];
}

export function fetchMlModels() {
  return apiJson('/ml/models') as Promise<{ models: MlModelRow[] }>;
}

export function fetchMlModel(oid: string) {
  return apiJson(`/ml/models/${oid}`) as Promise<{ opportunity_id: string; status: string; model?: Record<string, unknown> | null }>;
}

export function postMlPredict(body: { opportunity_id: string; agent_id?: string; features?: Record<string, unknown> }) {
  return apiJson('/ml/predict', { method: 'POST', body: JSON.stringify(body) }) as Promise<MlPredictResponse>;
}
