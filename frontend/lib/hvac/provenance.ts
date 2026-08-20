export type ProvenanceLabel = 'LIVE' | 'SIMULATED' | 'STALE' | 'NO DATA' | 'BMS OFFLINE';

export type MlProvenanceLabel = 'TRAINING DATA' | 'MODEL PREDICTION' | 'MODEL NOT AVAILABLE' | 'MODEL NOT TRAINABLE' | 'NO DATA';

const LIVE_SOURCES = new Set(['LIVE_BMS', 'BMS', 'LIVE']);
const SIM_SOURCES = new Set(['SIMULATION', 'SIMULATOR', 'DEMO', 'TEST', 'TEST TELEMETRY']);
const TRAINING_SOURCES = new Set(['TRAINING_DATASET', 'TRAINING DATA', 'KAGGLE', 'ML_MODEL']);

function upper(v: unknown): string {
  return String(v || '').trim().toUpperCase();
}

/** LIVE only when production BMS is connected, source is LIVE_BMS, quality is GOOD, and telemetry is fresh. */
export function provenanceLabel(input: {
  bmsConnected?: boolean | null;
  source?: string | null;
  quality?: string | null;
  classified?: string | null;
  telemetryAgeSeconds?: number | null;
  staleSeconds?: number;
}): ProvenanceLabel {
  const connected = Boolean(input.bmsConnected);
  const src = upper(input.source);
  const quality = upper(input.quality);
  const age = input.telemetryAgeSeconds;
  const staleLimit = input.staleSeconds ?? 90;

  const classified = upper(input.classified);
  if (TRAINING_SOURCES.has(src) || src.includes('TRAINING') || src === 'ML_MODEL') return 'SIMULATED';
  if (SIM_SOURCES.has(src) || src.includes('SIMUL') || src.startsWith('DEMO') || classified === 'SIMULATED') return 'SIMULATED';
  if (!connected || classified === 'BMS_OFFLINE') return 'BMS OFFLINE';
  if (quality === 'STALE' || classified === 'STALE' || (age != null && age > staleLimit)) return 'STALE';
  if (quality === 'MISSING' || quality === 'BAD' || quality === '' || classified === 'MISSING' || classified === 'BAD') return 'NO DATA';
  if (connected && LIVE_SOURCES.has(src) && quality === 'GOOD') return 'LIVE';
  return 'NO DATA';
}

/** Map typical O1–O9 / plant-control agent payloads onto provenanceLabel. */
export function provenanceFromAgent(state: Record<string, unknown> | null | undefined): ProvenanceLabel {
  if (!state) return 'NO DATA';
  const header = (state.header as Record<string, unknown> | undefined) || {};
  const bms = String(state.bms_connection || state.bms_status || state.bms || header.bms || '').toUpperCase();
  const connected =
    state.bmsConnected === true ||
    state.bms_connected === true ||
    bms === 'CONNECTED' ||
    bms === 'ONLINE';
  const tel = (state.telemetry as Record<string, unknown> | undefined) || {};
  const classifiedTel = (state.classified_telemetry as Record<string, unknown> | undefined) || {};
  return provenanceLabel({
    bmsConnected: connected,
    source: (state.source || state.telemetry_source || classifiedTel.source || tel.source) as string | null,
    quality: (state.telemetry_quality || state.quality || classifiedTel.quality || tel.quality) as string | null,
    classified: (state.classified || classifiedTel.status || tel.classified) as string | null,
    telemetryAgeSeconds:
      (state.telemetry_age_seconds as number | undefined) ??
      (classifiedTel.age_seconds as number | undefined) ??
      (tel.ageSeconds as number | undefined) ??
      (tel.age_seconds as number | undefined) ??
      null,
  });
}

export function mlProvenanceFromPayload(state: Record<string, unknown> | null | undefined): MlProvenanceLabel {
  if (!state) return 'NO DATA';
  const ml = (state.ml as Record<string, unknown> | undefined) || {};
  const raw = upper(ml.provenance || state.ml_provenance || ml.status);
  if (raw.includes('TRAINABLE') && raw.includes('NOT')) return 'MODEL NOT TRAINABLE';
  if (raw.includes('NOT AVAILABLE') || raw === 'MODEL_NOT_AVAILABLE' || raw === 'NO_ML_MODEL') return 'MODEL NOT AVAILABLE';
  if (raw.includes('MODEL PREDICTION') || (upper(ml.source as string) === 'ML_MODEL' && Boolean(ml.prediction))) return 'MODEL PREDICTION';
  if (raw.includes('TRAINING')) return 'TRAINING DATA';
  if (ml.prediction) return 'MODEL PREDICTION';
  if (ml.status) return 'MODEL NOT AVAILABLE';
  return 'NO DATA';
}
