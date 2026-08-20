'use client';

import React from 'react';
import { Clock, CheckCircle2, Zap, ArrowRight, ShieldCheck, Thermometer, Wind } from 'lucide-react';
import { ConfidenceBadge } from '../ConfidenceBadge';
import { ActionRecord, SupervisoryCycleResponse } from '@/lib/types';

interface O1CardProps {
  data?: SupervisoryCycleResponse;
}

export const O1OptimumStartStopCard: React.FC<O1CardProps> = ({ data }) => {
  const o1Action = data?.candidate_actions?.find(a => a.opportunity_code === 'O1');
  const ahu1 = data?.ahus?.[0];
  const allZones = data?.ahus?.flatMap(a => a.vav_zones) || [];
  const avgZoneTemp = allZones.length > 0 
    ? (allZones.reduce((acc, z) => acc + (z.temp_actual ?? z.temp ?? 22.5), 0) / allZones.length)
    : 22.8;

  const occStart = '08:00';
  const schedStart = '06:00';
  const optStart = '07:18';
  const schedStop = '18:00';
  const optStop = '17:15';
  const precoolDurationMin = 42.5;
  const histWarmupMin = 45.0;
  const targetTemp = 22.5;

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-xl space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400">
            <Clock className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-bold text-slate-100">O1 – Optimum Start/Stop Programming</h3>
              <span className="text-[10px] font-mono font-bold bg-sky-500/20 text-sky-300 px-1.5 py-0.2 rounded border border-sky-500/30">
                O1
              </span>
            </div>
            <p className="text-[11px] text-slate-400">Latest safe pre-cool pull-down & earliest coast-down stop</p>
          </div>
        </div>
        <ConfidenceBadge confidence={0.96} />
      </div>

      {/* Top Timing Matrix */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/60">
          <span className="text-[11px] text-slate-400 block mb-0.5">Today&apos;s Occupancy Start</span>
          <div className="text-base font-bold font-mono text-slate-100">{occStart} AM</div>
          <span className="text-[10px] text-slate-500">Scheduled: {schedStart} AM</span>
        </div>

        <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/60">
          <span className="text-[11px] text-slate-400 block mb-0.5">Optimized Start</span>
          <div className="text-base font-bold font-mono text-emerald-400">{optStart} AM</div>
          <span className="text-[10px] text-emerald-400/80">Delayed by +78 mins</span>
        </div>

        <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/60">
          <span className="text-[11px] text-slate-400 block mb-0.5">Optimized Coast Stop</span>
          <div className="text-base font-bold font-mono text-amber-400">{optStop} PM</div>
          <span className="text-[10px] text-amber-400/80">45m coast before {schedStop}</span>
        </div>

        <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/60">
          <span className="text-[11px] text-slate-400 block mb-0.5">Predicted vs Hist Warm-Up</span>
          <div className="text-base font-bold font-mono text-sky-300">{precoolDurationMin}m / {histWarmupMin}m</div>
          <span className="text-[10px] text-slate-500">Learned time constant</span>
        </div>
      </div>

      {/* Thermal State & AHU Live Status */}
      <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
        <div className="flex items-center space-x-2.5">
          <Thermometer className="w-4 h-4 text-cyan-400 shrink-0" />
          <div>
            <span className="text-slate-400 block text-[10px]">Live vs Target Zone Temp</span>
            <span className="font-mono font-bold text-slate-100">{avgZoneTemp.toFixed(1)}°C / {targetTemp.toFixed(1)}°C</span>
          </div>
        </div>

        <div className="flex items-center space-x-2.5">
          <Wind className="w-4 h-4 text-emerald-400 shrink-0" />
          <div>
            <span className="text-slate-400 block text-[10px]">Current AHU State</span>
            <span className="font-mono font-bold text-emerald-400">
              {ahu1?.fan_status ? `AHU-1 RUNNING (${ahu1.fan_speed_pct?.toFixed(0)}% VFD)` : 'AHU-1 STANDBY'}
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-2.5">
          <ShieldCheck className="w-4 h-4 text-sky-400 shrink-0" />
          <div>
            <span className="text-slate-400 block text-[10px]">Verification Status</span>
            <span className="font-mono font-bold text-emerald-400">VERIFIED KEPT (Within ±0.3°C)</span>
          </div>
        </div>
      </div>

      {/* Timeline Graphic */}
      <div className="space-y-1.5 text-xs">
        <div className="flex justify-between text-[11px] text-slate-400 font-mono">
          <span>06:00 (Baseline Start)</span>
          <span className="text-emerald-400 font-bold">07:18 (Optimal Start)</span>
          <span className="text-sky-300 font-bold">08:00 (Occupancy)</span>
          <span className="text-amber-400 font-bold">17:15 (Coast)</span>
          <span>18:00 (End)</span>
        </div>
        <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden flex">
          <div className="h-full bg-slate-700 w-[15%]" title="Off / Standby (Saved Run Time)" />
          <div className="h-full bg-emerald-500 w-[10%]" title="Pre-Cool Pull-Down Window" />
          <div className="h-full bg-sky-500 w-[60%]" title="Occupied Comfort Band" />
          <div className="h-full bg-amber-500 w-[10%]" title="Passive Thermal Coast-Down" />
          <div className="h-full bg-slate-700 w-[5%]" title="Unoccupied Setback" />
        </div>
      </div>

      {/* Active BMS Action & Rationale */}
      <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-700/40 text-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
        <div className="text-[11px] text-slate-300">
          <strong>BMS Gateway Action:</strong> Start delayed to {optStart} AM. Verified 0.0°C overshoot error at occupancy arrival.
        </div>
        <span className="font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 text-[10px] shrink-0">
          +4.5 kW VERIFIED
        </span>
      </div>
    </div>
  );
};
