/**
 * TraceErrorBoundary - Error boundary for trace visualization components.
 *
 * Catches errors in the span tree and detail panel, providing:
 * - Graceful error display
 * - Retry functionality
 * - Error details for debugging
 *
 * Implements Phase 7 of ENHANCED_TRACING_SPEC.md.
 */
import { Component, ReactNode } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface TraceErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onRetry?: () => void;
  className?: string;
}

interface TraceErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

export class TraceErrorBoundary extends Component<
  TraceErrorBoundaryProps,
  TraceErrorBoundaryState
> {
  constructor(props: TraceErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<TraceErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({ errorInfo });
    // Log error for debugging (could be sent to monitoring service)
    console.error('TraceErrorBoundary caught an error:', error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    this.props.onRetry?.();
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div
          className={cn(
            'flex flex-col items-center justify-center p-6 text-center',
            this.props.className
          )}
          role="alert"
          aria-live="assertive"
        >
          <div className="rounded-full bg-red-100 dark:bg-red-900/30 p-3 mb-4">
            <AlertCircle className="h-8 w-8 text-red-600 dark:text-red-400" aria-hidden="true" />
          </div>

          <h3 className="text-lg font-semibold mb-2">
            Failed to load trace data
          </h3>

          <p className="text-sm text-muted-foreground mb-4 max-w-md">
            An error occurred while rendering the trace visualization.
            {this.state.error?.message && (
              <span className="block mt-1 font-mono text-xs text-red-600 dark:text-red-400">
                {this.state.error.message}
              </span>
            )}
          </p>

          <Button onClick={this.handleRetry} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" aria-hidden="true" />
            Try Again
          </Button>

          {/* Show stack trace in development */}
          {import.meta.env.DEV && this.state.errorInfo && (
            <details className="mt-4 text-left w-full max-w-lg">
              <summary className="text-xs text-muted-foreground cursor-pointer">
                Show error details
              </summary>
              <pre className="mt-2 p-2 bg-muted rounded text-xs overflow-auto max-h-48 thin-scrollbar">
                {this.state.error?.stack}
                {'\n\nComponent Stack:\n'}
                {this.state.errorInfo.componentStack}
              </pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

export default TraceErrorBoundary;
