'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchO20Opportunity, fetchOmDashboardTyped, fetchPlatformGate, postO20ChangeRequest } from '@/lib/hvac/o20Api';
import { LIVE_POLL_MS, PLATFORM_POLL_MS } from '@/lib/hvac/poll';

export function useO20Opportunity() {
  return useQuery({ queryKey: ['o20', 'opportunity'], queryFn: fetchO20Opportunity, refetchInterval: LIVE_POLL_MS });
}

export function useO20Dashboard() {
  return useQuery({ queryKey: ['om', 'dashboard'], queryFn: fetchOmDashboardTyped, refetchInterval: LIVE_POLL_MS });
}

export function useO20Building() {
  return useQuery({
    queryKey: ['platform', 'status'],
    queryFn: fetchPlatformGate,
    refetchInterval: PLATFORM_POLL_MS,
  });
}

export function useO20Mutations() {
  const qc = useQueryClient();
  return {
    changeRequest: useMutation({
      mutationFn: postO20ChangeRequest,
      onSettled: () => {
        void qc.invalidateQueries({ queryKey: ['o20'] });
        void qc.invalidateQueries({ queryKey: ['om'] });
      },
    }),
  };
}
