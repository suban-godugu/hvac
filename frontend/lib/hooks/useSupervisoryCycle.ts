'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchStatus } from '../api';
import { SupervisoryCycleResponse } from '../types';
import { LIVE_POLL_MS } from '@/lib/hvac/poll';

export function useSupervisoryCycle() {
  const query = useQuery<SupervisoryCycleResponse>({
    queryKey: ['supervisory-status'],
    queryFn: fetchStatus,
    refetchInterval: LIVE_POLL_MS,
    staleTime: LIVE_POLL_MS,
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch
  };
}
