'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchPlatformGate } from '@/lib/hvac/o20Api';
import { fetchVentilationDashboard, fetchVentilationOpportunity, postVentilationAction } from '@/lib/hvac/ventilationApi';
import { apiJson } from '@/lib/api/client';
import { LIVE_POLL_MS, PLATFORM_POLL_MS } from '@/lib/hvac/poll';

export function useO10Opportunity() {
  return useQuery({
    queryKey: ['o10', 'opportunity'],
    queryFn: async () => {
      const r = await fetchVentilationOpportunity('O10');
      return r.data ?? null;
    },
    retry: 1,
    refetchInterval: LIVE_POLL_MS,
  });
}

export function useO10Dashboard() {
  return useQuery({
    queryKey: ['ventilation', 'dashboard'],
    queryFn: async () => {
      const r = await fetchVentilationDashboard();
      return r.data;
    },
    refetchInterval: LIVE_POLL_MS,
  });
}

export function useO10Platform() {
  return useQuery({
    queryKey: ['platform', 'status'],
    queryFn: fetchPlatformGate,
    refetchInterval: PLATFORM_POLL_MS,
  });
}

export function useO10Audit() {
  return useQuery({
    queryKey: ['o10', 'audit'],
    queryFn: async () => {
      try {
        return (await apiJson('/hvac/ventilation/O10/audit')) as { events?: unknown[] };
      } catch {
        return { events: [] as unknown[] };
      }
    },
    retry: false,
  });
}

export function useO10Mutations() {
  const qc = useQueryClient();
  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ['o10'] });
    void qc.invalidateQueries({ queryKey: ['ventilation'] });
  };
  return {
    dispatch: useMutation({
      mutationFn: (target?: number | null) => postVentilationAction('O10', 'dispatch', { target_value: target }),
      onSettled: invalidate,
    }),
    verify: useMutation({
      mutationFn: () => postVentilationAction('O10', 'verify'),
      onSettled: invalidate,
    }),
    rollback: useMutation({
      mutationFn: () => postVentilationAction('O10', 'rollback'),
      onSettled: invalidate,
    }),
  };
}
