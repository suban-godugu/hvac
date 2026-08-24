'use client';

import React, { useState, useEffect } from 'react';
import { useSupervisoryStore } from '@/lib/store';
import { AgentMode } from '@/lib/types';
import { DEFAULT_FACILITY_CONFIG } from '@/lib/facilityConfig';
import { hvacFetch } from '@/lib/api/client';
import { StatusBadge, toneForStatus } from '@/components/hvac/StatusBadge';
import { useLiveTelemetry } from '@/lib/hvac/liveTelemetryStore';
import type { TelemetryFrame } from '@/lib/hvac/telemetrySocket';
import { Cpu, Sun, Sunrise, Sunset, Moon, Clock, MapPin } from 'lucide-react';

function num(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string' && value.trim() !== '') {
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

function formatFacilityClock(timeZone: string, now: Date) {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone,
    weekday: 'short',
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(now);
  const pick = (type: string) => parts.find((p) => p.type === type)?.value || '';
  const hour = parseInt(pick('hour') || '0', 10);
  let dayState = 'DAY';
  if (hour >= 5 && hour < 12) dayState = 'MORNING';
  else if (hour >= 12 && hour < 17) dayState = 'DAY';
  else if (hour >= 17 && hour < 21) dayState = 'EVENING';
  else dayState = 'NIGHT';
  return {
    weekday: pick('weekday').toUpperCase(),
    dateStr: `${pick('day')} ${pick('month').toUpperCase()}`,
    timeStr: `${pick('hour')}:${pick('minute')}`,
    dayState,
  };
}

export const Header: React.FC = () => {
  const { agentMode, setAgentMode } = useSupervisoryStore();
  const live = useLiveTelemetry();
  const [safetyStatus, setSafetyStatus] = useState<'PASS' | 'SAFE_HOLD'>('SAFE_HOLD');
  const [buildingName, setBuildingName] = useState<string>(DEFAULT_FACILITY_CONFIG.name);
  const [buildingLocation, setBuildingLocation] = useState<string>(DEFAULT_FACILITY_CONFIG.location);
  const [timezone, setTimezone] = useState<string>(DEFAULT_FACILITY_CONFIG.timezone);
  const [modeLabel, setModeLabel] = useState('ADVISORY');
  const [oat, setOat] = useState<number | null>(null);
  const [humidity, setHumidity] = useState<number | null>(null);
  const bmsStatus = live.bmsStatus;
  const telemetryLabel = live.telemetryStatus;
  const telemetryAge = live.telemetryAgeSeconds;
  const safeMode = live.safeMode;
  const plantMode = live.plantMode || 'DATASET';
  const applyFrame = useLiveTelemetry((s) => s.applyFrame);

  const setPlant = async (mode: 'DATASET' | 'LIVE_BMS') => {
    const res = await hvacFetch('/api/platform/plant-mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode, reason: 'header-toggle' }),
    });
    if (!res.ok) return;
    const status = await res.json();
    applyFrame(
      {
        bms: status.bms,
        telemetry: status.telemetry,
        safeMode: Boolean(status.safeMode),
        plantMode: status.plantMode,
        controlEnabled: Boolean(status.controlEnabled),
        controlLabel: String(status.controlLabel || (status.controlEnabled ? 'WRITE ENABLED' : 'WRITE DISABLED')),
        events: useLiveTelemetry.getState().events,
      },
      useLiveTelemetry.getState().connectionState
    );
  };

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const res = await fetch('/api/platform/status', { cache: 'no-store' });
        if (!res.ok || cancelled) return;
        const body = (await res.json()) as Record<string, unknown>;
        setSafetyStatus(body.safety === 'PASS' && !body.safeMode ? 'PASS' : 'SAFE_HOLD');
        setModeLabel(String(body.mode || 'ADVISORY'));
        const facility = (body.facility || body.building) as
          | { name?: string; location?: string; timezone?: string }
          | undefined;
        const weather = body.weather as { oat?: unknown; humidity?: unknown; oah?: unknown } | undefined;
        if (facility?.name) setBuildingName(facility.name);
        if (facility?.location) setBuildingLocation(facility.location);
        if (facility?.timezone) setTimezone(facility.timezone);
        const nextOat = num(weather?.oat);
        const nextRh = num(weather?.humidity ?? weather?.oah);
        if (nextOat != null) setOat(nextOat);
        if (nextRh != null) setHumidity(nextRh);
        if (body.plantMode === 'DATASET' || body.plantMode === 'LIVE_BMS') {
          applyFrame(
            {
              bms: (body.bms as TelemetryFrame['bms']) || { status: String(body.bmsStatus || '') },
              telemetry: (body.telemetry as TelemetryFrame['telemetry']) || { status: undefined },
              safeMode: Boolean(body.safeMode),
              plantMode: String(body.plantMode),
              controlEnabled: Boolean(body.controlEnabled),
              controlLabel: String(body.controlLabel || (body.controlEnabled ? 'WRITE ENABLED' : 'WRITE DISABLED')),
              events: useLiveTelemetry.getState().events,
            },
            useLiveTelemetry.getState().connectionState
          );
        }
      } catch {
        /* keep last known */
      }
    };
    load();
    const id = window.setInterval(load, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [applyFrame]);

  const [facilityTime, setFacilityTime] = useState({
    weekday: '',
    dateStr: '',
    timeStr: '',
    dayState: 'DAY',
  });

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      try {
        setFacilityTime(formatFacilityClock(timezone, now));
      } catch {
        setFacilityTime(formatFacilityClock('Asia/Kolkata', now));
      }
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, [timezone]);

  const dayIcon =
    facilityTime.dayState === 'MORNING' ? (
      <Sunrise className="w-3.5 h-3.5 text-amber-400 shrink-0" />
    ) : facilityTime.dayState === 'EVENING' ? (
      <Sunset className="w-3.5 h-3.5 text-orange-400 shrink-0" />
    ) : facilityTime.dayState === 'NIGHT' ? (
      <Moon className="w-3.5 h-3.5 text-slate-400 shrink-0" />
    ) : (
      <Sun className="w-3.5 h-3.5 text-amber-400 shrink-0" />
    );

  const toggleSafe = async () => {
    await hvacFetch('/api/platform/safe-mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: !safeMode, reason: 'header-toggle' }),
    });
  };

  const ageText =
    telemetryAge != null ? (telemetryAge < 1 ? '<1s' : `${Math.round(telemetryAge)}s`) : '—';

  return (
    <header className="sticky top-0 z-40 h-16 bg-[color:var(--bg-header)] backdrop-blur-xl border-b border-white/[0.07] px-5 lg:px-7 flex items-center select-none shadow-[0_1px_0_rgba(34,211,238,0.06)]">
      <div className="flex items-center justify-between w-full gap-4">
        <div className="flex items-center gap-3 shrink-0 min-w-0">
          <div className="w-9 h-9 rounded-[10px] border border-cyan-400/30 bg-gradient-to-br from-cyan-400/22 to-cyan-500/5 shadow-[var(--glow-cyan)] flex items-center justify-center text-cyan-300">
            <Cpu className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <div className="text-[13px] font-semibold text-slate-50 tracking-tight leading-none">HVAC AI</div>
            <div className="text-[11px] text-slate-400 truncate flex items-center gap-1 mt-1">
              <span className="text-slate-200 truncate">{buildingName}</span>
              <span className="text-slate-600">·</span>
              <MapPin className="w-3 h-3 shrink-0 text-slate-500" />
              <span className="truncate">{buildingLocation || 'Location unavailable'}</span>
            </div>
          </div>
        </div>

        <div className="hidden lg:flex items-center gap-2">
          <div className="flex items-center gap-2 h-8 px-3 rounded-[10px] border border-white/[0.07] bg-white/[0.035] text-[11px] font-mono text-slate-300">
            {dayIcon}
            <span className="text-slate-200">{facilityTime.dayState}</span>
            <span className="text-slate-600">·</span>
            <span>{oat != null ? `${oat.toFixed(1)}°C` : 'OAT —'}</span>
            <span className="text-slate-600">·</span>
            <span className="text-slate-400">{humidity != null ? `RH ${Math.round(humidity)}%` : 'RH —'}</span>
          </div>
          <div className="flex items-center gap-2 h-8 px-3 rounded-[10px] border border-white/[0.07] bg-white/[0.035] text-[11px] font-mono text-slate-200">
            <Clock className="w-3.5 h-3.5 text-slate-500" />
            <span className="font-semibold tabular-nums tracking-wide">{facilityTime.timeStr || '—'}</span>
            <span className="text-slate-500">
              {facilityTime.weekday} {facilityTime.dateStr}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <div className="hidden md:flex h-8 rounded-[10px] border border-white/[0.08] bg-[color:var(--bg-card)] p-0.5">
            <button
              type="button"
              onClick={() => setPlant('DATASET')}
              className={`px-2.5 text-[10px] font-semibold tracking-wide rounded-md ${
                plantMode === 'DATASET' ? 'bg-amber-400/15 text-amber-200' : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              DATASET
            </button>
            <button
              type="button"
              onClick={() => setPlant('LIVE_BMS')}
              className={`px-2.5 text-[10px] font-semibold tracking-wide rounded-md ${
                plantMode === 'LIVE_BMS' ? 'bg-cyan-400/15 text-cyan-200' : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              LIVE BMS
            </button>
          </div>
          <div className="hidden md:flex items-center gap-1.5" title={`${modeLabel} · ${safetyStatus === 'PASS' ? 'SAFETY PASS' : 'SAFETY HOLD'}`}>
            <StatusBadge tone={bmsStatus === 'CONNECTED' ? 'live' : 'danger'} pulse={bmsStatus === 'CONNECTED'}>
              BMS {bmsStatus}
            </StatusBadge>
            <StatusBadge tone={toneForStatus(telemetryLabel)} pulse={telemetryLabel === 'LIVE'}>
              TEL {telemetryLabel} {ageText}
            </StatusBadge>
            <StatusBadge tone={live.controlEnabled ? 'live' : 'muted'} pulse={false}>
              {live.controlLabel || (live.controlEnabled ? 'WRITE ENABLED' : 'WRITE DISABLED')}
            </StatusBadge>
          </div>
          <select
            value={agentMode}
            onChange={(e) => setAgentMode(e.target.value as AgentMode)}
            className="h-8 rounded-[10px] bg-[color:var(--bg-card)] border border-white/[0.08] px-2 text-[11px] font-semibold text-cyan-300 focus:outline-none"
            aria-label="Agent mode"
          >
            <option value="AUTO" className="bg-[#0a101c]">
              AUTO
            </option>
            <option value="APPROVAL_REQUIRED" className="bg-[#0a101c]">
              APPROVAL
            </option>
            <option value="ADVISORY" className="bg-[#0a101c]">
              ADVISORY
            </option>
            <option value="SAFE_MODE" className="bg-[#0a101c]">
              SAFE MODE
            </option>
          </select>
          <button type="button" onClick={toggleSafe} className={safeMode ? 'btn-danger' : 'btn-ghost'}>
            {safeMode ? 'SAFE MODE ON' : 'SAFE MODE'}
          </button>
        </div>
      </div>
    </header>
  );
};
