'use client';

import React from 'react';
import { KPIGrid } from './KPIGrid';
import { EmptyState } from './EmptyState';
import { OpportunityWorkspace } from '@/components/hvac/guide/OpportunityWorkspace';
import { StatusBadge, toneForStatus } from './StatusBadge';
import type { OpportunityDef } from '@/lib/hvac/opportunityConfig';

export function OpportunityStudio(props: {
  def: OpportunityDef;
  live?: string | null;
  bms?: string | null;
  actions?: React.ReactNode;
  kpis?: { label: string; value?: React.ReactNode | null; detail?: React.ReactNode | null }[];
  children?: React.ReactNode;
  error?: string | null;
  loading?: boolean;
}) {
  return (
    <OpportunityWorkspace def={props.def} live={props.live} bms={props.bms} actions={props.actions}>
      {props.loading && <EmptyState title="LOADING TELEMETRY..." detail="Waiting for the HVAC API." />}
      {props.error && <EmptyState title={props.error} detail="Structured API error. Values are not fabricated." />}
      {props.kpis && <KPIGrid items={props.kpis} emptyText="—" />}
      {props.children}
    </OpportunityWorkspace>
  );
}

export function TelemetryPanel({ children }: { children: React.ReactNode }) {
  return (
    <div className="kpi-tile">
      <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-3">Telemetry</div>
      {children}
    </div>
  );
}

export function EngineeringInputs({ children }: { children: React.ReactNode }) {
  return (
    <div className="kpi-tile">
      <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-3">Engineering Inputs</div>
      {children}
    </div>
  );
}

export function RecommendationPanel({ children }: { children: React.ReactNode }) {
  return (
    <div className="kpi-tile">
      <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-3">Recommendation</div>
      {children}
    </div>
  );
}

export function SafetyPanel({ status, children }: { status?: string | null; children?: React.ReactNode }) {
  return (
    <div className="kpi-tile">
      <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-2">
        Safety <StatusBadge tone={toneForStatus(status)}>{status || 'UNKNOWN'}</StatusBadge>
      </div>
      {children}
    </div>
  );
}

export function SupervisoryDecisionPanel({ decision, children }: { decision?: string | null; children?: React.ReactNode }) {
  return (
    <div className="kpi-tile">
      <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-3">Supervisory Decision</div>
      <div className="text-lg font-mono text-emerald-300">{decision || '—'}</div>
      {children}
    </div>
  );
}

export function DispatchPanel({ children }: { children: React.ReactNode }) {
  return <div className="kpi-tile">{children}</div>;
}

export function VerificationPanel({ children }: { children: React.ReactNode }) {
  return <div className="kpi-tile">{children}</div>;
}

export function RollbackPanel({ children }: { children: React.ReactNode }) {
  return <div className="kpi-tile">{children}</div>;
}

export function CommandHistoryPanel({ children }: { children?: React.ReactNode }) {
  return (
    <div className="kpi-tile">
      <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-3">Command history</div>
      {children || <div className="font-mono text-xs text-slate-500">NO DATA</div>}
    </div>
  );
}

export function ApprovalPanel({ children }: { children?: React.ReactNode }) {
  return (
    <div className="kpi-tile">
      <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-3">Approval</div>
      {children}
    </div>
  );
}

export function AuditTimeline({ children }: { children: React.ReactNode }) {
  return (
    <div className="kpi-tile">
      <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-3">Audit</div>
      {children}
    </div>
  );
}
