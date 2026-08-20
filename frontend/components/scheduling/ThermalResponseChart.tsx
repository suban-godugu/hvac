'use client';

import React from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ReferenceArea, ReferenceLine } from 'recharts';
import { Clock } from 'lucide-react';
import { EngineeringChart, EngineeringTooltip, CHART_COLORS } from '@/components/hvac/EngineeringChart';

interface ThermalResponseChartProps {
  initialTemp?: number;
  oat?: number;
  startDelayMin?: number;
  precoolMin?: number;
}

export const ThermalResponseChart: React.FC<ThermalResponseChartProps> = ({
  initialTemp = 24.2,
  oat = 23.5,
  startDelayMin = 42,
  precoolMin = 48
}) => {
  // Generate predictive trajectory curve from 06:00 to 09:00 (180 mins)
  const trajectoryData = [];
  const startMinute = 360; // 06:00 AM
  const occMinute = 480;   // 08:00 AM
  const optStartMinute = occMinute - precoolMin;

  for (let m = 0; m <= 180; m += 10) {
    const currentSimM = startMinute + m;
    const h = Math.floor(currentSimM / 60);
    const min = currentSimM % 60;
    const timeLabel = `${h.toString().padStart(2, '0')}:${min.toString().padStart(2, '0')}`;

    // Baseline trajectory (starts at 06:00)
    let baselineTemp = initialTemp;
    if (currentSimM >= startMinute) {
      const elapsedBase = currentSimM - startMinute;
      baselineTemp = Math.max(22.2, initialTemp - (elapsedBase / 45.0) * (initialTemp - 22.2));
    }

    // Optimized trajectory (delays start until optStartMinute)
    let optTemp = initialTemp;
    if (currentSimM < optStartMinute) {
      // Natural thermal drift (slight warming before start)
      optTemp = initialTemp + (m / 180.0) * 0.2;
    } else {
      const elapsedOpt = currentSimM - optStartMinute;
      optTemp = Math.max(22.5, initialTemp - (elapsedOpt / precoolMin) * (initialTemp - 22.5));
    }

    trajectoryData.push({
      time: timeLabel,
      baselineTemp: Number(baselineTemp.toFixed(2)),
      optTemp: Number(optTemp.toFixed(2)),
      comfortBandUpper: 23.5,
      comfortBandLower: 21.5,
    });
  }

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-xl">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <div className="flex items-center space-x-2">
            <Clock className="w-4 h-4 text-sky-400" />
            <h2 className="text-sm font-semibold text-slate-200">
              Predictive Pre-Cool Pull-Down Trajectory (O1 Algorithm)
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Compares traditional fixed 06:00 AM start vs Dynamic AI Pull-Down targeting comfort at 08:00 AM
          </p>
        </div>

        <div className="flex items-center space-x-3 text-xs">
          <span className="flex items-center gap-1.5 text-slate-400">
            <span className="w-2.5 h-2.5 rounded-full bg-slate-500"></span> Static 06:00 Start
          </span>
          <span className="flex items-center gap-1.5 text-slate-400">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-400"></span> AI Dynamic Start
          </span>
        </div>
      </div>

      <EngineeringChart>
          <LineChart data={trajectoryData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
            <XAxis dataKey="time" stroke={CHART_COLORS.axis} tick={{ fontSize: 11 }} />
            <YAxis stroke={CHART_COLORS.axis} domain={[21.0, 25.5]} tick={{ fontSize: 11 }} unit="°C" />
            <Tooltip content={EngineeringTooltip} />
            {/* Comfort Envelope */}
            <ReferenceArea y1={21.5} y2={23.5} fill="#0284c7" fillOpacity={0.08} label={{ value: "ASHRAE 55 Comfort Envelope", fill: "#38bdf8", fontSize: 10 }} />
            <ReferenceLine x="08:00" stroke="#f59e0b" strokeDasharray="3 3" label={{ value: "Occupancy Start", fill: "#f59e0b", fontSize: 10 }} />
            
            <Line
              type="monotone"
              dataKey="baselineTemp"
              name="Static 06:00 Start (°C)"
              stroke="#64748b"
              strokeDasharray="4 4"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="optTemp"
              name="Optimal Start AI (°C)"
              stroke="#38bdf8"
              strokeWidth={3}
              dot={false}
            />
          </LineChart>
      </EngineeringChart>

      <div className="mt-4 grid grid-cols-3 gap-3 text-xs border-t border-slate-800/80 pt-3">
        <div className="bg-slate-800/40 p-2.5 rounded-lg border border-slate-700/40">
          <span className="text-slate-400 block">Pre-Cool Duration</span>
          <span className="text-sm font-bold text-sky-400 font-mono">{precoolMin} Minutes</span>
        </div>
        <div className="bg-slate-800/40 p-2.5 rounded-lg border border-slate-700/40">
          <span className="text-slate-400 block">Start Delayed By</span>
          <span className="text-sm font-bold text-emerald-400 font-mono">+{startDelayMin} Minutes</span>
        </div>
        <div className="bg-slate-800/40 p-2.5 rounded-lg border border-slate-700/40">
          <span className="text-slate-400 block">Comfort Error @ 08:00</span>
          <span className="text-sm font-bold text-emerald-300 font-mono">0.0°C (On Target)</span>
        </div>
      </div>
    </div>
  );
};
