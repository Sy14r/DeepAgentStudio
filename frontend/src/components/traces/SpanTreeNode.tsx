/**
 * SpanTreeNode - Individual node in the span tree hierarchy.
 *
 * Renders a collapsible tree node with type icon, name, status, and duration.
 * Supports recursive children rendering and selection.
 *
 * Implements Phase 4 of ENHANCED_TRACING_SPEC.md.
 * Updated in Phase 7 with memoization and accessibility improvements.
 */
import { useState, useCallback, memo } from 'react';
import { SpanTreeNode as SpanTreeNodeType, SpanStatus } from '@/api/types';
import { SpanTypeBadge } from './SpanTypeIcon';
import { cn } from '@/lib/utils';
import { ChevronRight, ChevronDown, Clock, Coins, AlertTriangle } from 'lucide-react';

interface SpanTreeNodeProps {
  node: SpanTreeNodeType;
  depth?: number;
  selectedSpanId?: number | null;
  onSelectSpan?: (spanId: number) => void;
  defaultExpanded?: boolean;
  showDurationBars?: boolean;
  maxDuration?: number;
}

/**
 * Format milliseconds to human-readable duration.
 */
function formatDuration(ms: number | null): string {
  if (ms === null || ms === undefined) return '-';
  if (ms < 1) return '<1ms';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

/**
 * Format cost to display string.
 */
function formatCost(cost: number | null): string {
  if (cost === null || cost === undefined || cost === 0) return '';
  if (cost < 0.01) return '<$0.01';
  return `$${cost.toFixed(4)}`;
}

/**
 * Get status indicator styling.
 */
function getStatusStyles(status: SpanStatus): { dot: string; text: string } {
  switch (status) {
    case 'running':
      return {
        dot: 'bg-blue-500 animate-pulse',
        text: 'text-blue-600 dark:text-blue-400',
      };
    case 'success':
      return {
        dot: 'bg-green-500',
        text: 'text-green-600 dark:text-green-400',
      };
    case 'error':
      return {
        dot: 'bg-red-500',
        text: 'text-red-600 dark:text-red-400',
      };
    default:
      return {
        dot: 'bg-gray-400',
        text: 'text-gray-600 dark:text-gray-400',
      };
  }
}

/**
 * Memoized SpanTreeNode component for optimal rendering performance.
 * Uses React.memo to prevent unnecessary re-renders when parent props haven't changed.
 */
export const SpanTreeNode = memo(function SpanTreeNode({
  node,
  depth = 0,
  selectedSpanId,
  onSelectSpan,
  defaultExpanded = true,
  showDurationBars = true,
  maxDuration = 0,
}: SpanTreeNodeProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const hasChildren = node.children && node.children.length > 0;
  const isSelected = selectedSpanId === node.id;
  const statusStyles = getStatusStyles(node.status);

  // Calculate duration bar width
  const durationPercent =
    showDurationBars && maxDuration > 0 && node.duration_ms
      ? Math.min((node.duration_ms / maxDuration) * 100, 100)
      : 0;

  const handleToggle = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setIsExpanded((prev) => !prev);
  }, []);

  const handleSelect = useCallback(() => {
    onSelectSpan?.(node.id);
  }, [node.id, onSelectSpan]);

  // Unique ID for accessibility
  const nodeId = `span-node-${node.id}`;
  const childrenId = `span-children-${node.id}`;

  return (
    <div
      className="select-none"
      role="treeitem"
      aria-expanded={hasChildren ? isExpanded : undefined}
      aria-selected={isSelected}
      aria-level={depth + 1}
      aria-labelledby={nodeId}
      id={nodeId}
    >
      {/* Node row */}
      <div
        className={cn(
          'group flex items-center gap-2 py-1.5 px-2 rounded-md cursor-pointer transition-colors',
          'hover:bg-muted/50',
          isSelected && 'bg-primary/10 hover:bg-primary/15 ring-1 ring-primary/20',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'
        )}
        style={{ paddingLeft: `${depth * 20 + 8}px` }}
        onClick={handleSelect}
        role="button"
        tabIndex={0}
        aria-label={`${node.span_type} ${node.tool_name || node.name}, ${node.status}${node.duration_ms ? `, ${formatDuration(node.duration_ms)}` : ''}`}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleSelect();
          }
          if (e.key === 'ArrowRight' && hasChildren && !isExpanded) {
            e.preventDefault();
            setIsExpanded(true);
          }
          if (e.key === 'ArrowLeft' && hasChildren && isExpanded) {
            e.preventDefault();
            setIsExpanded(false);
          }
        }}
      >
        {/* Expand/collapse button */}
        <button
          type="button"
          className={cn(
            'flex-shrink-0 p-0.5 rounded hover:bg-muted transition-colors',
            !hasChildren && 'invisible'
          )}
          onClick={handleToggle}
          aria-label={isExpanded ? 'Collapse' : 'Expand'}
          aria-controls={hasChildren ? childrenId : undefined}
          tabIndex={-1}
        >
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          )}
        </button>

        {/* Type icon */}
        <SpanTypeBadge type={node.span_type} size="sm" />

        {/* Status dot */}
        <span
          className={cn('w-2 h-2 rounded-full flex-shrink-0', statusStyles.dot)}
          title={node.status}
          role="img"
          aria-label={`Status: ${node.status}`}
        />

        {/* Name */}
        <span className="flex-1 truncate text-sm font-medium">
          {node.tool_name || node.name}
        </span>

        {/* Error indicator */}
        {node.error_message && (
          <span title={node.error_message} role="img" aria-label="Error occurred">
            <AlertTriangle className="h-4 w-4 text-red-500 flex-shrink-0" aria-hidden="true" />
          </span>
        )}

        {/* Duration */}
        {node.duration_ms !== null && (
          <span
            className="flex items-center gap-1 text-xs text-muted-foreground flex-shrink-0"
            aria-label={`Duration: ${formatDuration(node.duration_ms)}`}
          >
            <Clock className="h-3 w-3" aria-hidden="true" />
            {formatDuration(node.duration_ms)}
          </span>
        )}

        {/* Tokens */}
        {node.tokens_total !== null && node.tokens_total > 0 && (
          <span
            className="text-xs text-muted-foreground flex-shrink-0"
            aria-label={`${node.tokens_total.toLocaleString()} tokens`}
          >
            {node.tokens_total.toLocaleString()} tok
          </span>
        )}

        {/* Cost */}
        {formatCost(node.cost_usd) && (
          <span
            className="flex items-center gap-0.5 text-xs text-muted-foreground flex-shrink-0"
            aria-label={`Cost: ${formatCost(node.cost_usd)}`}
          >
            <Coins className="h-3 w-3" aria-hidden="true" />
            {formatCost(node.cost_usd)}
          </span>
        )}
      </div>

      {/* Duration bar (timeline visualization) */}
      {showDurationBars && durationPercent > 0 && (
        <div
          className="h-0.5 bg-primary/30 rounded-full ml-10 mr-2 mb-1"
          style={{ width: `${durationPercent}%` }}
          role="progressbar"
          aria-valuenow={node.duration_ms ?? 0}
          aria-valuemax={maxDuration}
          aria-label="Duration relative to total"
        />
      )}

      {/* Children */}
      {hasChildren && isExpanded && (
        <div
          className="border-l border-border/50 ml-4"
          role="group"
          id={childrenId}
          aria-label={`Children of ${node.tool_name || node.name}`}
        >
          {node.children.map((child) => (
            <SpanTreeNode
              key={child.id}
              node={child}
              depth={depth + 1}
              selectedSpanId={selectedSpanId}
              onSelectSpan={onSelectSpan}
              defaultExpanded={defaultExpanded}
              showDurationBars={showDurationBars}
              maxDuration={maxDuration}
            />
          ))}
        </div>
      )}
    </div>
  );
});

export default SpanTreeNode;
