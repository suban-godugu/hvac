'use client';

import React from 'react';
import { RotateCcw, AlertTriangle, ShieldCheck, CheckCircle2 } from 'lucide-react';
import { SupervisoryCycleResponse } from '@/lib/types';

interface RollbackPanelProps {
  data?: SupervisoryCycleResponse;
}

export const RollbackPanel: React.FC<RollbackPanelProps> = ({ data }) => {
  const rollbacks = data?.completed_actions?.filter(a => a.final_status === 'ROLLED_BACK') || [];

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-xl space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <RotateCcw className="w-4 h-4 text-amber-400" />
          <h3 className="text-sm font-bold text-slate-100">Automated Rollback & Fail-Safe Engine</h3>
        </div>
        <span className="text-xs font-mono text-slate-400">
          Reversion Priority: BACnet Pri 8
        </span>
      </div>

      {rollbacks.length === 0 ? (
        <div className="bg-slate-800/20 border border-slate-700/40 rounded-xl p-4 text-xs text-center text-slate-400 space-y-1">
          <ShieldCheck className="w-6 h-6 text-emerald-400 mx-auto" />
          <div className="font-semibold text-slate-200">Zero Rollbacks Triggered</div>
          <p className="text-[11px]">All dispatched supervisory actions successfully verified within thermodynamic tolerance.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {rollbacks.map((rb) => (
            <div key={rb.id} className="bg-amber-950/20 border border-amber-500/30 rounded-xl p-3.5 text-xs space-y-1.5">
              <div className="flex items-center justify-between font-mono">
                <span className="font-bold text-amber-300">{rb.point_id}</span>
                <span className="text-amber-400 font-bold bg-amber-900/60 px-2 py-0.5 rounded border border-amber-700">
                  ROLLED BACK
                </span>
              </div>
              <p className="text-slate-300">{rb.actual_result || rb.reason}</p>
              <div className="text-[10px] text-slate-400 pt-1 border-t border-slate-700/40 flex justify-between">
                <span>Restored Value: <strong className="text-slate-100 font-mono">{rb.rollback_value}</strong></span>
                <span>Automatic safety reversion</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
