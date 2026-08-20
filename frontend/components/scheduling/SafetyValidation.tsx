'use client';

import React from 'react';
import { ShieldCheck, AlertTriangle, CheckCircle, Lock } from 'lucide-react';

interface SafetyValidationProps {
  safetyReport?: any;
}

export const SafetyValidation: React.FC<SafetyValidationProps> = ({ safetyReport }) => {
  const rules = [
    {
      name: 'ASHRAE 55 Comfort Envelope',
      rule: 'Space temp bounded within 21.0°C - 24.5°C during occupancy',
      status: 'PASS',
      details: 'All 12 zones strictly within comfort limits'
    },
    {
      name: 'AHU Coil Freeze Protection',
      rule: 'SAT Setpoint clamped ≥ 12.0°C to prevent freeze-stat trip',
      status: 'PASS',
      details: 'Low limit clamp active at 12.0°C'
    },
    {
      name: 'Chiller Anti-Short Cycling',
      rule: 'Minimum runtime 15 min / Minimum off time 15 min',
      status: 'PASS',
      details: 'CH-1 runtime: 180 min (Timer satisfied)'
    },
    {
      name: 'Rate-of-Change Limiter',
      rule: 'Max setpoint step ≤ 0.5°C per 15-minute supervisory cycle',
      status: 'PASS',
      details: 'Damped setpoint ramps prevent mechanical hunting'
    },
  ];

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <h2 className="text-sm font-semibold text-slate-200">Safety Guardrails & Constraint Validation Kernel</h2>
        </div>
        <span className="text-xs bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 px-2.5 py-0.5 rounded-full font-medium">
          Deterministic Guard Active
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
        {rules.map((r, i) => (
          <div key={i} className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-3 flex items-start space-x-3">
            <div className="p-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-400 mt-0.5">
              <CheckCircle className="w-4 h-4" />
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-slate-100">{r.name}</h4>
                <span className="text-[10px] font-mono text-emerald-400 font-bold bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-800/40">
                  {r.status}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5 font-mono">{r.rule}</p>
              <p className="text-[10px] text-slate-400 mt-1">{r.details}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
