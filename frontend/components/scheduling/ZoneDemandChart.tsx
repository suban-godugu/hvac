'use client';

import React from 'react';
import { Zone } from '@/lib/types';
import { Thermometer, UserCheck, UserX, AlertCircle } from 'lucide-react';

interface ZoneDemandChartProps {
  zones?: Zone[];
  onZoneClick?: (zone: Zone) => void;
}

export const ZoneDemandChart: React.FC<ZoneDemandChartProps> = ({ zones = [], onZoneClick }) => {
  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Thermometer className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-semibold text-slate-200">
            Zone Thermal Comfort & Damper Position Heatmap (O2 Agent)
          </h2>
        </div>
        <div className="flex items-center space-x-3 text-xs text-slate-400">
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-sm bg-sky-500/30 border border-sky-500"></span> Satisfied
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-sm bg-amber-500/30 border border-amber-500"></span> Unoccupied Setback
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-sm bg-rose-500/30 border border-rose-500"></span> High Cooling Call
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {zones.map((zone) => {
          const zDamper = zone.damper_pos ?? zone.damper ?? 45.0;
          const zTemp = zone.temp_actual ?? zone.temp ?? 23.0;
          const isHighDemand = zDamper > 80;
          const isOvercooled = zTemp < zone.heating_sp;
          
          let cardBg = "bg-slate-800/40 border-slate-700/60";
          let badgeColor = "text-sky-400 bg-sky-500/10 border-sky-500/20";
          
          if (!zone.occupied) {
            cardBg = "bg-amber-950/20 border-amber-500/30";
            badgeColor = "text-amber-400 bg-amber-500/10 border-amber-500/20";
          } else if (isHighDemand) {
            cardBg = "bg-rose-950/20 border-rose-500/30";
            badgeColor = "text-rose-400 bg-rose-500/10 border-rose-500/20";
          }

          return (
            <div
              key={zone.id}
              onClick={() => onZoneClick && onZoneClick(zone)}
              className={`p-3 rounded-xl border ${cardBg} hover:scale-[1.02] transition-all cursor-pointer flex flex-col justify-between`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-mono font-bold text-slate-300">{zone.id}</span>
                  {zone.occupied ? (
                    <UserCheck className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <UserX className="w-3.5 h-3.5 text-amber-400" />
                  )}
                </div>

                <div className="text-xl font-bold font-mono text-slate-100 mb-1">
                  {zTemp.toFixed(1)}°C
                </div>
                <div className="text-[10px] text-slate-400 space-y-0.5">
                  <div>Cool SP: <strong className="text-slate-200">{zone.cooling_sp.toFixed(1)}°C</strong></div>
                  <div>Deadband: <strong className="text-slate-200">{zone.deadband.toFixed(1)}°C</strong></div>
                </div>
              </div>

              <div className="mt-3 pt-2 border-t border-slate-700/40">
                <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
                  <span>Damper</span>
                  <span className="font-mono font-bold text-slate-200">{zDamper.toFixed(0)}%</span>
                </div>
                <div className="w-full h-1.5 bg-slate-700/80 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      isHighDemand ? 'bg-rose-500' : (!zone.occupied ? 'bg-amber-500' : 'bg-sky-400')
                    }`}
                    style={{ width: `${Math.min(100, zDamper)}%` }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
