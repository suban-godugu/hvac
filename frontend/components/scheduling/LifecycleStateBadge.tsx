'use client';

import React from 'react';
import { AgentLifecycleState } from '@/lib/types';
import { RefreshCw, ArrowRight } from 'lucide-react';

interface LifecycleStateBadgeProps {
  state: AgentLifecycleState;
}

const LIFECYCLE_STEPS: AgentLifecycleState[] = [
  'OBSERVE',
  'VALIDATE_DATA',
  'BUILD_STATE',
  'DETECT_OPPORTUNITIES',
  'GENERATE_CANDIDATES',
  'EVALUATE_CANDIDATES',
  'SAFETY_CHECK',
  'EXECUTE',
  'VERIFY',
  'KEEP_OR_ROLLBACK',
  'LEARN',
  'IDLE'
];

export const LifecycleStateBadge: React.FC<LifecycleStateBadgeProps> = ({ state = 'IDLE' }) => {
  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <RefreshCw className="w-4 h-4 text-sky-400 animate-spin" style={{ animationDuration: '6s' }} />
          <h2 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
            Closed-Loop Autonomous Supervisory Lifecycle
          </h2>
        </div>
        <span className="text-[11px] font-mono font-bold bg-sky-500/10 text-sky-300 border border-sky-500/30 px-2.5 py-0.5 rounded-full">
          Current: {state}
        </span>
      </div>

      {/* Horizontal Step Pipeline Visualizer */}
      <div className="overflow-x-auto pb-2">
        <div className="flex items-center space-x-1 min-w-max">
          {LIFECYCLE_STEPS.map((step, idx) => {
            const isCurrent = step === state;
            return (
              <React.Fragment key={step}>
                <div
                  className={`px-2.5 py-1 rounded-lg text-[10px] font-mono font-semibold transition-all ${
                    isCurrent
                      ? 'bg-sky-500 text-white shadow-lg shadow-sky-500/30 scale-105 border border-sky-400'
                      : 'bg-slate-800/60 text-slate-400 border border-slate-700/60'
                  }`}
                >
                  {step}
                </div>
                {idx < LIFECYCLE_STEPS.length - 1 && (
                  <ArrowRight className="w-2.5 h-2.5 text-slate-600 shrink-0" />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
};
