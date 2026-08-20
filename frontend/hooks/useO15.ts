'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  fetchO15Commands,
  fetchO15Condensers,
  fetchO15Dashboard,
  fetchO15Fans,
  fetchO15History,
  fetchO15Recommendation,
  fetchO15Safety,
  fetchO15State,
  fetchO15Telemetry,
  postO15Apply,
  postO15Optimize,
  postO15Rollback,
  postO15SafeMode,
  postO15Verify,
} from '@/lib/hvac/o15Api';
import type { O15Dashboard } from '@/lib/hvac/o15Types';
import { historyPoints } from '@/lib/hvac/o15Format';
import { LIVE_POLL_MS } from '@/lib/hvac/poll';

const DASH = ['o15', 'dashboard'] as const;

export function useO15Dashboard() {
  return useQuery({
    queryKey: DASH,
    queryFn: fetchO15Dashboard,
    refetchInterval: (q) => (q.state.status === 'success' ? LIVE_POLL_MS : false),
  });
}

export function useO15State() {
  return useQuery({ queryKey: DASH, queryFn: fetchO15Dashboard, refetchInterval: LIVE_POLL_MS });
}

export function useO15Telemetry() {
  return useQuery({ queryKey: ['o15', 'telemetry'], queryFn: fetchO15Telemetry, refetchInterval: false });
}

export function useO15Condensers() {
  return useQuery({ queryKey: ['o15', 'condensers'], queryFn: fetchO15Condensers, refetchInterval: false });
}

export function useO15Fans() {
  return useQuery({ queryKey: ['o15', 'fans'], queryFn: fetchO15Fans, refetchInterval: false });
}

export function useO15Recommendation() {
  return useQuery({ queryKey: DASH, queryFn: fetchO15Dashboard, refetchInterval: LIVE_POLL_MS });
}

export function useO15Safety() {
  return useQuery({ queryKey: DASH, queryFn: fetchO15Dashboard, select: (d: O15Dashboard) => d.safety });
}

export function useO15History(hours: number, enabled = true) {
  return useQuery({
    queryKey: ['o15', 'history', hours],
    queryFn: () => fetchO15History(hours),
    refetchInterval: false,
    staleTime: 30_000,
    enabled,
    select: (d) => historyPoints(d),
  });
}

export function useO15Commands() {
  return useQuery({ queryKey: DASH, queryFn: fetchO15Dashboard, select: (d: O15Dashboard) => d.commands });
}

export function useO15Mutations() {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: ['o15'] });
  return {
    optimize: useMutation({ mutationFn: postO15Optimize, onSettled: invalidate }),
    apply: useMutation({
      mutationFn: ({ id, confirm }: { id: string; confirm: boolean }) => postO15Apply(id, confirm),
      onSettled: invalidate,
    }),
    verify: useMutation({ mutationFn: postO15Verify, onSettled: invalidate }),
    rollback: useMutation({ mutationFn: postO15Rollback, onSettled: invalidate }),
    safeMode: useMutation({ mutationFn: postO15SafeMode, onSettled: invalidate }),
  };
}

export { fetchO15Telemetry, fetchO15Recommendation, fetchO15Safety, fetchO15Commands, fetchO15State };
