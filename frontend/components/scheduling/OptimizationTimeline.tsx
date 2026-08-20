'use client';

import React from 'react';
import { Clock, Sun, Moon, Zap, Activity } from 'lucide-react';

export const OptimizationTimeline: React.FC = () => {
  const scheduleSegments = [
    { start: '00:00', end: '06:00', label: 'Unoccupied Night Setback (26.0°C DB)', color: 'bg-slate-800 text-slate-400 border-slate-700' },
    { start: '06:00', end: '07:18', label: 'O1 Delayed Start (Saved 78m Run)', color: 'bg-emerald-950/40 text-emerald-300 border-emerald-500/40' },
    { start: '07:18', end: '08:00', label: 'O1 Predictive Pull-Down (42m)', color: 'bg-sky-950/60 text-sky-300 border-sky-500/40' },
    { start: '08:00', end: '12:00', label: 'O2 & O3 Morning Trim & Respond', color: 'bg-cyan-950/40 text-cyan-300 border-cyan-500/40' },
    { start: '12:00', end: '15:00', label: 'O4 Peak Load Chiller Staging (76T)', color: 'bg-amber-950/40 text-amber-300 border-amber-500/40' },
    { start: '15:00', end: '17:15', label: 'O3 Afternoon SAT Lift Modulation', color: 'bg-emerald-950/40 text-emerald-300 border-emerald-500/40' },
    { start: '17:15', end: '18:00', label: 'O1 Early Coast-Down Shutdown (45m)', color: 'bg-amber-950/60 text-amber-300 border-amber-500/40' },
    { start: '18:00', end: '24:00', label: 'Evening Night Setback Floating', color: 'bg-slate-800 text-slate-400 border-slate-700' },
  ];

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-xl space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <Clock className="w-4 h-4 text-sky-400" />
          <h3 className="text-sm font-bold text-slate-100">24-Hour Autonomous Supervisory Optimization Timeline</h3>
        </div>
        <span className="text-xs font-mono text-slate-400">Skyline Corporate Center Schedule</span>
      </div>

      <div className="space-y-2">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 text-xs">
          {scheduleSegments.map((seg, idx) => (
            <div key={idx} className={`p-2.5 rounded-lg border flex flex-col justify-between ${seg.color}`}>
              <div className="flex items-center justify-between font-mono text-[10px] mb-1">
                <span className="font-bold">{seg.start} – {seg.end}</span>
                <span>Segment #{idx + 1}</span>
              </div>
              <p className="text-[11px] leading-tight font-medium">{seg.label}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
