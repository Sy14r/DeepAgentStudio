/**
 * Trace Components - Phase 3+
 *
 * Components for visualizing and interacting with hierarchical spans
 * during agent execution.
 */

// Phase 3 - Real-time indicators
export { LiveSpanIndicator } from './LiveSpanIndicator';

// Phase 4 - Tree view and detail panel
export { SpanTypeIcon, SpanTypeBadge, getSpanTypeConfig } from './SpanTypeIcon';
export { SpanTreeNode } from './SpanTreeNode';
export { SpanTreeView } from './SpanTreeView';
export { SpanDetailPanel } from './SpanDetailPanel';

// Phase 5 - Filtering, search, and statistics
export { SpanFilters, defaultFilterState, hasActiveFilters, countActiveFilters } from './SpanFilters';
export type { SpanFilterState } from './SpanFilters';
export { SpanSearch, useSpanSearch, searchSpanTree, findExpandedForMatches, highlightMatches } from './SpanSearch';
export { SpanStats } from './SpanStats';
export { useSpanFilters, useLocalSpanFilters } from './useSpanFilters';
export { TraceExplorer } from './TraceExplorer';

// Phase 7 - Polish and performance
export { TraceErrorBoundary } from './TraceErrorBoundary';
export { SpanTreeSkeleton, SpanDetailSkeleton, SpanStatsSkeleton } from './SpanSkeletons';
