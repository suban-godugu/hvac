'use client';

import React from 'react';
import { AlertCircle, CheckCircle2, Radio } from 'lucide-react';

interface StatusBannerProps {
  text: string;
  type?: 'success' | 'error' | 'info';
}

export const StatusBanner: React.FC<StatusBannerProps> = ({ text, type = 'info' }) => {
  const styles = {
    success: 'bg-emerald-950/40 border-emerald-500/30 text-emerald-300',
    error: 'bg-rose-950/40 border-rose-500/30 text-rose-300',
    info: 'bg-cyan-950/40 border-cyan-500/30 text-cyan-300',
  };

  const Icon = type === 'success' ? CheckCircle2 : type === 'error' ? AlertCircle : Radio;

  return (
    <div className={`px-4 py-3 rounded-xl border flex items-center gap-2.5 text-xs font-medium ${styles[type]}`}>
      <Icon className="w-4 h-4 shrink-0" />
      <span>{text}</span>
    </div>
  );
};
