'use client';

import React from 'react';
import { Clock, Thermometer, Wind, Server, CheckCircle2, AlertTriangle, ShieldCheck } from 'lucide-react';

interface AgentStatusProps {
  decisions?: any;
}

export const AgentStatus: React.FC<AgentStatusProps> = ({ decisions = {} }) => {
  const agents = [
    {
      id: 'o1',
      code: 'O1',
      name: 'Optimum Start/Stop',
      icon: Clock,
      status: 'Active',
      action: decisions.o1_optimum_start_stop?.optimal_start_time 
        ? `Start @ ${decisions.o1_optimum_start_stop.optimal_start_time} (Delay: ${decisions.o1_optimum_start_stop.start_delay_minutes}m)` 
        : 'Standby',
      savings: `${decisions.o1_optimum_start_stop?.estimated_kwh_savings || 18.5} kWh/day`,
      color: 'sky'
    },
    {
      id: 'o2',
      code: 'O2',
      name: 'Space Temperature Reset',
      icon: Thermometer,
      status: 'Active',
      action: `${decisions.o2_space_temperature?.unoccupied_count || 3} zones setback`,
      savings: `${decisions.o2_space_temperature?.total_shed_kw_est || 4.8} kW`,
      color: 'cyan'
    },
    {
      id: 'o3',
      code: 'O3',
      name: 'Master AHU SAT Reset',
      icon: Wind,
      status: 'Active',
      action: decisions.o3_master_ahu_sat?.[0]?.action 
        ? `${decisions.o3_master_ahu_sat[0].action} (${decisions.o3_master_ahu_sat[0].target_sat_sp}°C)`
        : 'Trim & Respond Active',
      savings: `${decisions.o3_master_ahu_sat?.[0]?.net_savings_kw_est || 3.2} kW`,
      color: 'emerald'
    },
    {
      id: 'o4',
      code: 'O4',
      name: 'Chiller Plant Staging',
      icon: Server,
      status: 'Active',
      action: decisions.o4_chiller_staging?.staging_action 
        ? `${decisions.o4_chiller_staging.staging_action} (CHWS: ${decisions.o4_chiller_staging.target_chws_sp}°C)`
        : '1 Chiller Active @ 64%',
      savings: `${decisions.o4_chiller_staging?.power_saved_est_kw || 5.6} kW`,
      color: 'amber'
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {agents.map((ag) => {
        const Icon = ag.icon;
        return (
          <div
            key={ag.id}
            className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex flex-col justify-between hover:border-slate-700 transition-all shadow-sm"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-2">
                  <div className="p-2 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400">
                    <Icon className="w-4 h-4" />
                  </div>
                  <div>
                    <span className="text-[10px] font-mono font-bold text-sky-400 bg-sky-950/60 px-1.5 py-0.5 rounded border border-sky-800/40">
                      {ag.code}
                    </span>
                  </div>
                </div>
                <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  {ag.status}
                </span>
              </div>
              <h3 className="text-xs font-semibold text-slate-200">{ag.name}</h3>
              <p className="text-[11px] text-slate-400 mt-1 font-mono line-clamp-1">{ag.action}</p>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
              <span className="text-slate-400">Est. Impact</span>
              <span className="font-semibold text-emerald-400 font-mono">+{ag.savings}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
};
