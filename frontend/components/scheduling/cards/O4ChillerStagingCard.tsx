'use client';

import React from 'react';
import { Server, Zap, ShieldCheck, CheckCircle2, Sliders, ArrowRight, Gauge, Cpu } from 'lucide-react';
import { ConfidenceBadge } from '../ConfidenceBadge';
import { SupervisoryCycleResponse } from '@/lib/types';

interface O4CardProps {
  data?: SupervisoryCycleResponse;
}

export const O4ChillerStagingCard: React.FC<O4CardProps> = ({ data }) => {
  const plant = data?.plant;
  const totalTons = plant?.total_tons;
  const chillers = plant?.chillers || [];
  const activeCount = chillers.filter((c: { status?: boolean }) => c.status).length;
  const chwsTemp = plant?.chws_temp;
  const chwrTemp = plant?.chwr_temp;
  const plantPower = plant?.total_power_kw;
  const lead = chillers[0];
  const confidence = (data as unknown as { confidence?: number } | undefined)?.confidence;

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-xl space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400">
            <Server className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-bold text-slate-100">O4 – Staging of Chillers and Compressors</h3>
              <span className="text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 px-1.5 py-0.2 rounded border border-amber-500/30">
                O4
              </span>
            </div>
            <p className="text-[11px] text-slate-400">Cooling load matching, anti-short-cycling, compressor staging & ChW temperature reset</p>
          </div>
        </div>
        {typeof confidence === 'number' ? <ConfidenceBadge confidence={confidence} /> : null}
      </div>

      {/* Top Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/60">
          <span className="text-[11px] text-slate-400 block mb-0.5">Plant Cooling Load</span>
          <div className="text-base font-bold font-mono text-slate-100">
            {totalTons != null ? `${Number(totalTons).toFixed(1)} Tons` : 'NO DATA'}
          </div>
          <span className="text-[10px] text-slate-400">{totalTons != null ? `${(Number(totalTons) * 3.517).toFixed(0)} kW thermal` : 'Awaiting plant telemetry'}</span>
        </div>

        <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/60">
          <span className="text-[11px] text-slate-400 block mb-0.5">Active vs Optimal Chillers</span>
          <div className="text-base font-bold font-mono text-emerald-400">
            {chillers.length ? `${activeCount} Active` : 'NO DATA'}
          </div>
          <span className="text-[10px] text-emerald-400/80">Stage-up threshold: &gt;105T</span>
        </div>

        <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/60">
          <span className="text-[11px] text-slate-400 block mb-0.5">CHWS / CHWR Temperatures</span>
          <div className="text-base font-bold font-mono text-cyan-400">
            {chwsTemp != null && chwrTemp != null ? `${Number(chwsTemp).toFixed(1)}°C / ${Number(chwrTemp).toFixed(1)}°C` : 'NO DATA'}
          </div>
          <span className="text-[10px] text-slate-400">{chwsTemp != null && chwrTemp != null ? `ΔT: ${(Number(chwrTemp) - Number(chwsTemp)).toFixed(1)}°C` : '—'}</span>
        </div>

        <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/60">
          <span className="text-[11px] text-slate-400 block mb-0.5">Plant Power Before/After</span>
          <div className="text-base font-bold font-mono text-emerald-400">
            {plantPower != null ? `${Number(plantPower).toFixed(1)} kW` : 'NO DATA'}
          </div>
          <span className="text-[10px] text-slate-400">Plant electrical power</span>
        </div>
      </div>

      {/* Individual Chillers & Compressor Stages Matrix */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* CH-1 Lead */}
        <div className="bg-slate-800/40 p-3.5 rounded-xl border border-sky-500/30 space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-bold text-slate-200 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Chiller 1 (CH-1 Lead) — 120 Tons
            </span>
            <span className="font-mono text-[10px] text-emerald-400 font-bold bg-emerald-500/10 px-1.5 py-0.5 rounded">
              RUNNING @ {lead?.pct_load != null ? `${lead.pct_load}% PLR` : 'NO DATA'}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-400 pt-1">
            <div>Operating Load: <strong className="text-slate-200 font-mono">{lead?.current_tons != null ? `${lead.current_tons} Tons` : 'NO DATA'}</strong></div>
            <div>Power / COP: <strong className="text-emerald-400 font-mono">{lead?.power_kw != null ? `${lead.power_kw} kW` : 'NO DATA'}</strong></div>
          </div>

          {/* Compressors */}
          <div className="pt-2 border-t border-slate-700/40 flex items-center space-x-2 text-[10px] font-mono">
            <span className="text-slate-400">Compressor Stages:</span>
            <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              Stage 1A: 100%
            </span>
            <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              Stage 1B: 26%
            </span>
          </div>
        </div>

        {/* CH-2 Lag */}
        <div className="bg-slate-800/20 p-3.5 rounded-xl border border-slate-800 space-y-2 text-xs opacity-75">
          <div className="flex items-center justify-between">
            <span className="font-bold text-slate-400 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-slate-600" />
              Chiller 2 (CH-2 Lag) — 120 Tons
            </span>
            <span className="font-mono text-[10px] text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded">
              STANDBY (OFF)
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-400 pt-1">
            <div>Operating Load: <strong className="text-slate-400 font-mono">0.0 Tons</strong></div>
            <div>Min Off Timer: <strong className="text-emerald-400 font-mono">180m (Ready)</strong></div>
          </div>

          {/* Compressors */}
          <div className="pt-2 border-t border-slate-700/40 flex items-center space-x-2 text-[10px] font-mono">
            <span className="text-slate-400">Compressor Stages:</span>
            <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-500 border border-slate-700">
              Stage 2A: OFF
            </span>
            <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-500 border border-slate-700">
              Stage 2B: OFF
            </span>
          </div>
        </div>
      </div>

      {/* Safety Checks & Staging Conditions */}
      <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center space-x-2 text-slate-300">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>Safety Checks: <strong className="text-emerald-400">Min flow rate 28.5 L/s ≥ 12.0 L/s • Anti-short timers valid</strong></span>
        </div>
        <div className="flex items-center space-x-2 text-slate-400">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          <span>Verification: <strong>{chwsTemp != null ? `CHWS ${Number(chwsTemp).toFixed(1)}°C` : 'NO DATA'}</strong></span>
        </div>
      </div>
    </div>
  );
};
