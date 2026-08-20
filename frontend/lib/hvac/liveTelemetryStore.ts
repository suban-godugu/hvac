'use client';

import { create } from 'zustand';
import type { TelemetryEvent, TelemetryFrame, WsConnectionState } from '@/lib/hvac/telemetrySocket';

export type TelStatus = 'LIVE' | 'STALE' | 'NO DATA' | 'BAD' | 'SIMULATED';

function telLabel(raw?: string | null): TelStatus {
  const s = String(raw || '').toUpperCase().replace(/_/g, ' ');
  if (s === 'LIVE') return 'LIVE';
  if (s === 'STALE') return 'STALE';
  if (s === 'BAD') return 'BAD';
  if (s === 'SIMULATED') return 'SIMULATED';
  return 'NO DATA';
}

function bmsLabel(raw?: string | null): 'CONNECTED' | 'DISCONNECTED' | 'OFFLINE' {
  const s = String(raw || '').toUpperCase();
  if (s === 'CONNECTED') return 'CONNECTED';
  if (s === 'OFFLINE') return 'OFFLINE';
  return 'DISCONNECTED';
}

export function displayValue(v: unknown): string {
  if (v === null || v === undefined || v === '') return '—';
  return String(v);
}

type LiveState = {
  bmsStatus: 'CONNECTED' | 'DISCONNECTED' | 'OFFLINE';
  telemetryStatus: TelStatus;
  telemetryAgeSeconds: number | null;
  telemetryQuality: string | null;
  telemetrySource: string | null;
  safeMode: boolean;
  controlEnabled: boolean;
  lastUpdate: number | null;
  connectionState: WsConnectionState;
  events: TelemetryEvent[];
  protocol: string | null;
  lastError: string | null;
  applyFrame: (frame: TelemetryFrame, connectionState: WsConnectionState) => void;
  getPoint: (equipmentId: string, point: string) => TelemetryEvent | null;
};

export const useLiveTelemetry = create<LiveState>((set, get) => ({
  bmsStatus: 'DISCONNECTED',
  telemetryStatus: 'NO DATA',
  telemetryAgeSeconds: null,
  telemetryQuality: null,
  telemetrySource: null,
  safeMode: false,
  controlEnabled: false,
  lastUpdate: null,
  connectionState: 'idle',
  events: [],
  protocol: null,
  lastError: null,
  applyFrame: (frame, connectionState) => {
    const bms = frame.bms || {};
    const tel = frame.telemetry || {};
    set({
      connectionState,
      bmsStatus: bmsLabel(bms.status),
      telemetryStatus: telLabel(tel.status),
      telemetryAgeSeconds: typeof tel.ageSeconds === 'number' ? tel.ageSeconds : null,
      telemetryQuality: tel.quality ? String(tel.quality) : null,
      telemetrySource: tel.source ? String(tel.source) : null,
      safeMode: Boolean(frame.safeMode),
      controlEnabled: false,
      lastUpdate: Date.now(),
      events: Array.isArray(frame.events) ? frame.events : [],
      protocol: bms.protocol ? String(bms.protocol) : null,
      lastError: (bms.lastError || bms.last_error || null) as string | null,
    });
  },
  getPoint: (equipmentId, point) => {
    const eq = equipmentId.toUpperCase();
    const pt = point.toLowerCase();
    return (
      get().events.find((e) => {
        const eid = String(e.equipment_id || '').toUpperCase();
        const name = String(e.point || e.point_id || '').toLowerCase();
        return eid === eq && (name === pt || name.endsWith(`.${pt}`) || name.includes(pt));
      }) || null
    );
  },
}));
