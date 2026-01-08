/**
 * Live Span Recording Indicator.
 *
 * Shows real-time span recording status during agent execution.
 * Displays span count, running count, and error count with animations.
 *
 * Implements Phase 3 of ENHANCED_TRACING_SPEC.md.
 */
import { useRecordingStatus } from '@/stores/spanStore';
import { cn } from '@/lib/utils';

interface LiveSpanIndicatorProps {
  className?: string;
  showDetails?: boolean;
}

export function LiveSpanIndicator({ className, showDetails = true }: LiveSpanIndicatorProps) {
  const { isRecording, spanCount, runningCount, errorCount } = useRecordingStatus();

  if (!isRecording && spanCount === 0) {
    return null;
  }

  return (
    <div
      className={cn(
        'flex items-center gap-2 text-sm',
        className
      )}
    >
      {/* Recording indicator with pulse animation */}
      {isRecording && (
        <div className="flex items-center gap-1.5">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500" />
          </span>
          <span className="text-red-600 dark:text-red-400 font-medium">
            Recording
          </span>
        </div>
      )}

      {/* Span counts */}
      {showDetails && spanCount > 0 && (
        <div className="flex items-center gap-3 text-muted-foreground">
          {/* Total spans */}
          <span className="flex items-center gap-1">
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
            <span>{spanCount} spans</span>
          </span>

          {/* Running spans */}
          {runningCount > 0 && (
            <span className="flex items-center gap-1 text-blue-600 dark:text-blue-400">
              <svg
                className="h-4 w-4 animate-spin"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              <span>{runningCount} running</span>
            </span>
          )}

          {/* Error spans */}
          {errorCount > 0 && (
            <span className="flex items-center gap-1 text-red-600 dark:text-red-400">
              <svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <span>{errorCount} errors</span>
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export default LiveSpanIndicator;
