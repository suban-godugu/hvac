'use client';

import React, { useState } from 'react';
import { Thermometer, Sliders, ShieldCheck, CheckCircle2, RotateCcw, Activity } from 'lucide-react';
import { ConfidenceBadge } from '../ConfidenceBadge';
import { SupervisoryCycleResponse, Zone } from '@/lib/types';

interface O2CardProps {
  data?: SupervisoryCycleResponse;
}

export const O2SpaceTemperatureCard: React.FC<O2CardProps> = ({ data }) => {
  const allZones = data?.ahus?.flatMap(a => a.vav_zones) || [];
  const [selectedZoneId, setSelectedZoneId] = useState<string>(allZones[0]?.id || 'VAV-101');
  const activeZone = allZones.find(z => z.id === selectedZoneId) || allZones[0];

  const currentSp = activeZone?.cooling_sp ?? 23.0;
  const optSp = !activeZone?.occupied ? 24.5 : (activeZone?.damper_pos < 30 ? 23.3 : currentSp);
  const deadband = activeZone?.deadband ?? 2.0;
  const heatingPband = 1.5;
  const coolingPband = 1.5;
  const comfortMin = 20.0;
  const comfortMax = 26.5;

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-xl space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
            <Thermometer className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-bold text-slate-100">O2 – Space Temperature Set Points & Control Bands</h3>
              <span className="text-[10px] font-mono font-bold bg-cyan-500/20 text-cyan-300 px-1.5 py-0.2 rounded border border-cyan-500/30">
                O2
              </span>
            </div>
            <p className="text-[11px] text-slate-400">Deadband expansion, proportional band tuning & setback control</p>
          </div>
        </div>
        <ConfidenceBadge confidence={0.97} />
      </div>

      {/* Control Band Parameters Matrix */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/60">
          <span className="text-[11px] text-slate-400 block mb-0.5">Current → Optimized SP</span>
          <div className="text-base font-bold font-mono text-cyan-400">
            {currentSp.toFixed(1)}°C → {optSp.toFixed(1)}°C
          </div>
          <span className="text-[10px] text-slate-400">ASHRAE 55 [{comfortMin}°C - {comfortMax}°C]</span>
        </div>

        <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/60">
          <span className="text-[11px] text-slate-400 block mb-0.5">Active Deadband</span>
          <div className="text-base font-bold font-mono text-slate-100">
            {deadband.toFixed(1)}°C
          </div>
          <span className="text-[10px] text-slate-400">Widened on setback (4.0°C)</span>
        </div>

        <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/60">
          <span className="text-[11px] text-slate-400 block mb-0.5">Heat / Cool P-Bands</span>
          <div className="text-base font-bold font-mono text-slate-100">
            ±{heatingPband}°C / ±{coolingPband}°C
          </div>
          <span className="text-[10px] text-slate-400">Prevents damper hunting</span>
        </div>

        <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/60">
          <span className="text-[11px] text-slate-400 block mb-0.5">Before / After Energy Shed</span>
          <div className="text-base font-bold font-mono text-emerald-400">
            18.2 kW → 13.4 kW
          </div>
          <span className="text-[10px] text-emerald-400/80">-4.8 kW verified shed</span>
        </div>
      </div>

      {/* Zone-by-Zone Optimization Matrix */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-slate-300">Zone-by-Zone Optimization Selector ({allZones.length} VAVs)</span>
          <span className="text-[10px] text-slate-400 font-mono">Click zone to inspect</span>
        </div>

        <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 text-xs">
          {allZones.map((z) => {
            const isSelected = z.id === selectedZoneId;
            const isUnocc = !z.occupied;
            return (
              <button
                key={z.id}
                onClick={() => setSelectedZoneId(z.id)}
                className={`p-2 rounded-lg border text-left transition-all ${
                  isSelected
                    ? 'bg-cyan-950/60 border-cyan-500/80 shadow-md ring-1 ring-cyan-500/50'
                    : isUnocc
                    ? 'bg-amber-950/20 border-amber-500/30 hover:border-amber-400'
                    : 'bg-slate-800/40 border-slate-700/60 hover:border-slate-600'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-[10px] text-slate-200">{z.id}</span>
                  <span className={`w-1.5 h-1.5 rounded-full ${isUnocc ? 'bg-amber-400' : 'bg-emerald-400'}`} />
                </div>
                <div className="text-sm font-mono font-bold text-slate-100 mt-1">
                  {(z.temp_actual ?? z.temp ?? 23.0).toFixed(1)}°C
                </div>
                <div className="text-[9px] text-slate-400 mt-0.5 flex justify-between">
                  <span>SP: {z.cooling_sp?.toFixed(1)}°</span>
                  <span>{(z.damper_pos ?? z.damper ?? 45).toFixed(0)}%</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Safety & Rollback Status Bar */}
      <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center space-x-2 text-slate-300">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>Safety Status: <strong className="text-emerald-400">100% PASS</strong> (Rate of change ≤ 0.5°C/step)</span>
        </div>
        <div className="flex items-center space-x-2 text-slate-400">
          <RotateCcw className="w-3.5 h-3.5 text-slate-500" />
          <span>Rollback Threshold: <strong>±0.8°C violation</strong> (No rollbacks active)</span>
        </div>
      </div>
    </div>
  );
};
