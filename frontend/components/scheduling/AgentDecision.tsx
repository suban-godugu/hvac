'use client';

import React from 'react';
import { BrainCircuit, CheckCircle2, ChevronRight, FileCode } from 'lucide-react';

interface AgentDecisionProps {
  decisions?: any;
}

export const AgentDecision: React.FC<AgentDecisionProps> = ({ decisions = {} }) => {
  const o1 = decisions.o1_optimum_start_stop;
  const o2 = decisions.o2_space_temperature;
  const o3 = decisions.o3_master_ahu_sat?.[0];
  const o4 = decisions.o4_chiller_staging;

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <BrainCircuit className="w-4 h-4 text-sky-400" />
          <h2 className="text-sm font-semibold text-slate-200">Supervisory Agent Reasoning & Optimization Log</h2>
        </div>
        <span className="text-xs text-slate-400 font-mono">Cycle ID: #8492</span>
      </div>

      <div className="space-y-3 text-xs">
        {/* O1 Decision */}
        {o1 && (
          <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-3.5 space-y-1">
            <div className="flex items-center justify-between font-mono text-[11px]">
              <span className="font-bold text-sky-400">O1: Optimum Start/Stop</span>
              <span className="text-emerald-400 font-semibold">{o1.optimal_start_time ? `Delay: +${o1.start_delay_minutes}m` : 'Computed'}</span>
            </div>
            <p className="text-slate-300 leading-relaxed text-[11px]">
              Calculated <strong>{o1.required_precool_minutes} min</strong> pre-cool pull-down requirement. Delaying baseline start from <strong>{o1.baseline_start}</strong> to <strong>{o1.optimal_start_time}</strong>. Recommended coast-down stop at <strong>{o1.optimal_stop_time}</strong>.
            </p>
          </div>
        )}

        {/* O3 Decision */}
        {o3 && (
          <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-3.5 space-y-1">
            <div className="flex items-center justify-between font-mono text-[11px]">
              <span className="font-bold text-emerald-400">O3: Master AHU SAT</span>
              <span className="text-emerald-400 font-semibold">{o3.action}</span>
            </div>
            <p className="text-slate-300 leading-relaxed text-[11px]">
              {o3.reasoning} Adjusted AHU-1 SAT Setpoint from <strong>{o3.current_sat_sp}°C</strong> → <strong>{o3.target_sat_sp}°C</strong>. Net thermal lift saving: <strong>+{o3.net_savings_kw_est} kW</strong>.
            </p>
          </div>
        )}

        {/* O4 Decision */}
        {o4 && (
          <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-3.5 space-y-1">
            <div className="flex items-center justify-between font-mono text-[11px]">
              <span className="font-bold text-amber-400">O4: Chiller Staging</span>
              <span className="text-amber-400 font-semibold">{o4.staging_action}</span>
            </div>
            <p className="text-slate-300 leading-relaxed text-[11px]">
              Building load at <strong>{o4.load_tons} Tons</strong>. Single chiller CH-1 running at peak COP (<strong>{o4.plant_cop_est}</strong>). Chilled water supply reset setpoint: <strong>{o4.target_chws_sp}°C</strong> (+{o4.power_saved_est_kw} kW saved).
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
