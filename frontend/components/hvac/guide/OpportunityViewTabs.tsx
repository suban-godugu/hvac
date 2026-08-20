'use client';

import React, { useState } from 'react';

export type OpportunityStudioTab = 'ops' | 'guide';

export function useStudioViewTab(): [OpportunityStudioTab, (next: OpportunityStudioTab) => void] {
  const [tab, setTab] = useState<OpportunityStudioTab>(() => {
    if (typeof window === 'undefined') return 'ops';
    return new URLSearchParams(window.location.search).get('view') === 'guide' ? 'guide' : 'ops';
  });
  const onChange = (next: OpportunityStudioTab) => {
    setTab(next);
    if (typeof window === 'undefined') return;
    const url = new URL(window.location.href);
    if (next === 'guide') url.searchParams.set('view', 'guide');
    else url.searchParams.delete('view');
    window.history.replaceState({}, '', `${url.pathname}${url.search}${url.hash}`);
  };
  return [tab, onChange];
}

export function OpportunityViewTabs({
  tab,
  onChange,
  color,
}: {
  tab: OpportunityStudioTab;
  onChange: (next: OpportunityStudioTab) => void;
  color: string;
}) {
  const btn = (id: OpportunityStudioTab, label: string) => {
    const on = tab === id;
    return (
      <button
        type="button"
        role="tab"
        aria-selected={on}
        className={`px-3 py-1.5 text-[11px] font-mono uppercase tracking-wider rounded-md border transition-colors ${
          on ? 'text-slate-100' : 'text-slate-500 border-transparent hover:text-slate-300'
        }`}
        style={on ? { borderColor: color, color, background: `${color}18` } : undefined}
        onClick={() => onChange(id)}
      >
        {label}
      </button>
    );
  };

  return (
    <div role="tablist" aria-label="Opportunity view" className="flex gap-1 px-5 pb-4">
      {btn('ops', 'Operations')}
      {btn('guide', 'OEH guide')}
    </div>
  );
}
