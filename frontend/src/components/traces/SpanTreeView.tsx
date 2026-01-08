/**
 * SpanTreeView - Hierarchical visualization of execution spans.
 *
 * Displays a collapsible tree of spans with filtering, statistics,
 * and selection support. Integrates with the span store for real-time updates.
 *
 * Implements Phase 4 of ENHANCED_TRACING_SPEC.md.
 * Updated in Phase 7 with accessibility improvements.
 */
import { useMemo, useState, useCallback } from 'react';
import { SpanTreeNode as SpanTreeNodeType, SpanStats, SpanType } from '@/api/types';
import { SpanTreeNode } from './SpanTreeNode';
import { SpanTypeIcon, getSpanTypeConfig } from './SpanTypeIcon';
import { cn } from '@/lib/utils';
import {
  ChevronDown,
  ChevronUp,
  Filter,
  Clock,
  Coins,
  Hash,
  AlertCircle,
  RefreshCw,
  Expand,
  Minimize2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from '@/components/ui/dropdown-menu';

interface SpanTreeViewProps {
  rootSpan: SpanTreeNodeType | null;
  stats?: SpanStats;
  selectedSpanId?: number | null;
  onSelectSpan?: (spanId: number) => void;
  isLoading?: boolean;
  isRecording?: boolean;
  onRefresh?: () => void;
  className?: string;
}

/**
 * Calculate max duration recursively for timeline scaling.
 */
function getMaxDuration(node: SpanTreeNodeType): number {
  let max = node.duration_ms || 0;
  for (const child of node.children) {
    max = Math.max(max, getMaxDuration(child));
  }
  return max;
}

/**
 * Collect all span types present in the tree.
 */
function collectSpanTypes(node: SpanTreeNodeType, types: Set<SpanType>): void {
  types.add(node.span_type);
  for (const child of node.children) {
    collectSpanTypes(child, types);
  }
}

/**
 * Filter tree by span types.
 */
function filterTree(
  node: SpanTreeNodeType,
  allowedTypes: Set<SpanType>
): SpanTreeNodeType | null {
  // If this node's type is not allowed and has no children to check, skip it
  const filteredChildren: SpanTreeNodeType[] = [];

  for (const child of node.children) {
    const filteredChild = filterTree(child, allowedTypes);
    if (filteredChild) {
      filteredChildren.push(filteredChild);
    }
  }

  // Include node if its type is allowed OR it has matching children
  if (allowedTypes.has(node.span_type) || filteredChildren.length > 0) {
    return {
      ...node,
      children: filteredChildren,
    };
  }

  return null;
}

export function SpanTreeView({
  rootSpan,
  stats,
  selectedSpanId,
  onSelectSpan,
  isLoading = false,
  isRecording = false,
  onRefresh,
  className,
}: SpanTreeViewProps) {
  const [expandAll, setExpandAll] = useState(true);
  const [filterTypes, setFilterTypes] = useState<Set<SpanType>>(new Set());
  const [showStats, setShowStats] = useState(true);

  // Collect available span types
  const availableTypes = useMemo(() => {
    const types = new Set<SpanType>();
    if (rootSpan) {
      collectSpanTypes(rootSpan, types);
    }
    return types;
  }, [rootSpan]);

  // Calculate max duration for timeline bars
  const maxDuration = useMemo(() => {
    if (!rootSpan) return 0;
    return getMaxDuration(rootSpan);
  }, [rootSpan]);

  // Apply type filter
  const filteredTree = useMemo(() => {
    if (!rootSpan) return null;
    if (filterTypes.size === 0) return rootSpan;
    return filterTree(rootSpan, filterTypes);
  }, [rootSpan, filterTypes]);

  const toggleTypeFilter = useCallback((type: SpanType) => {
    setFilterTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  }, []);

  const clearFilters = useCallback(() => {
    setFilterTypes(new Set());
  }, []);

  // Format stats for display
  const formattedStats = useMemo(() => {
    if (!stats) return null;
    return {
      totalSpans: stats.total_spans,
      duration: stats.total_duration_ms
        ? stats.total_duration_ms < 1000
          ? `${stats.total_duration_ms}ms`
          : `${(stats.total_duration_ms / 1000).toFixed(1)}s`
        : '-',
      tokens: stats.total_tokens.toLocaleString(),
      cost: Number(stats.total_cost_usd) > 0 ? `$${Number(stats.total_cost_usd).toFixed(4)}` : '-',
      errors: stats.error_count,
    };
  }, [stats]);

  if (!rootSpan && !isLoading) {
    return (
      <div className={cn('flex flex-col items-center justify-center p-8 text-muted-foreground', className)}>
        <Hash className="h-12 w-12 mb-4 opacity-50" />
        <p className="text-sm">No spans recorded yet</p>
        {isRecording && (
          <p className="text-xs mt-2 flex items-center gap-1">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
            </span>
            Recording in progress...
          </p>
        )}
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Header with controls */}
      <div className="flex items-center justify-between gap-2 p-2 border-b bg-muted/30">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-medium">Execution Trace</h3>
          {isRecording && (
            <span className="flex items-center gap-1 text-xs text-red-600 dark:text-red-400">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
              </span>
              Recording
            </span>
          )}
          {isLoading && !isRecording && (
            <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground" />
          )}
        </div>

        <div className="flex items-center gap-1">
          {/* Refresh button */}
          {onRefresh && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={onRefresh}
              disabled={isLoading}
            >
              <RefreshCw className={cn('h-4 w-4', isLoading && 'animate-spin')} />
            </Button>
          )}

          {/* Expand/Collapse all */}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => setExpandAll((prev) => !prev)}
            title={expandAll ? 'Collapse all' : 'Expand all'}
          >
            {expandAll ? (
              <Minimize2 className="h-4 w-4" />
            ) : (
              <Expand className="h-4 w-4" />
            )}
          </Button>

          {/* Type filter */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className={cn('h-7 w-7', filterTypes.size > 0 && 'text-primary')}
              >
                <Filter className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuLabel>Filter by Type</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {Array.from(availableTypes).map((type) => {
                const config = getSpanTypeConfig(type);
                return (
                  <DropdownMenuCheckboxItem
                    key={type}
                    checked={filterTypes.has(type)}
                    onCheckedChange={() => toggleTypeFilter(type)}
                  >
                    <span className="flex items-center gap-2">
                      <SpanTypeIcon type={type} size="sm" />
                      {config.label}
                    </span>
                  </DropdownMenuCheckboxItem>
                );
              })}
              {filterTypes.size > 0 && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuCheckboxItem
                    checked={false}
                    onCheckedChange={clearFilters}
                  >
                    Clear filters
                  </DropdownMenuCheckboxItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Toggle stats */}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => setShowStats((prev) => !prev)}
            title={showStats ? 'Hide stats' : 'Show stats'}
          >
            {showStats ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>

      {/* Stats summary */}
      {showStats && formattedStats && (
        <div className="flex items-center gap-4 px-3 py-2 border-b bg-muted/20 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <Hash className="h-3 w-3" />
            {formattedStats.totalSpans} spans
          </span>
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {formattedStats.duration}
          </span>
          <span>{formattedStats.tokens} tokens</span>
          {formattedStats.cost !== '-' && (
            <span className="flex items-center gap-1">
              <Coins className="h-3 w-3" />
              {formattedStats.cost}
            </span>
          )}
          {formattedStats.errors > 0 && (
            <span className="flex items-center gap-1 text-red-600 dark:text-red-400">
              <AlertCircle className="h-3 w-3" />
              {formattedStats.errors} errors
            </span>
          )}
        </div>
      )}

      {/* Tree content */}
      <div
        className="flex-1 overflow-auto p-2 custom-scrollbar"
        role="tree"
        aria-label="Execution trace tree"
        aria-busy={isLoading}
      >
        {isLoading && !filteredTree ? (
          <div className="flex items-center justify-center h-32" role="status" aria-label="Loading trace">
            <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" aria-hidden="true" />
            <span className="sr-only">Loading trace data...</span>
          </div>
        ) : filteredTree ? (
          <SpanTreeNode
            node={filteredTree}
            selectedSpanId={selectedSpanId}
            onSelectSpan={onSelectSpan}
            defaultExpanded={expandAll}
            showDurationBars={true}
            maxDuration={maxDuration}
          />
        ) : (
          <div className="flex items-center justify-center h-32 text-muted-foreground" role="status">
            <p className="text-sm">No spans match the current filter</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default SpanTreeView;
