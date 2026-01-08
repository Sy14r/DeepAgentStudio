/**
 * SpanSkeletons - Skeleton loading states for trace components.
 *
 * Provides visual feedback during data loading with:
 * - SpanTreeSkeleton: Animated tree structure placeholder
 * - SpanDetailSkeleton: Animated detail panel placeholder
 *
 * Implements Phase 7 of ENHANCED_TRACING_SPEC.md.
 */
import { cn } from '@/lib/utils';

interface SkeletonProps {
  className?: string;
}

/**
 * Base skeleton element with pulse animation.
 */
function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-md bg-muted',
        className
      )}
      aria-hidden="true"
    />
  );
}

/**
 * Single tree node skeleton.
 */
function SpanNodeSkeleton({ depth = 0 }: { depth?: number }) {
  return (
    <div
      className="flex items-center gap-2 py-1.5 px-2"
      style={{ paddingLeft: `${depth * 20 + 8}px` }}
    >
      {/* Expand button placeholder */}
      <Skeleton className="h-4 w-4 rounded" />
      {/* Type badge placeholder */}
      <Skeleton className="h-5 w-12 rounded" />
      {/* Status dot placeholder */}
      <Skeleton className="h-2 w-2 rounded-full" />
      {/* Name placeholder */}
      <Skeleton className="h-4 flex-1 max-w-[150px]" />
      {/* Duration placeholder */}
      <Skeleton className="h-4 w-12" />
    </div>
  );
}

/**
 * Skeleton for the span tree view.
 */
export function SpanTreeSkeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn('flex flex-col h-full', className)}
      role="status"
      aria-label="Loading trace data"
    >
      {/* Header skeleton */}
      <div className="flex items-center justify-between gap-2 p-2 border-b bg-muted/30">
        <div className="flex items-center gap-2">
          <Skeleton className="h-4 w-28" />
        </div>
        <div className="flex items-center gap-1">
          <Skeleton className="h-7 w-7 rounded" />
          <Skeleton className="h-7 w-7 rounded" />
          <Skeleton className="h-7 w-7 rounded" />
        </div>
      </div>

      {/* Stats skeleton */}
      <div className="flex items-center gap-4 px-3 py-2 border-b bg-muted/20">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-12" />
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-14" />
      </div>

      {/* Tree nodes skeleton */}
      <div className="flex-1 overflow-auto p-2">
        {/* Root node */}
        <SpanNodeSkeleton depth={0} />
        {/* Child nodes */}
        <div className="border-l border-border/50 ml-4">
          <SpanNodeSkeleton depth={1} />
          <SpanNodeSkeleton depth={1} />
          <div className="border-l border-border/50 ml-4">
            <SpanNodeSkeleton depth={2} />
            <SpanNodeSkeleton depth={2} />
          </div>
          <SpanNodeSkeleton depth={1} />
          <div className="border-l border-border/50 ml-4">
            <SpanNodeSkeleton depth={2} />
          </div>
          <SpanNodeSkeleton depth={1} />
        </div>
      </div>

      <span className="sr-only">Loading trace data...</span>
    </div>
  );
}

/**
 * Skeleton for the span detail panel.
 */
export function SpanDetailSkeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn('flex flex-col h-full', className)}
      role="status"
      aria-label="Loading span details"
    >
      {/* Header skeleton */}
      <div className="p-4 border-b">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Skeleton className="h-8 w-8 rounded" />
            <Skeleton className="h-6 w-32" />
          </div>
          <Skeleton className="h-8 w-8 rounded" />
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-4 w-24" />
        </div>
      </div>

      {/* Stats skeleton */}
      <div className="grid grid-cols-3 gap-2 p-4 border-b bg-muted/20">
        <div className="text-center">
          <Skeleton className="h-3 w-12 mx-auto mb-1" />
          <Skeleton className="h-5 w-16 mx-auto" />
        </div>
        <div className="text-center">
          <Skeleton className="h-3 w-12 mx-auto mb-1" />
          <Skeleton className="h-5 w-16 mx-auto" />
        </div>
        <div className="text-center">
          <Skeleton className="h-3 w-12 mx-auto mb-1" />
          <Skeleton className="h-5 w-16 mx-auto" />
        </div>
      </div>

      {/* Tabs skeleton */}
      <div className="flex gap-2 p-2 border-b">
        <Skeleton className="h-8 w-16 rounded" />
        <Skeleton className="h-8 w-16 rounded" />
        <Skeleton className="h-8 w-16 rounded" />
        <Skeleton className="h-8 w-16 rounded" />
      </div>

      {/* Content skeleton */}
      <div className="flex-1 p-4 space-y-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-32 w-full rounded-lg" />
        <Skeleton className="h-4 w-2/3" />
        <Skeleton className="h-4 w-4/5" />
      </div>

      <span className="sr-only">Loading span details...</span>
    </div>
  );
}

/**
 * Skeleton for the stats panel.
 */
export function SpanStatsSkeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn('grid grid-cols-2 md:grid-cols-4 gap-4 p-4', className)}
      role="status"
      aria-label="Loading statistics"
    >
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="space-y-2">
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-8 w-16" />
          <Skeleton className="h-2 w-full rounded-full" />
        </div>
      ))}
      <span className="sr-only">Loading statistics...</span>
    </div>
  );
}

export default SpanTreeSkeleton;
