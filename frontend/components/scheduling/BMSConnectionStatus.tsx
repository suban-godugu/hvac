'use client';

import React, { useState } from 'react';

interface BMSConnectionStatusProps {
  isConnected?: boolean;
  telemetryAgeSec?: number;
}

export const BMSConnectionStatus: React.FC<BMSConnectionStatusProps> = ({
  isConnected,
  telemetryAgeSec
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const connected = isConnected === true;
  const unknown = isConnected === undefined;

  return (
    <div className="relative inline-block text-xs font-mono">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`px-2 py-1 border rounded flex items-center gap-1.5 ${
          unknown
            ? 'border-white/[0.08] text-slate-400'
            : connected
            ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400 font-semibold'
            : 'border-rose-500/30 bg-rose-500/10 text-rose-400 font-semibold'
        }`}
      >
        <span>{unknown ? 'BMS —' : connected ? 'BMS CONNECTED' : 'BMS OFFLINE'}</span>
      </button>

      {isOpen && (
        <div
          className="absolute right-0 mt-1 w-64 bg-[#0b1120] border border-[#334155] p-3 shadow-xl z-50 text-xs font-mono space-y-2 text-slate-300"
        >
          <div className="flex items-center justify-between pb-2 border-b border-[#1e293b]">
            <span className="font-bold text-slate-100 uppercase text-[10px]">BMS Gateway</span>
          </div>
          <div className="space-y-1.5 text-[11px]">
            <div className="flex justify-between text-slate-400">
              <span>Status:</span>
              <span className={connected ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>
                {unknown ? 'UNKNOWN' : connected ? 'CONNECTED' : 'OFFLINE'}
              </span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Telemetry age:</span>
              <span className="text-slate-200">{telemetryAgeSec == null ? '—' : `${telemetryAgeSec}s`}</span>
            </div>
          </div>

          <div className="pt-2 border-t border-[#1e293b]">
            <button
              onClick={() => setIsOpen(false)}
              className="w-full text-center py-1 bg-[#1e293b] hover:bg-[#334155] text-slate-200 border border-[#334155] text-[10px]"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
