'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  fetchO16Commands,
  fetchO16Dashboard,
  fetchO16Equipment,
  fetchO16Health,
  fetchO16History,
  fetchO16Recommendation,
  fetchO16Safety,
  fetchO16Telemetry,
  postO16Apply,
  postO16Approve,
  postO16Optimize,
  postO16Rollback,
  postO16SafeMode,
  postO16Verify,
} from '@/lib/hvac/o16Api';
import type { O16Dashboard } from '@/lib/hvac/o16Types';
import { o16HistoryPoints } from '@/lib/hvac/o16Format';
import { LIVE_POLL_MS } from '@/lib/hvac/poll';

const DASH = ['o16', 'dashboard'] as const;

export function useO16Dashboard() {
  return useQuery({
    queryKey: DASH,
    queryFn: fetchO16Dashboard,
    refetchInterval: (q) => (q.state.status === 'success' ? LIVE_POLL_MS : false),
  });
}

export function useO16Telemetry(enabled = true) {
  return useQuery({ queryKey: ['o16', 'telemetry'], queryFn: fetchO16Telemetry, refetchInterval: false, enabled });
}

export function useO16Health() {
  return useQuery({ queryKey: DASH, queryFn: fetchO16Dashboard, select: (d: O16Dashboard) => d.header });
}

export function useO16Equipment(enabled = true) {
  return useQuery({ queryKey: ['o16', 'equipment'], queryFn: fetchO16Equipment, refetchInterval: false, enabled });
}

export function useO16Recommendation() {
  return useQuery({ queryKey: DASH, queryFn: fetchO16Dashboard, refetchInterval: LIVE_POLL_MS });
}

export function useO16Safety() {
  return useQuery({ queryKey: DASH, queryFn: fetchO16Dashboard, select: (d: O16Dashboard) => d.safety });
}

export function useO16History(hours: number, enabled = true) {
  return useQuery({
    queryKey: ['o16', 'history', hours],
    queryFn: () => fetchO16History(hours),
    refetchInterval: false,
    staleTime: 30_000,
    enabled,
    select: (d) => o16HistoryPoints(d),
  });
}

export function useO16Commands() {
  return useQuery({ queryKey: DASH, queryFn: fetchO16Dashboard, select: (d: O16Dashboard) => d.commands });
}

export function useO16Mutations() {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: ['o16'] });
  return {
    optimize: useMutation({ mutationFn: postO16Optimize, onSettled: invalidate }),
    apply: useMutation({
      mutationFn: ({ id, confirm }: { id: string; confirm: boolean }) => postO16Apply(id, confirm),
      onSettled: invalidate,
    }),
    approve: useMutation({ mutationFn: postO16Approve, onSettled: invalidate }),
    verify: useMutation({ mutationFn: postO16Verify, onSettled: invalidate }),
    rollback: useMutation({ mutationFn: postO16Rollback, onSettled: invalidate }),
    safeMode: useMutation({ mutationFn: postO16SafeMode, onSettled: invalidate }),
  };
}

export { fetchO16Telemetry, fetchO16Recommendation, fetchO16Safety, fetchO16Commands, fetchO16Health };
