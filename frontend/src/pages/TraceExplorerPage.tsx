/**
 * TraceExplorerPage - Full-page trace exploration experience.
 *
 * Provides a dedicated page for deep trace analysis with:
 * - Resizable split view (tree + detail panel)
 * - Session header with metadata
 * - Export functionality (JSON/CSV)
 * - Keyboard navigation
 * - Deep linking to specific spans
 *
 * Implements Phase 6 of ENHANCED_TRACING_SPEC.md.
 * Updated in Phase 7 with error boundaries, skeletons, and retry support.
 */
import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useSession } from '@/api/hooks';
import { useSpanTree, useSpan, useRefreshSpanData } from '@/api/hooks/useSpans';
import { SpanTreeNode as SpanTreeNodeType, Span } from '@/api/types';
import {
  SpanTreeView,
  SpanDetailPanel,
  SpanFilters,
  SpanSearch,
  SpanStats,
  SpanFilterState,
  defaultFilterState,
  hasActiveFilters,
  useSpanSearch,
  TraceErrorBoundary,
  SpanTreeSkeleton,
  SpanDetailSkeleton,
} from '@/components/traces';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  ArrowLeft,
  Download,
  FileJson,
  FileSpreadsheet,
  Copy,
  ExternalLink,
  RefreshCw,
  Clock,
  Zap,
  Coins,
  AlertCircle,
  CheckCircle,
  Loader2,
  PanelRightClose,
  PanelRight,
  BarChart3,
  ChevronRight,
} from 'lucide-react';

// URL param keys
const PARAM_SPAN_ID = 'span';

/**
 * Export spans as JSON.
 */
function exportAsJson(rootSpan: SpanTreeNodeType, sessionId: number) {
  const data = {
    session_id: sessionId,
    exported_at: new Date().toISOString(),
    root_span: rootSpan,
  };
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `trace-session-${sessionId}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

/**
 * Flatten span tree for CSV export.
 */
function flattenSpanTree(node: SpanTreeNodeType, rows: Record<string, unknown>[] = []): Record<string, unknown>[] {
  rows.push({
    id: node.id,
    span_type: node.span_type,
    name: node.name,
    status: node.status,
    started_at: node.started_at,
    ended_at: node.ended_at,
    duration_ms: node.duration_ms,
    depth: node.depth,
    tokens_total: node.tokens_total,
    cost_usd: node.cost_usd,
    tool_name: node.tool_name,
    error_message: node.error_message,
  });
  for (const child of node.children) {
    flattenSpanTree(child, rows);
  }
  return rows;
}

/**
 * Export spans as CSV.
 */
function exportAsCsv(rootSpan: SpanTreeNodeType, sessionId: number) {
  const rows = flattenSpanTree(rootSpan);
  if (rows.length === 0) return;

  const headers = Object.keys(rows[0]);
  const csvContent = [
    headers.join(','),
    ...rows.map((row) =>
      headers
        .map((h) => {
          const val = row[h];
          if (val === null || val === undefined) return '';
          if (typeof val === 'string' && (val.includes(',') || val.includes('"'))) {
            return `"${val.replace(/"/g, '""')}"`;
          }
          return String(val);
        })
        .join(',')
    ),
  ].join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `trace-session-${sessionId}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

/**
 * Copy span to clipboard as JSON.
 */
async function copySpanToClipboard(span: Span): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(JSON.stringify(span, null, 2));
    return true;
  } catch {
    return false;
  }
}

/**
 * Filter a span tree based on filter state.
 */
function filterSpanTree(
  node: SpanTreeNodeType,
  filters: SpanFilterState
): SpanTreeNodeType | null {
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

  const filteredChildren: SpanTreeNodeType[] = [];
  for (const child of node.children) {
    const filteredChild = filterSpanTree(child, filters);
    if (filteredChild) {
      filteredChildren.push(filteredChild);
    }
  }

  const nodeMatches =
    matchesType && matchesStatus && matchesMinDuration && matchesMaxDuration && matchesError;

  if (nodeMatches || filteredChildren.length > 0) {
    return { ...node, children: filteredChildren };
  }

  return null;
}

/**
 * Get status badge for session.
 */
function SessionStatusBadge({ status }: { status: string }) {
  const config = {
    completed: { icon: CheckCircle, label: 'Completed', variant: 'default' as const, className: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' },
    running: { icon: Loader2, label: 'Running', variant: 'default' as const, className: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' },
    failed: { icon: AlertCircle, label: 'Failed', variant: 'destructive' as const, className: '' },
    pending: { icon: Clock, label: 'Pending', variant: 'secondary' as const, className: '' },
  }[status] || { icon: Clock, label: status, variant: 'secondary' as const, className: '' };

  const Icon = config.icon;

  return (
    <Badge variant={config.variant} className={cn('gap-1', config.className)}>
      <Icon className={cn('h-3 w-3', status === 'running' && 'animate-spin')} />
      {config.label}
    </Badge>
  );
}

export function TraceExplorerPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const sessionId = id ? parseInt(id, 10) : undefined;

  // State
  const [showDetailPanel, setShowDetailPanel] = useState(true);
  const [panelWidth, setPanelWidth] = useState(380);
  const [isResizing, setIsResizing] = useState(false);
  const [showStats, setShowStats] = useState(false);
  const [filters, setFilters] = useState<SpanFilterState>(defaultFilterState);
  const containerRef = useRef<HTMLDivElement>(null);

  // Get selected span ID from URL
  const selectedSpanIdFromUrl = searchParams.get(PARAM_SPAN_ID);
  const [selectedSpanId, setSelectedSpanId] = useState<number | null>(
    selectedSpanIdFromUrl ? parseInt(selectedSpanIdFromUrl, 10) : null
  );

  // Fetch data
  const { data: session, isLoading: isLoadingSession } = useSession(sessionId);
  const { data: spanTree, isLoading: isLoadingSpans, error: spanTreeError, refetch: refetchSpans } = useSpanTree(sessionId);
  const { data: selectedSpan, isLoading: isLoadingSpanDetail } = useSpan(sessionId, selectedSpanId ?? undefined, { enabled: !!selectedSpanId });

  // Retry hooks for error recovery
  const { refreshTree } = useRefreshSpanData();

  // Search state
  const {
    searchQuery,
    setSearchQuery,
    matchCount,
    currentMatchIndex,
    currentMatchId,
    goToNextMatch,
    goToPrevMatch,
  } = useSpanSearch(spanTree?.root_span || null);

  // Apply filters to tree
  const filteredTree = useMemo(() => {
    if (!spanTree?.root_span) return null;
    if (!hasActiveFilters({ ...filters, search: '' })) return spanTree.root_span;
    return filterSpanTree(spanTree.root_span, { ...filters, search: '' });
  }, [spanTree?.root_span, filters]);

  // Collect available types
  const availableTypes = useMemo(() => {
    const types = new Set<string>();
    function collect(node: SpanTreeNodeType) {
      types.add(node.span_type);
      node.children.forEach(collect);
    }
    if (spanTree?.root_span) collect(spanTree.root_span);
    return types;
  }, [spanTree?.root_span]);

  // Update URL when span is selected
  useEffect(() => {
    if (selectedSpanId !== null) {
      searchParams.set(PARAM_SPAN_ID, selectedSpanId.toString());
    } else {
      searchParams.delete(PARAM_SPAN_ID);
    }
    setSearchParams(searchParams, { replace: true });
  }, [selectedSpanId, searchParams, setSearchParams]);

  // Navigate to match when searching
  useEffect(() => {
    if (currentMatchId !== null) {
      setSelectedSpanId(currentMatchId);
    }
  }, [currentMatchId]);

  // Handle span selection
  const handleSelectSpan = useCallback((spanId: number) => {
    setSelectedSpanId(spanId);
  }, []);

  // Panel resize handlers
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  }, []);

  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;
      const containerRect = containerRef.current.getBoundingClientRect();
      const newWidth = containerRect.right - e.clientX;
      setPanelWidth(Math.max(280, Math.min(600, newWidth)));
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl+F to focus search
      if ((e.metaKey || e.ctrlKey) && e.key === 'f') {
        e.preventDefault();
        const searchInput = document.querySelector<HTMLInputElement>('[data-search-input]');
        searchInput?.focus();
      }

      // Escape to deselect
      if (e.key === 'Escape') {
        setSelectedSpanId(null);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Format duration
  const formatDuration = (ms: number | null) => {
    if (ms === null) return '-';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  // Loading state
  if (isLoadingSession && !session) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Not found
  if (!session && !isLoadingSession) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <AlertCircle className="h-12 w-12 text-muted-foreground" />
        <p className="text-muted-foreground">Session not found</p>
        <Button variant="outline" onClick={() => navigate('/sessions')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Sessions
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full" ref={containerRef}>
      {/* Header */}
      <div className="flex-shrink-0 border-b">
        {/* Breadcrumb */}
        <div className="px-4 py-2 border-b bg-muted/30">
          <nav className="flex items-center text-sm text-muted-foreground">
            <Link to="/sessions" className="hover:text-foreground transition-colors">
              Sessions
            </Link>
            <ChevronRight className="h-4 w-4 mx-1" />
            <Link
              to={`/sessions/${sessionId}`}
              className="hover:text-foreground transition-colors"
            >
              {session?.title || `Session #${sessionId}`}
            </Link>
            <ChevronRight className="h-4 w-4 mx-1" />
            <span className="text-foreground font-medium">Trace Explorer</span>
          </nav>
        </div>

        {/* Session info bar */}
        <div className="px-4 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" onClick={() => navigate('/sessions')}>
              <ArrowLeft className="h-4 w-4 mr-1" />
              Back
            </Button>

            <div className="h-6 w-px bg-border" />

            <div>
              <h1 className="text-lg font-semibold">
                {session?.title || `Session #${sessionId}`}
              </h1>
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                {session && <SessionStatusBadge status={session.status} />}
                {session?.started_at && (
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {new Date(session.started_at).toLocaleString()}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Quick stats */}
            {spanTree?.stats && (
              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                <span className="flex items-center gap-1">
                  <Zap className="h-4 w-4" />
                  {spanTree.stats.total_spans} spans
                </span>
                <span className="flex items-center gap-1">
                  <Clock className="h-4 w-4" />
                  {formatDuration(spanTree.stats.total_duration_ms)}
                </span>
                <span>{spanTree.stats.total_tokens.toLocaleString()} tokens</span>
                {Number(spanTree.stats.total_cost_usd) > 0 && (
                  <span className="flex items-center gap-1">
                    <Coins className="h-4 w-4" />
                    ${Number(spanTree.stats.total_cost_usd).toFixed(4)}
                  </span>
                )}
                {spanTree.stats.error_count > 0 && (
                  <span className="flex items-center gap-1 text-red-600">
                    <AlertCircle className="h-4 w-4" />
                    {spanTree.stats.error_count} errors
                  </span>
                )}
              </div>
            )}

            <div className="h-6 w-px bg-border" />

            {/* Actions */}
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setShowStats(!showStats)}
              title={showStats ? 'Hide statistics' : 'Show statistics'}
            >
              <BarChart3 className="h-4 w-4" />
            </Button>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm">
                  <Download className="h-4 w-4 mr-1" />
                  Export
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  onClick={() => spanTree?.root_span && exportAsJson(spanTree.root_span, sessionId!)}
                  disabled={!spanTree?.root_span}
                >
                  <FileJson className="h-4 w-4 mr-2" />
                  Export as JSON
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => spanTree?.root_span && exportAsCsv(spanTree.root_span, sessionId!)}
                  disabled={!spanTree?.root_span}
                >
                  <FileSpreadsheet className="h-4 w-4 mr-2" />
                  Export as CSV
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={async () => {
                    if (selectedSpan) {
                      await copySpanToClipboard(selectedSpan);
                    }
                  }}
                  disabled={!selectedSpan}
                >
                  <Copy className="h-4 w-4 mr-2" />
                  Copy selected span
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => refetchSpans()}
              disabled={isLoadingSpans}
            >
              <RefreshCw className={cn('h-4 w-4', isLoadingSpans && 'animate-spin')} />
            </Button>

            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setShowDetailPanel(!showDetailPanel)}
            >
              {showDetailPanel ? (
                <PanelRightClose className="h-4 w-4" />
              ) : (
                <PanelRight className="h-4 w-4" />
              )}
            </Button>

            {session?.agent_id && (
              <Button variant="outline" size="sm" asChild>
                <Link to={`/playground/${session.agent_id}/session/${sessionId}`}>
                  <ExternalLink className="h-4 w-4 mr-1" />
                  Open in Playground
                </Link>
              </Button>
            )}
          </div>
        </div>

        {/* Stats panel (collapsible) */}
        {showStats && spanTree?.stats && (
          <div className="px-4 py-3 border-t bg-muted/20">
            <SpanStats stats={spanTree.stats} layout="horizontal" />
          </div>
        )}

        {/* Filters and search bar */}
        <div className="px-4 py-2 border-t flex items-center gap-4">
          <SpanFilters
            filters={filters}
            onFiltersChange={setFilters}
            availableTypes={availableTypes as Set<any>}
            compact
          />

          <div className="flex-1" />

          <SpanSearch
            value={searchQuery}
            onChange={setSearchQuery}
            matchCount={matchCount}
            currentMatch={currentMatchIndex + 1}
            onNextMatch={goToNextMatch}
            onPrevMatch={goToPrevMatch}
            className="w-72"
          />
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Tree view with error boundary */}
        <div className="flex-1 min-w-0 overflow-hidden border-r">
          <TraceErrorBoundary
            onRetry={() => sessionId && refreshTree(sessionId)}
            className="h-full"
          >
            {isLoadingSpans && !spanTree ? (
              <SpanTreeSkeleton className="h-full" />
            ) : spanTreeError ? (
              <div className="flex flex-col items-center justify-center h-full p-6 text-center">
                <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
                <h3 className="text-lg font-semibold mb-2">Failed to load trace</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  {spanTreeError instanceof Error ? spanTreeError.message : 'An error occurred'}
                </p>
                <Button onClick={() => refetchSpans()} variant="outline" size="sm">
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Retry
                </Button>
              </div>
            ) : (
              <SpanTreeView
                rootSpan={filteredTree}
                stats={spanTree?.stats}
                selectedSpanId={selectedSpanId}
                onSelectSpan={handleSelectSpan}
                isLoading={isLoadingSpans}
                isRecording={session?.status === 'running'}
                onRefresh={() => refetchSpans()}
                className="h-full"
              />
            )}
          </TraceErrorBoundary>
        </div>

        {/* Resize handle */}
        {showDetailPanel && (
          <div
            className={cn(
              'w-1 cursor-col-resize hover:bg-primary/20 transition-colors flex-shrink-0',
              isResizing && 'bg-primary/30'
            )}
            onMouseDown={handleMouseDown}
          />
        )}

        {/* Detail panel with error boundary */}
        {showDetailPanel && (
          <div
            className="flex-shrink-0 overflow-hidden"
            style={{ width: panelWidth }}
          >
            <TraceErrorBoundary className="h-full">
              {isLoadingSpanDetail && selectedSpanId ? (
                <SpanDetailSkeleton className="h-full" />
              ) : (
                <SpanDetailPanel
                  span={selectedSpan || null}
                  onClose={() => setSelectedSpanId(null)}
                />
              )}
            </TraceErrorBoundary>
          </div>
        )}
      </div>
    </div>
  );
}

export default TraceExplorerPage;
