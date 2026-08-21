'use client';

import React from 'react';
import Link from 'next/link';
import { ArrowLeft, LucideIcon } from 'lucide-react';
import { StatusBadge } from './StatusBadge';

interface PageHeaderProps {
  backHref?: string;
  backLabel?: string;
  crumb?: string;
  icon: LucideIcon;
  title: string;
  subtitle?: string;
  badge?: string;
  actions?: React.ReactNode;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  backHref,
  backLabel,
  crumb,
  icon: Icon,
  title,
  subtitle,
  badge,
  actions,
}) => {
  return (
    <div className="space-y-5 pb-1">
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
      <div className="min-w-0">
        {(backHref || crumb) && (
          <div className="flex items-center gap-2 text-xs font-mono text-slate-500 mb-3">
            {backHref && (
              <Link href={backHref} className="hover:text-cyan-400 flex items-center gap-1 transition-colors">
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>{backLabel}</span>
              </Link>
            )}
            {crumb && (
              <>
                <span className="text-slate-700">/</span>
                <span className="text-cyan-400 font-semibold">{crumb}</span>
              </>
            )}
          </div>
        )}
        <div className="flex items-start gap-3.5">
          <div className="w-11 h-11 rounded-[10px] bg-gradient-to-br from-cyan-400/20 to-cyan-500/5 border border-cyan-400/30 shadow-[var(--glow-cyan)] flex items-center justify-center text-cyan-300 shrink-0">
            <Icon className="w-5 h-5" />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-[1.7rem] font-semibold text-white tracking-tight leading-tight">{title}</h1>
              {badge && (
                <StatusBadge tone="neutral" pulse={false}>
                  {badge}
                </StatusBadge>
              )}
            </div>
            {subtitle && <p className="text-[13px] text-slate-400 mt-1.5 leading-relaxed max-w-3xl">{subtitle}</p>}
          </div>
        </div>
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2 shrink-0">{actions}</div>}
      </div>
      <div className="page-rule" />
    </div>
  );
};
