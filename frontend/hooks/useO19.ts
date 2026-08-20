'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchO19Opportunity, fetchOmDashboardTyped, postO19MaintenanceAction } from '@/lib/hvac/o19Api';
import { fetchPlatformGate } from '@/lib/hvac/o20Api';
import { LIVE_POLL_MS, PLATFORM_POLL_MS } from '@/lib/hvac/poll';

export function useO19Opportunity() {
  return useQuery({ queryKey: ['o19', 'opportunity'], queryFn: fetchO19Opportunity, refetchInterval: LIVE_POLL_MS });
}

export function useO19Dashboard() {
  return useQuery({ queryKey: ['om', 'dashboard'], queryFn: fetchOmDashboardTyped, refetchInterval: LIVE_POLL_MS });
}

export function useO19Building() {
  return useQuery({
    queryKey: ['platform', 'status'],
    queryFn: fetchPlatformGate,
    refetchInterval: PLATFORM_POLL_MS,
  });
}

export function useO19Mutations() {
  const qc = useQueryClient();
  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ['o19'] });
    void qc.invalidateQueries({ queryKey: ['om'] });
  };
  return {
    maintenanceAction: useMutation({
      mutationFn: postO19MaintenanceAction,
      onSettled: invalidate,
    }),
  };
}
