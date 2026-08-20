'use client';

import React from 'react';
import { ChillerPlant as PlantType } from '@/lib/types';
import { Server, Zap, ArrowRight, Gauge, CheckCircle2, CircleOff } from 'lucide-react';

interface ChillerPlantProps {
  plant?: PlantType;
  onToggleChiller?: (chillerId: string, newState: boolean) => void;
}

export const ChillerPlant: React.FC<ChillerPlantProps> = ({ plant, onToggleChiller }) => {
  if (!plant) return null;

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-xl">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex items-center space-x-2">
          <Server className="w-4 h-4 text-amber-400" />
          <h2 className="text-sm font-semibold text-slate-200">
            Central Chiller Plant Topology & Staging Sequence (O4 Agent)
          </h2>
        </div>
        
        <div className="flex items-center space-x-4 text-xs">
          <div className="bg-slate-800/80 px-2.5 py-1 rounded-lg border border-slate-700">
            <span className="text-slate-400">Total Load: </span>
            <strong className="text-sky-300 font-mono">{plant.total_tons.toFixed(1)} Tons</strong>
          </div>
          <div className="bg-slate-800/80 px-2.5 py-1 rounded-lg border border-slate-700">
            <span className="text-slate-400">Plant Efficiency: </span>
            <strong className="text-emerald-400 font-mono">{(plant.plant_efficiency_kw_per_ton ?? plant.kw_per_ton ?? 0.56).toFixed(3)} kW/Ton</strong>
          </div>
        </div>
      </div>

      {/* Hydraulic Loop Readout */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
        <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-700/60">
          <span className="text-[11px] text-slate-400 block mb-0.5">ChW Supply Temp</span>
          <div className="text-lg font-bold font-mono text-cyan-400">{plant.chws_temp.toFixed(1)}°C</div>
          <span className="text-[10px] text-slate-500">Setpoint: {(plant.chws_setpoint ?? plant.chws_sp ?? 6.7).toFixed(1)}°C</span>
        </div>

        <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-700/60">
          <span className="text-[11px] text-slate-400 block mb-0.5">ChW Return Temp</span>
          <div className="text-lg font-bold font-mono text-slate-200">{plant.chwr_temp.toFixed(1)}°C</div>
          <span className="text-[10px] text-slate-500">Delta T: {(plant.chwr_temp - plant.chws_temp).toFixed(1)}°C</span>
        </div>

        <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-700/60">
          <span className="text-[11px] text-slate-400 block mb-0.5">ChW Loop Flow</span>
          <div className="text-lg font-bold font-mono text-slate-200">{(plant.flow_rate_lps ?? plant.flow_lps ?? 28.5).toFixed(1)} L/s</div>
          <span className="text-[10px] text-slate-500">Primary Header</span>
        </div>

        <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-700/60">
          <span className="text-[11px] text-slate-400 block mb-0.5">Total Electrical Power</span>
          <div className="text-lg font-bold font-mono text-amber-400">{(plant.total_power_kw ?? plant.power_kw ?? 42.0).toFixed(1)} kW</div>
          <span className="text-[10px] text-slate-500">Compressors + Aux</span>
        </div>
      </div>

      {/* Individual Chillers Graphic */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {plant.chillers.map((ch) => (
          <div
            key={ch.id}
            className={`p-4 rounded-xl border transition-all ${
              ch.status
                ? 'bg-slate-800/60 border-sky-500/40 shadow-sm shadow-sky-500/10'
                : 'bg-slate-900/40 border-slate-800/80 opacity-70'
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${ch.status ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'}`} />
                <h3 className="text-xs font-bold text-slate-100">{ch.name}</h3>
              </div>
              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                ch.status
                  ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                  : 'bg-slate-800 text-slate-400 border-slate-700'
              }`}>
                {ch.status ? 'LEAD RUNNING' : 'STANDBY (OFF)'}
              </span>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <div className="flex justify-between text-slate-400 mb-1">
                  <span>Capacity Load:</span>
                  <span className="font-mono text-slate-200 font-bold">{ch.pct_load.toFixed(1)}% ({ch.current_tons.toFixed(1)} / 120 Tons)</span>
                </div>
                <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      ch.pct_load > 85 ? 'bg-amber-500' : 'bg-emerald-400'
                    }`}
                    style={{ width: `${ch.pct_load}%` }}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-700/40">
                <div className="text-slate-400">
                  Power: <strong className="text-slate-200 font-mono">{ch.power_kw.toFixed(1)} kW</strong>
                </div>
                <div className="text-slate-400">
                  Operating COP: <strong className="text-emerald-400 font-mono">{ch.cop.toFixed(2)}</strong>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
