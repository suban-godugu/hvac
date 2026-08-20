'use client';

import React from 'react';
import { CheckCircle2, AlertCircle, Sparkles } from 'lucide-react';

interface ConfidenceBadgeProps {
  confidence: number; // 0.0 to 1.0 or 0 to 100
  showLabel?: boolean;
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({ confidence, showLabel = true }) => {
  const score = confidence <= 1.0 ? Math.round(confidence * 100) : Math.round(confidence);
  
  let color = 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30';
  let dotColor = 'bg-emerald-400';

  if (score < 80) {
    color = 'bg-amber-500/10 text-amber-300 border-amber-500/30';
    dotColor = 'bg-amber-400';
  } else if (score < 60) {
    color = 'bg-rose-500/10 text-rose-300 border-rose-500/30';
    dotColor = 'bg-rose-400';
  }

  return (
    <span className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold border ${color}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor} animate-pulse`} />
      <span>{score}%</span>
      {showLabel && <span className="text-slate-400 font-normal">Conf.</span>}
    </span>
  );
};
