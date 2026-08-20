'use client';

import React from 'react';
import { Award, CheckCircle2, Clock, Activity, ArrowRight } from 'lucide-react';
import { SupervisoryCycleResponse } from '@/lib/types';

interface VerificationPanelProps {
  data?: SupervisoryCycleResponse;
}

export const VerificationPanel: React.FC<VerificationPanelProps> = ({ data }) => {
  const verifiedActions = data?.completed_actions?.filter(a => a.final_status === 'VERIFIED_KEPT') || [];

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-xl space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <Award className="w-4 h-4 text-emerald-400" />
          <h3 className="text-sm font-bold text-slate-100">Closed-Loop Response Verification Panel</h3>
        </div>
        <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
          Verification Window: 15–30 mins
        </span>
      </div>

      <div className="space-y-3">
        {verifiedActions.slice(0, 4).map((act) => (
          <div key={act.id} className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-3.5 text-xs space-y-1.5">
            <div className="flex items-center justify-between font-mono">
              <span className="font-bold text-sky-300">{act.opportunity_code} • {act.point_id}</span>
              <span className="text-emerald-400 font-bold bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/40">
                VERIFIED KEPT
              </span>
            </div>
            <p className="text-slate-300">{act.actual_result || act.expected_result}</p>
            <div className="text-[10px] text-slate-400 pt-1 border-t border-slate-700/40 flex items-center justify-between">
              <span>Timestamp: {act.timestamp ? act.timestamp.split('T')[1]?.substring(0, 8) || act.timestamp : '--'}</span>
              <span className="font-mono text-emerald-400 font-bold">Telemetry Verified</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
