'use client';

import React from 'react';
import { AgentMode } from '@/lib/types';
import { ShieldCheck, UserCheck, Play, Lock } from 'lucide-react';
import { setAgentMode } from '@/lib/api';

interface ModeSwitcherProps {
  currentMode: AgentMode;
  onModeChange?: (newMode: AgentMode) => void;
}

const MODES: Array<{ mode: AgentMode; label: string; desc: string; icon: any; color: string }> = [
  {
    mode: 'AUTO',
    label: 'Auto Dispatch',
    desc: 'Autonomous closed-loop control through Safety Engine & BMS Gateway',
    icon: Play,
    color: 'emerald'
  },
  {
    mode: 'APPROVAL_REQUIRED',
    label: 'Approval Required',
    desc: 'Candidate actions require human operator sign-off before dispatch',
    icon: UserCheck,
    color: 'sky'
  },
  {
    mode: 'ADVISORY',
    label: 'Advisory Mode',
    desc: 'Generates real-time optimization suggestions without writing to BMS',
    icon: ShieldCheck,
    color: 'amber'
  },
  {
    mode: 'SAFE_MODE',
    label: 'Safe Mode (Lock)',
    desc: 'Safety fallback maintaining static baseline setpoints',
    icon: Lock,
    color: 'rose'
  }
];

export const ModeSwitcher: React.FC<ModeSwitcherProps> = ({ currentMode = 'AUTO', onModeChange }) => {
  const handleSelect = async (mode: AgentMode) => {
    try {
      await setAgentMode(mode);
      if (onModeChange) onModeChange(mode);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
          Supervisory Operating Mode
        </h3>
        <span className="text-[11px] font-mono text-slate-400">Deterministic Control Policy</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {MODES.map((m) => {
          const Icon = m.icon;
          const isActive = currentMode === m.mode;
          return (
            <button
              key={m.mode}
              onClick={() => handleSelect(m.mode)}
              className={`p-3 rounded-xl border text-left transition-all flex flex-col justify-between ${
                isActive
                  ? 'bg-slate-800 border-sky-500/80 shadow-md shadow-sky-500/10 ring-1 ring-sky-500/50'
                  : 'bg-slate-950/40 border-slate-800 hover:border-slate-700 hover:bg-slate-800/30'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <div className={`p-1.5 rounded-lg ${isActive ? 'bg-sky-500/20 text-sky-400' : 'bg-slate-800 text-slate-400'}`}>
                    <Icon className="w-3.5 h-3.5" />
                  </div>
                  <span className="text-xs font-bold text-slate-200">{m.label}</span>
                </div>
                {isActive && (
                  <span className="w-2 h-2 rounded-full bg-sky-400 animate-pulse"></span>
                )}
              </div>
              <p className="text-[10px] text-slate-400 leading-relaxed">{m.desc}</p>
            </button>
          );
        })}
      </div>
    </div>
  );
};
