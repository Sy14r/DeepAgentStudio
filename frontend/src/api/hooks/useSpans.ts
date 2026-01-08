/**
 * React Query hooks for Span API endpoints.
 *
 * Implements Phase 4 of ENHANCED_TRACING_SPEC.md - Frontend Tree View & Detail Panel.
 * Updated in Phase 7 with retry mechanism and improved error handling.
 */
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import {
  Span,
  SpanListResponse,
  SpanTreeResponse,
  SpanStats,
  SpanType,
  SpanStatus,
} from '@/api/types';

// ============================================================================
// Retry Configuration
// ============================================================================

/**
 * Default retry configuration for span queries.
 * Implements exponential backoff with max 3 retries.
 */
const RETRY_CONFIG = {
  retry: 3,
  retryDelay: (attemptIndex: number) => Math.min(1000 * 2 ** attemptIndex, 10000),
} as const;

/**
 * Stale time for span data (30 seconds).
 * Tree data is cached but refreshed when stale.
 */
const STALE_TIME = 30 * 1000;

// ============================================================================
// Query Keys
// ============================================================================

export const spanKeys = {
  all: ['spans'] as const,
  lists: () => [...spanKeys.all, 'list'] as const,
  list: (sessionId: number, filters?: SpanFilterParams) =>
    [...spanKeys.lists(), sessionId, filters] as const,
  trees: () => [...spanKeys.all, 'tree'] as const,
  tree: (sessionId: number) => [...spanKeys.trees(), sessionId] as const,
  details: () => [...spanKeys.all, 'detail'] as const,
  detail: (spanId: number) => [...spanKeys.details(), spanId] as const,
  stats: (sessionId: number) => [...spanKeys.all, 'stats', sessionId] as const,
};

// ============================================================================
// Filter Parameters
// ============================================================================

export interface SpanFilterParams {
  spanTypes?: SpanType[];
  statuses?: SpanStatus[];
  minDurationMs?: number;
  maxDurationMs?: number;
  hasError?: boolean;
  tags?: string[];
  search?: string;
  toolName?: string;
  modelName?: string;
  page?: number;
  pageSize?: number;
}

// ============================================================================
// Hooks
// ============================================================================

/**
 * Fetch flat list of spans for a session with optional filtering.
 * Includes retry logic with exponential backoff.
 */
export function useSpans(sessionId: number | undefined, filters: SpanFilterParams = {}) {
  const { page = 1, pageSize = 50, ...filterParams } = filters;

  return useQuery({
    queryKey: spanKeys.list(sessionId!, filters),
    queryFn: async () => {
      if (!sessionId) throw new Error('Session ID is required');

      const searchParams = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });

      // Add filter parameters
      if (filterParams.spanTypes?.length) {
        filterParams.spanTypes.forEach((t) => searchParams.append('span_type', t));
      }
      if (filterParams.statuses?.length) {
        filterParams.statuses.forEach((s) => searchParams.append('status', s));
      }
      if (filterParams.minDurationMs !== undefined) {
        searchParams.append('min_duration_ms', filterParams.minDurationMs.toString());
      }
      if (filterParams.maxDurationMs !== undefined) {
        searchParams.append('max_duration_ms', filterParams.maxDurationMs.toString());
      }
      if (filterParams.hasError !== undefined) {
        searchParams.append('has_error', filterParams.hasError.toString());
      }
      if (filterParams.tags?.length) {
        filterParams.tags.forEach((tag) => searchParams.append('tags', tag));
      }
      if (filterParams.search) {
        searchParams.append('search', filterParams.search);
      }
      if (filterParams.toolName) {
        searchParams.append('tool_name', filterParams.toolName);
      }
      if (filterParams.modelName) {
        searchParams.append('model_name', filterParams.modelName);
      }

      const response = await apiClient.get<SpanListResponse>(
        `/sessions/${sessionId}/spans?${searchParams.toString()}`
      );
      return response.data;
    },
    enabled: !!sessionId,
    staleTime: STALE_TIME,
    ...RETRY_CONFIG,
  });
}

/**
 * Fetch hierarchical span tree for a session.
 * Returns the root span with nested children for tree visualization.
 * Includes retry logic with exponential backoff.
 */
export function useSpanTree(sessionId: number | undefined, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: spanKeys.tree(sessionId!),
    queryFn: async () => {
      if (!sessionId) throw new Error('Session ID is required');
      const response = await apiClient.get<SpanTreeResponse>(
        `/sessions/${sessionId}/spans/tree`
      );
      return response.data;
    },
    enabled: options?.enabled !== undefined ? options.enabled && !!sessionId : !!sessionId,
    staleTime: STALE_TIME,
    ...RETRY_CONFIG,
  });
}

/**
 * Fetch a single span by ID with full details.
 * Includes retry logic with exponential backoff.
 */
export function useSpan(sessionId: number | undefined, spanId: number | undefined, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: spanKeys.detail(spanId!),
    queryFn: async () => {
      if (!sessionId) throw new Error('Session ID is required');
      if (!spanId) throw new Error('Span ID is required');
      const response = await apiClient.get<Span>(`/sessions/${sessionId}/spans/${spanId}`);
      return response.data;
    },
    enabled: options?.enabled !== undefined ? options.enabled && !!sessionId && !!spanId : !!sessionId && !!spanId,
    staleTime: STALE_TIME,
    ...RETRY_CONFIG,
  });
}

/**
 * Fetch aggregated statistics for spans in a session.
 * Includes retry logic with exponential backoff.
 */
export function useSpanStats(sessionId: number | undefined, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: spanKeys.stats(sessionId!),
    queryFn: async () => {
      if (!sessionId) throw new Error('Session ID is required');
      const response = await apiClient.get<SpanStats>(
        `/sessions/${sessionId}/spans/stats`
      );
      return response.data;
    },
    enabled: options?.enabled !== undefined ? options.enabled && !!sessionId : !!sessionId,
    staleTime: STALE_TIME,
    ...RETRY_CONFIG,
  });
}

/**
 * Prefetch span tree data for a session.
 * Useful for optimistic loading before user navigates to session details.
 */
export function usePrefetchSpanTree() {
  const queryClient = useQueryClient();

  return {
    prefetch: async (sessionId: number) => {
      await queryClient.prefetchQuery({
        queryKey: spanKeys.tree(sessionId),
        queryFn: async () => {
          const response = await apiClient.get<SpanTreeResponse>(
            `/sessions/${sessionId}/spans/tree`
          );
          return response.data;
        },
        staleTime: STALE_TIME,
      });
    },
  };
}

/**
 * Hook to manually invalidate and refetch span data.
 * Useful for retry buttons in error states.
 */
export function useRefreshSpanData() {
  const queryClient = useQueryClient();

  return {
    refreshTree: async (sessionId: number) => {
      await queryClient.invalidateQueries({ queryKey: spanKeys.tree(sessionId) });
    },
    refreshStats: async (sessionId: number) => {
      await queryClient.invalidateQueries({ queryKey: spanKeys.stats(sessionId) });
    },
    refreshAll: async (sessionId: number) => {
      await queryClient.invalidateQueries({ queryKey: [...spanKeys.all, sessionId] });
    },
  };
}
