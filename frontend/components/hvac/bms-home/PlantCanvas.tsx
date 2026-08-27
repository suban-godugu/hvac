'use client';

import React from 'react';
import { LAYER_GROUPS, type PlantEquipment, type PlantTone } from '@/lib/hvac/dashboardHome';

const TONE_DOT: Record<PlantTone, string> = {
  good: 'bg-emerald-400',
  stale: 'bg-amber-400',
  bad: 'bg-rose-400',
  missing: 'bg-slate-500',
  unmapped: 'bg-slate-600',
};

export function PlantCanvas({
  layers,
  selectedId,
  onSelect,
  compact,
}: {
  layers?: Record<string, PlantEquipment[]>;
  selectedId?: string | null;
  onSelect: (row: PlantEquipment) => void;
  compact?: boolean;
}) {
  const groups = LAYER_GROUPS.map((g) => ({ ...g, rows: layers?.[g.key] || [] })).filter((g) => g.rows.length > 0);
  if (groups.length === 0) return null;

  return (
    <div className={`glass-card ${compact ? 'p-3 space-y-2' : 'p-4 space-y-3'}`}>
      <div className="flex items-center justify-between gap-2">
        <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">Plant layers</div>
        <div className="flex flex-wrap gap-2 text-[10px] font-mono text-slate-500">
          {(['good', 'stale', 'bad', 'unmapped'] as PlantTone[]).map((t) => (
            <span key={t} className="inline-flex items-center gap-1">
              <span className={`w-1.5 h-1.5 rounded-full ${TONE_DOT[t]}`} />
              {t}
            </span>
          ))}
        </div>
      </div>
      <div className="space-y-3">
        {groups.map((g) => (
          <div key={g.key}>
            <div className="text-[10px] font-semibold tracking-[0.14em] uppercase text-slate-500 mb-1.5">{g.title}</div>
            <div className="space-y-1.5">
              {g.rows.map((row) => {
                const tone = (row.tone || 'unmapped') as PlantTone;
                const on = selectedId === row.equipment_id;
                const n = Object.keys(row.points || {}).length;
                return (
                  <button
                    key={row.equipment_id}
                    type="button"
                    onClick={() => onSelect(row)}
                    className={`w-full text-left rounded-lg border px-3 py-2.5 flex items-center justify-between gap-2 transition-transform ${
                      on
                        ? 'border-cyan-400/50 bg-cyan-500/10 -translate-y-0.5 shadow-[var(--glow-cyan)]'
                        : 'border-white/[0.08] bg-white/[0.02] hover:border-cyan-400/30'
                    }`}
                  >
                    <span className="inline-flex items-center gap-2 min-w-0">
                      <span className={`w-2 h-2 rounded-full shrink-0 ${TONE_DOT[tone]}`} />
                      <span className="font-mono text-[12px] text-slate-100 truncate">{row.equipment_id}</span>
                    </span>
                    <span className="text-[10px] font-mono text-slate-500">{n} pts</span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
