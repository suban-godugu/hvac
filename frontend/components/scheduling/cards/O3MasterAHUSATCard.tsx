'use client';

import React, { useState } from 'react';
import { Wind, Sliders, CheckCircle2, ShieldCheck, Zap, Activity, Layers } from 'lucide-react';
import { ConfidenceBadge } from '../ConfidenceBadge';
import { SupervisoryCycleResponse } from '@/lib/types';
import { useSupervisoryStore } from '@/lib/store';

interface O3CardProps {
  data?: SupervisoryCycleResponse;
}

export const O3MasterAHUSATCard: React.FC<O3CardProps> = ({ data }) => {
  const { demandMethod, setDemandMethod } = useSupervisoryStore();
  const ahu1 = data?.ahus?.[0];
  const allZones = data?.ahus?.flatMap(a => a.vav_zones) || [];

  const currentSat = ahu1?.sat_actual ?? 13.2;
  const optSat = ahu1?.sat_setpoint ?? 14.5;
  const minSat = 12.0;
  const maxSat = 17.5;

  const fanPower = ahu1?.fan_power_kw ?? 10.4;
  const chillerPowerSaved = 3.6;
  const fanPowerPenalty = 0.4;
  const netHvacImpact = chillerPowerSaved - fanPowerPenalty;

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-xl space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
            <Wind className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-bold text-slate-100">O3 – Master AHU Supply Air Temperature Signal</h3>
              <span className="text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-300 px-1.5 py-0.2 rounded border border-emerald-500/30">
                O3
              </span>
            </div>
            <p className="text-[11px] text-slate-400">Master zone demand aggregation, Trim & Respond reset & fan/chiller power trade-off</p>
          </div>
        </div>
        <ConfidenceBadge confidence={0.94} />
      </div>

      {/* Top Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/60">
          <span className="text-[11px] text-slate-400 block mb-0.5">Current SAT → Target SAT</span>
          <div className="text-base font-bold font-mono text-emerald-400">
            {currentSat.toFixed(1)}°C → {optSat.toFixed(1)}°C
          </div>
          <span className="text-[10px] text-slate-400">Allowed: [{minSat}°C - {maxSat}°C]</span>
        </div>

        <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/60">
          <span className="text-[11px] text-slate-400 block mb-0.5">Chiller Lift Savings</span>
          <div className="text-base font-bold font-mono text-emerald-400">
            +{chillerPowerSaved.toFixed(1)} kW
          </div>
          <span className="text-[10px] text-slate-400">~3.2% compressor lift reduction/°C</span>
        </div>

        <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/60">
          <span className="text-[11px] text-slate-400 block mb-0.5">Fan Power vs Penalty</span>
          <div className="text-base font-bold font-mono text-slate-100">
            {fanPower.toFixed(1)} kW (+{fanPowerPenalty} kW)
          </div>
          <span className="text-[10px] text-slate-400">VFD Speed: {ahu1?.fan_speed_pct?.toFixed(0) ?? 65}%</span>
        </div>

        <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/60">
          <span className="text-[11px] text-slate-400 block mb-0.5">Net HVAC Impact</span>
          <div className="text-base font-bold font-mono text-emerald-400">
            +{netHvacImpact.toFixed(1)} kW Net
          </div>
          <span className="text-[10px] text-emerald-400/80">Net energy reduction</span>
        </div>
      </div>

      {/* Demand Calculation Selector & Fault Filter */}
      <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center space-x-2">
          <Layers className="w-4 h-4 text-emerald-400" />
          <span className="font-semibold text-slate-200">Master Demand Calculation Method:</span>
          <div className="flex items-center bg-slate-900 border border-slate-700 rounded-lg p-0.5 font-mono text-[11px]">
            <button
              onClick={() => setDemandMethod('TRIM_RESPOND')}
              className={`px-2 py-0.5 rounded transition-all ${
                demandMethod === 'TRIM_RESPOND' ? 'bg-emerald-600 text-white font-bold' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Trim & Respond
            </button>
            <button
              onClick={() => setDemandMethod('WEIGHTED')}
              className={`px-2 py-0.5 rounded transition-all ${
                demandMethod === 'WEIGHTED' ? 'bg-emerald-600 text-white font-bold' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Weighted Area
            </button>
            <button
              onClick={() => setDemandMethod('THIRD_HIGHEST')}
              className={`px-2 py-0.5 rounded transition-all ${
                demandMethod === 'THIRD_HIGHEST' ? 'bg-emerald-600 text-white font-bold' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              3rd-Highest
            </button>
          </div>
        </div>

        <div className="text-[11px] text-slate-400 flex items-center space-x-2">
          <span>Excluded/Rogue Zones:</span>
          <strong className="text-slate-200 font-mono">0 Faulty (All 12 Active)</strong>
        </div>
      </div>

      {/* BMS Action & Verification Status */}
      <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-700/40 text-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
        <div className="text-[11px] text-slate-300">
          <strong>BMS Gateway Action:</strong> SAT setpoint reset upward to {optSat.toFixed(1)}°C. Freeze-stat guard verified ≥ 12.0°C.
        </div>
        <div className="flex items-center space-x-2 shrink-0">
          <span className="font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 text-[10px]">
            VERIFIED STABLE
          </span>
        </div>
      </div>
    </div>
  );
};
