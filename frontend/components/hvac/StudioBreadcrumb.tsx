'use client';

import Link from 'next/link';
import type { OpportunityDef } from '@/lib/hvac/opportunityConfig';

export function StudioBreadcrumb({ def }: { def: OpportunityDef }) {
  return (
    <nav className="text-[11px] font-mono text-slate-500 tracking-wide" aria-label="Breadcrumb">
      <Link href="/overview" className="hover:text-cyan-400">
        Fleet Overview
      </Link>
      <span className="text-slate-700"> / </span>
      <Link href={def.sectionHref} className="hover:text-cyan-400">
        {def.sectionTitle}
      </Link>
      <span className="text-slate-700"> / </span>
      <span className="text-cyan-400">
        {def.id} {def.shortLabel}
      </span>
    </nav>
  );
}
