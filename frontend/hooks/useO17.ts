'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchO17Opportunity, fetchOmDashboardTyped, postO17PlanningAction } from '@/lib/hvac/o17Api';
import { LIVE_POLL_MS, PLATFORM_POLL_MS } from '@/lib/hvac/poll';
import { fetchPlatformGate } from '@/lib/hvac/o20Api';

export function useO17Opportunity() {
  return useQuery({ queryKey: ['o17', 'opportunity'], queryFn: fetchO17Opportunity, refetchInterval: LIVE_POLL_MS });
}

export function useO17Dashboard() {
  return useQuery({ queryKey: ['om', 'dashboard'], queryFn: fetchOmDashboardTyped, refetchInterval: LIVE_POLL_MS });
}

export function useO17Building() {
  return useQuery({
    queryKey: ['platform', 'status'],
    queryFn: fetchPlatformGate,
    refetchInterval: PLATFORM_POLL_MS,
  });
}

export function useO17Mutations() {
  const qc = useQueryClient();
  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ['o17'] });
    void qc.invalidateQueries({ queryKey: ['om'] });
  };
  return {
    dispatchPlan: useMutation({ mutationFn: postO17PlanningAction, onSettled: invalidate }),
  };
}
