'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchO18Opportunity, fetchOmDashboardTyped } from '@/lib/hvac/o18Api';
import { LIVE_POLL_MS, PLATFORM_POLL_MS } from '@/lib/hvac/poll';
import { fetchPlatformGate } from '@/lib/hvac/o20Api';

export function useO18Opportunity() {
  return useQuery({ queryKey: ['o18', 'opportunity'], queryFn: fetchO18Opportunity, refetchInterval: LIVE_POLL_MS });
}

export function useO18Dashboard() {
  return useQuery({ queryKey: ['om', 'dashboard'], queryFn: fetchOmDashboardTyped, refetchInterval: LIVE_POLL_MS });
}

export function useO18Building() {
  return useQuery({
    queryKey: ['platform', 'status'],
    queryFn: fetchPlatformGate,
    refetchInterval: PLATFORM_POLL_MS,
  });
}
