'use client';

import React from 'react';

interface SectionTitleProps {
  children: React.ReactNode;
  hint?: string;
}

export const SectionTitle: React.FC<SectionTitleProps> = ({ children, hint }) => {
  return (
    <div className="flex items-center justify-between gap-3 mb-3">
      <h2 className="text-[11px] font-semibold text-slate-400 uppercase tracking-[0.16em]">{children}</h2>
      {hint && <span className="text-[11px] font-mono text-slate-500">{hint}</span>}
    </div>
  );
};
