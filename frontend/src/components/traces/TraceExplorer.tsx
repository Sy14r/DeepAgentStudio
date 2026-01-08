/**
 * TraceExplorer - Full-featured trace exploration component.
 *
 * Integrates all Phase 5 features:
 * - SpanTreeView for hierarchical visualization
 * - SpanFilters for type/status/duration filtering
 * - SpanSearch for text search with match navigation
 * - SpanStats for statistics visualization
 * - SpanDetailPanel for selected span details
 *
 * Implements Phase 5 of ENHANCED_TRACING_SPEC.md.
 */
import { useState, useCallback, useMemo, useEffect } from 'react';
import { SpanTreeNode as SpanTreeNodeType, SpanStats as SpanStatsType, Span } from '@/api/types';
import { SpanTreeView } from './SpanTreeView';
import { SpanDetailPanel } from './SpanDetailPanel';
import { SpanFilters, SpanFilterState, defaultFilterState, hasActiveFilters } from './SpanFilters';
import { SpanSearch, useSpanSearch } from './SpanSearch';
import { SpanStats } from './SpanStats';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  GitBranch,
  BarChart3,
  PanelRightClose,
  PanelRight,
  Share2,
  RefreshCw,
} from 'lucide-react';

interface TraceExplorerProps {
  rootSpan: SpanTreeNodeType | null;
  stats?: SpanStatsType;
  selectedSpan?: Span | null;
  isLoading?: boolean;
  isRecording?: boolean;
  onRefresh?: () => void;
  onSelectSpan?: (spanId: number) => void;
  onFetchSpan?: (spanId: number) => void;
  className?: string;
  showStats?: boolean;
  showFilters?: boolean;
  showSearch?: boolean;
  showDetailPanel?: boolean;
  persistFilters?: boolean;
}

/**
 * Filter a span tree based on filter state.
 */
function filterSpanTree(
  node: SpanTreeNodeType,
  filters: SpanFilterState
): SpanTreeNodeType | null {
  // Check if node matches filters
  const matchesType =
    filters.spanTypes.size === 0 || filters.spanTypes.has(node.span_type);
  const matchesStatus =
    filters.status === 'all' || node.status === filters.status;
  const matchesMinDuration =
    filters.minDurationMs === null ||
    (node.duration_ms !== null && node.duration_ms >= filters.minDurationMs);
  const matchesMaxDuration =
    filters.maxDurationMs === null ||
    (node.duration_ms !== null && node.duration_ms <= filters.maxDurationMs);
  const matchesError =
    filters.hasError === null ||
    (filters.hasError && node.error_message !== null);

  // Filter children recursively
  const filteredChildren: SpanTreeNodeType[] = [];
  for (const child of node.children) {
    const filteredChild = filterSpanTree(child, filters);
    if (filteredChild) {
      filteredChildren.push(filteredChild);
    }
  }

  // Include node if it matches OR has matching children
  const nodeMatches =
    matchesType && matchesStatus && matchesMinDuration && matchesMaxDuration && matchesError;

  if (nodeMatches || filteredChildren.length > 0) {
    return {
      ...node,
      children: filteredChildren,
    };
  }

  return null;
}

export function TraceExplorer({
  rootSpan,
  stats,
  selectedSpan,
  isLoading = false,
  isRecording = false,
  onRefresh,
  onSelectSpan,
  onFetchSpan,
  className,
  showStats = true,
  showFilters = true,
  showSearch = true,
  showDetailPanel = true,
  persistFilters = false,
}: TraceExplorerProps) {
  const [activeTab, setActiveTab] = useState<'tree' | 'stats'>('tree');
  const [showPanel, setShowPanel] = useState(true);
  const [filters, setFilters] = useState<SpanFilterState>(defaultFilterState);
  const [selectedSpanId, setSelectedSpanId] = useState<number | null>(null);

  // Search state
  const {
    searchQuery,
    setSearchQuery,
    matchCount,
    currentMatchIndex,
    currentMatchId,
    goToNextMatch,
    goToPrevMatch,
  } = useSpanSearch(rootSpan);

  // Update filters for search
  useEffect(() => {
    if (searchQuery) {
      setFilters((prev) => ({ ...prev, search: searchQuery }));
    } else {
      setFilters((prev) => ({ ...prev, search: '' }));
    }
  }, [searchQuery]);

  // Apply filters to span tree
  const filteredTree = useMemo(() => {
    if (!rootSpan) return null;

    // If only search is active, show full tree with highlights
    if (!hasActiveFilters({ ...filters, search: '' }) && searchQuery) {
      return rootSpan;
    }

    // Apply other filters
    const withFilters = hasActiveFilters({ ...filters, search: '' })
      ? filterSpanTree(rootSpan, { ...filters, search: '' })
      : rootSpan;

    return withFilters;
  }, [rootSpan, filters, searchQuery]);

  // Handle span selection
  const handleSelectSpan = useCallback(
    (spanId: number) => {
      setSelectedSpanId(spanId);
      onSelectSpan?.(spanId);
      onFetchSpan?.(spanId);
    },
    [onSelectSpan, onFetchSpan]
  );

  // Navigate to match and select it
  useEffect(() => {
    if (currentMatchId !== null) {
      handleSelectSpan(currentMatchId);
    }
  }, [currentMatchId, handleSelectSpan]);

  // Share URL with filters
  const handleShare = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      // Could add toast notification here if toast hook is available
    } catch {
      // Silent fail - could log error
    }
  }, []);

  // Collect available span types from tree
  const availableTypes = useMemo(() => {
    const types = new Set<string>();
    function collectTypes(node: SpanTreeNodeType) {
      types.add(node.span_type);
      for (const child of node.children) {
        collectTypes(child);
      }
    }
    if (rootSpan) collectTypes(rootSpan);
    return types;
  }, [rootSpan]);

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Top toolbar */}
      <div className="flex items-center gap-2 p-2 border-b bg-muted/30">
        {/* Tabs */}
        <div className="flex items-center gap-1">
          <Button
            variant={activeTab === 'tree' ? 'secondary' : 'ghost'}
            size="sm"
            className="gap-1"
            onClick={() => setActiveTab('tree')}
          >
            <GitBranch className="h-4 w-4" />
            Tree
          </Button>
          {showStats && stats && (
            <Button
              variant={activeTab === 'stats' ? 'secondary' : 'ghost'}
              size="sm"
              className="gap-1"
              onClick={() => setActiveTab('stats')}
            >
              <BarChart3 className="h-4 w-4" />
              Stats
            </Button>
          )}
        </div>

        <div className="flex-1" />

        {/* Search */}
        {showSearch && activeTab === 'tree' && (
          <SpanSearch
            value={searchQuery}
            onChange={setSearchQuery}
            matchCount={matchCount}
            currentMatch={currentMatchIndex + 1}
            onNextMatch={goToNextMatch}
            onPrevMatch={goToPrevMatch}
            className="w-64"
          />
        )}

        {/* Actions */}
        <div className="flex items-center gap-1">
          {persistFilters && hasActiveFilters(filters) && (
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleShare}>
              <Share2 className="h-4 w-4" />
            </Button>
          )}
          {onRefresh && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={onRefresh}
              disabled={isLoading}
            >
              <RefreshCw className={cn('h-4 w-4', isLoading && 'animate-spin')} />
            </Button>
          )}
          {showDetailPanel && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setShowPanel(!showPanel)}
            >
              {showPanel ? (
                <PanelRightClose className="h-4 w-4" />
              ) : (
                <PanelRight className="h-4 w-4" />
              )}
            </Button>
          )}
        </div>
      </div>

      {/* Filters bar */}
      {showFilters && activeTab === 'tree' && (
        <div className="p-2 border-b">
          <SpanFilters
            filters={filters}
            onFiltersChange={setFilters}
            availableTypes={availableTypes as Set<any>}
            compact
          />
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Tree or Stats view */}
        <div className="flex-1 min-w-0 overflow-hidden">
          {activeTab === 'tree' ? (
            <SpanTreeView
              rootSpan={filteredTree}
              stats={stats}
              selectedSpanId={selectedSpanId}
              onSelectSpan={handleSelectSpan}
              isLoading={isLoading}
              isRecording={isRecording}
              onRefresh={onRefresh}
              className="h-full"
            />
          ) : (
            stats && (
              <div className="h-full overflow-auto p-4 custom-scrollbar">
                <SpanStats stats={stats} layout="horizontal" />
              </div>
            )
          )}
        </div>

        {/* Detail panel */}
        {showDetailPanel && showPanel && activeTab === 'tree' && (
          <div className="w-80 border-l overflow-hidden flex-shrink-0">
            <SpanDetailPanel
              span={selectedSpan || null}
              onClose={() => {
                setSelectedSpanId(null);
                setShowPanel(false);
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default TraceExplorer;
