'use client';

import React from 'react';
import { AHU } from '@/lib/types';
import { Wind, Sliders, ArrowUpRight, ArrowDownRight, Gauge, Check } from 'lucide-react';

interface SATControlProps {
  ahus?: AHU[];
  onSetSAT?: (ahuId: string, sp: number) => void;
}

export const SATControl: React.FC<SATControlProps> = ({ ahus = [], onSetSAT }) => {
  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Wind className="w-4 h-4 text-emerald-400" />
          <h2 className="text-sm font-semibold text-slate-200">
            Master AHU Supply Air Temperature (Trim & Respond Control)
          </h2>
        </div>
        <span className="text-xs text-slate-400 font-mono">ASHRAE Guideline 36</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {ahus.map((ahu) => {
          const isWarmer = ahu.sat_setpoint > 13.0;
          return (
            <div
              key={ahu.id}
              className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-4 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="text-xs font-bold text-slate-200">{ahu.name}</h3>
                    <span className="text-[10px] text-slate-400 font-mono">{ahu.id} • VAV Distribution</span>
                  </div>
                  <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border flex items-center gap-1 ${
                    isWarmer 
                      ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                      : 'bg-sky-500/10 text-sky-300 border-sky-500/20'
                  }`}>
                    {isWarmer ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                    {isWarmer ? 'Reset Warmer (Trim)' : 'Cooler (Respond)'}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3 mb-4">
                  <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800">
                    <span className="text-[11px] text-slate-400 block mb-0.5">Discharge SAT</span>
                    <div className="text-xl font-bold font-mono text-slate-100">{ahu.sat_actual.toFixed(1)}°C</div>
                    <span className="text-[10px] text-slate-500">Sensor actual</span>
                  </div>

                  <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800">
                    <span className="text-[11px] text-slate-400 block mb-0.5">Supervisory Setpoint</span>
                    <div className="text-xl font-bold font-mono text-emerald-400">{ahu.sat_setpoint.toFixed(1)}°C</div>
                    <span className="text-[10px] text-emerald-400/80">AI Optimized</span>
                  </div>
                </div>

                {/* Fan VFD & Power */}
                <div className="space-y-2 text-xs">
                  <div className="flex items-center justify-between text-slate-400">
                    <span>Supply Fan VFD Speed:</span>
                    <strong className="font-mono text-slate-200">{(ahu.fan_speed_pct ?? ahu.fan_speed ?? 65.0).toFixed(1)}%</strong>
                  </div>
                  <div className="flex items-center justify-between text-slate-400">
                    <span>Fan Electrical Power:</span>
                    <strong className="font-mono text-slate-200">{(ahu.fan_power_kw ?? ahu.fan_kw ?? 10.0).toFixed(1)} kW</strong>
                  </div>
                </div>
              </div>

              {/* Setpoint Slider Control */}
              <div className="mt-4 pt-3 border-t border-slate-700/40">
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="text-slate-400">Manual Override Trim:</span>
                  <span className="font-mono text-sky-400 font-bold">{ahu.sat_setpoint.toFixed(1)}°C</span>
                </div>
                <input
                  type="range"
                  min="12.0"
                  max="17.5"
                  step="0.5"
                  value={ahu.sat_setpoint}
                  onChange={(e) => onSetSAT && onSetSAT(ahu.id, parseFloat(e.target.value))}
                  className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-sky-400"
                />
                <div className="flex justify-between text-[10px] text-slate-500 mt-1 font-mono">
                  <span>12.0°C (Max Cool)</span>
                  <span>17.5°C (Max Trim)</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
