/**
 * useSpanFilters - URL-based filter state management.
 *
 * Persists span filter state in URL query parameters for:
 * - Shareable filtered views
 * - Browser back/forward navigation
 * - Bookmark support
 *
 * Implements Phase 5 of ENHANCED_TRACING_SPEC.md.
 */
import { useCallback, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { SpanType, SpanStatus } from '@/api/types';
import { SpanFilterState, defaultFilterState } from './SpanFilters';

/**
 * URL parameter keys for filters.
 */
const PARAM_KEYS = {
  types: 'types',
  status: 'status',
  minDuration: 'minDur',
  maxDuration: 'maxDur',
  hasError: 'error',
  search: 'q',
  toolName: 'tool',
  modelName: 'model',
} as const;

/**
 * Parse URL search params into filter state.
 */
function parseFiltersFromParams(params: URLSearchParams): SpanFilterState {
  // Parse types
  const typesParam = params.get(PARAM_KEYS.types);
  const spanTypes = new Set<SpanType>(
    typesParam
      ? (typesParam.split(',').filter((t) => isValidSpanType(t)) as SpanType[])
      : []
  );

  // Parse status
  const statusParam = params.get(PARAM_KEYS.status);
  const status: SpanStatus | 'all' =
    statusParam && isValidStatus(statusParam) ? (statusParam as SpanStatus) : 'all';

  // Parse duration
  const minDurParam = params.get(PARAM_KEYS.minDuration);
  const maxDurParam = params.get(PARAM_KEYS.maxDuration);
  const minDurationMs = minDurParam ? parseInt(minDurParam, 10) : null;
  const maxDurationMs = maxDurParam ? parseInt(maxDurParam, 10) : null;

  // Parse error filter
  const errorParam = params.get(PARAM_KEYS.hasError);
  const hasError = errorParam === 'true' ? true : null;

  // Parse search
  const search = params.get(PARAM_KEYS.search) || '';

  // Parse tool/model
  const toolName = params.get(PARAM_KEYS.toolName) || '';
  const modelName = params.get(PARAM_KEYS.modelName) || '';

  return {
    spanTypes,
    status,
    minDurationMs: isNaN(minDurationMs!) ? null : minDurationMs,
    maxDurationMs: isNaN(maxDurationMs!) ? null : maxDurationMs,
    hasError,
    search,
    toolName,
    modelName,
  };
}

/**
 * Serialize filter state to URL search params.
 */
function serializeFiltersToParams(
  filters: SpanFilterState,
  currentParams: URLSearchParams
): URLSearchParams {
  const params = new URLSearchParams(currentParams);

  // Types
  if (filters.spanTypes.size > 0) {
    params.set(PARAM_KEYS.types, Array.from(filters.spanTypes).join(','));
  } else {
    params.delete(PARAM_KEYS.types);
  }

  // Status
  if (filters.status !== 'all') {
    params.set(PARAM_KEYS.status, filters.status);
  } else {
    params.delete(PARAM_KEYS.status);
  }

  // Duration
  if (filters.minDurationMs !== null) {
    params.set(PARAM_KEYS.minDuration, filters.minDurationMs.toString());
  } else {
    params.delete(PARAM_KEYS.minDuration);
  }

  if (filters.maxDurationMs !== null) {
    params.set(PARAM_KEYS.maxDuration, filters.maxDurationMs.toString());
  } else {
    params.delete(PARAM_KEYS.maxDuration);
  }

  // Error
  if (filters.hasError === true) {
    params.set(PARAM_KEYS.hasError, 'true');
  } else {
    params.delete(PARAM_KEYS.hasError);
  }

  // Search
  if (filters.search) {
    params.set(PARAM_KEYS.search, filters.search);
  } else {
    params.delete(PARAM_KEYS.search);
  }

  // Tool name
  if (filters.toolName) {
    params.set(PARAM_KEYS.toolName, filters.toolName);
  } else {
    params.delete(PARAM_KEYS.toolName);
  }

  // Model name
  if (filters.modelName) {
    params.set(PARAM_KEYS.modelName, filters.modelName);
  } else {
    params.delete(PARAM_KEYS.modelName);
  }

  return params;
}

/**
 * Validate span type string.
 */
function isValidSpanType(type: string): type is SpanType {
  const validTypes: SpanType[] = [
    'agent',
    'chain',
    'llm',
    'tool',
    'retriever',
    'embedding',
    'parser',
    'prompt',
    'memory',
    'thought',
    'error',
  ];
  return validTypes.includes(type as SpanType);
}

/**
 * Validate status string.
 */
function isValidStatus(status: string): status is SpanStatus | 'all' {
  return ['all', 'running', 'success', 'error'].includes(status);
}

/**
 * Hook for managing span filters with URL persistence.
 *
 * @param options.persist - Whether to persist filters in URL (default: true)
 * @returns Filter state and setter function
 */
export function useSpanFilters(options: { persist?: boolean } = {}) {
  const { persist = true } = options;
  const [searchParams, setSearchParams] = useSearchParams();

  // Parse current filters from URL
  const filters = useMemo(() => {
    if (!persist) return defaultFilterState;
    return parseFiltersFromParams(searchParams);
  }, [searchParams, persist]);

  // Update filters
  const setFilters = useCallback(
    (newFilters: SpanFilterState) => {
      if (persist) {
        const newParams = serializeFiltersToParams(newFilters, searchParams);
        setSearchParams(newParams, { replace: true });
      }
    },
    [persist, searchParams, setSearchParams]
  );

  // Update a single filter field
  const updateFilter = useCallback(
    <K extends keyof SpanFilterState>(key: K, value: SpanFilterState[K]) => {
      setFilters({ ...filters, [key]: value });
    },
    [filters, setFilters]
  );

  // Clear all filters
  const clearFilters = useCallback(() => {
    setFilters(defaultFilterState);
  }, [setFilters]);

  // Check if filters are active
  const hasFilters = useMemo(() => {
    return (
      filters.spanTypes.size > 0 ||
      filters.status !== 'all' ||
      filters.minDurationMs !== null ||
      filters.maxDurationMs !== null ||
      filters.hasError !== null ||
      filters.search !== '' ||
      filters.toolName !== '' ||
      filters.modelName !== ''
    );
  }, [filters]);

  // Generate shareable URL
  const getShareableUrl = useCallback(() => {
    const params = serializeFiltersToParams(filters, new URLSearchParams());
    const url = new URL(window.location.href);
    url.search = params.toString();
    return url.toString();
  }, [filters]);

  return {
    filters,
    setFilters,
    updateFilter,
    clearFilters,
    hasFilters,
    getShareableUrl,
  };
}

/**
 * Hook for managing span filters without URL persistence.
 * Useful for dialogs or embedded views.
 */
export function useLocalSpanFilters(initialFilters: SpanFilterState = defaultFilterState) {
  const [filters, setFiltersState] = useState(initialFilters);

  const setFilters = useCallback((newFilters: SpanFilterState) => {
    setFiltersState(newFilters);
  }, []);

  const updateFilter = useCallback(
    <K extends keyof SpanFilterState>(key: K, value: SpanFilterState[K]) => {
      setFiltersState((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  const clearFilters = useCallback(() => {
    setFiltersState(defaultFilterState);
  }, []);

  const hasFilters = useMemo(() => {
    return (
      filters.spanTypes.size > 0 ||
      filters.status !== 'all' ||
      filters.minDurationMs !== null ||
      filters.maxDurationMs !== null ||
      filters.hasError !== null ||
      filters.search !== '' ||
      filters.toolName !== '' ||
      filters.modelName !== ''
    );
  }, [filters]);

  return {
    filters,
    setFilters,
    updateFilter,
    clearFilters,
    hasFilters,
  };
}

export default useSpanFilters;
