/**
 * SpanDetailPanel - Detailed view of a selected span.
 *
 * Shows comprehensive information about a span including:
 * - Basic info (type, name, status, timing)
 * - Input/Output data with JSON formatting
 * - LLM-specific info (model, tokens, cost)
 * - Error details with stack trace
 * - Metadata
 *
 * Implements Phase 4 of ENHANCED_TRACING_SPEC.md.
 */
import { useMemo } from 'react';
import { Span, SpanStatus } from '@/api/types';
import { SpanTypeBadge, getSpanTypeConfig } from './SpanTypeIcon';
import { cn } from '@/lib/utils';
import {
  X,
  Clock,
  Calendar,
  Coins,
  Hash,
  AlertCircle,
  CheckCircle,
  Loader2,
  MessageSquare,
  Wrench,
  Copy,
  ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';

interface SpanDetailPanelProps {
  span: Span | null;
  onClose?: () => void;
  className?: string;
}

/**
 * Format a date string to locale time.
 */
function formatTime(dateStr: string): string {
  const date = new Date(dateStr);
  const time = date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
  const ms = date.getMilliseconds().toString().padStart(3, '0');
  return `${time}.${ms}`;
}

/**
 * Format duration in human-readable form.
 */
function formatDuration(ms: number | null): string {
  if (ms === null || ms === undefined) return '-';
  if (ms < 1) return '<1ms';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
  return `${(ms / 60000).toFixed(2)}m`;
}

/**
 * Format JSON data for display with truncation.
 */
function formatJson(data: unknown, maxLength = 5000): string {
  try {
    const json = JSON.stringify(data, null, 2);
    if (json.length > maxLength) {
      return json.slice(0, maxLength) + '\n...(truncated)';
    }
    return json;
  } catch {
    return String(data);
  }
}

/**
 * Copy text to clipboard.
 */
async function copyToClipboard(text: string): Promise<void> {
  await navigator.clipboard.writeText(text);
}

/**
 * Status badge component.
 */
function StatusBadge({ status }: { status: SpanStatus }) {
  const config = {
    running: {
      icon: Loader2,
      label: 'Running',
      variant: 'outline' as const,
      className: 'border-blue-500 text-blue-600 dark:text-blue-400',
      iconClass: 'animate-spin',
    },
    success: {
      icon: CheckCircle,
      label: 'Success',
      variant: 'outline' as const,
      className: 'border-green-500 text-green-600 dark:text-green-400',
      iconClass: '',
    },
    error: {
      icon: AlertCircle,
      label: 'Error',
      variant: 'outline' as const,
      className: 'border-red-500 text-red-600 dark:text-red-400',
      iconClass: '',
    },
  }[status];

  const Icon = config.icon;

  return (
    <Badge variant={config.variant} className={cn('gap-1', config.className)}>
      <Icon className={cn('h-3 w-3', config.iconClass)} />
      {config.label}
    </Badge>
  );
}

/**
 * Info row component for displaying key-value pairs.
 */
function InfoRow({
  label,
  value,
  icon: Icon,
  className,
}: {
  label: string;
  value: React.ReactNode;
  icon?: React.ComponentType<{ className?: string }>;
  className?: string;
}) {
  return (
    <div className={cn('flex items-start gap-2 py-1.5', className)}>
      {Icon && <Icon className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />}
      <span className="text-sm text-muted-foreground w-24 flex-shrink-0">{label}</span>
      <span className="text-sm flex-1">{value}</span>
    </div>
  );
}

/**
 * JSON viewer with copy button.
 */
function JsonViewer({ data, title }: { data: unknown; title: string }) {
  const formatted = useMemo(() => formatJson(data), [data]);

  if (!data || (typeof data === 'object' && Object.keys(data as object).length === 0)) {
    return (
      <div className="text-sm text-muted-foreground italic p-4">No {title.toLowerCase()} data</div>
    );
  }

  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="icon"
        className="absolute right-2 top-2 h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity"
        onClick={() => copyToClipboard(formatted)}
        title="Copy to clipboard"
      >
        <Copy className="h-4 w-4" />
      </Button>
      <pre className="text-xs p-4 bg-muted/50 rounded-md overflow-x-auto font-mono whitespace-pre-wrap break-words thin-scrollbar">
        {formatted}
      </pre>
    </div>
  );
}

export function SpanDetailPanel({ span, onClose, className }: SpanDetailPanelProps) {
  if (!span) {
    return (
      <div
        className={cn(
          'flex flex-col items-center justify-center h-full text-muted-foreground',
          className
        )}
      >
        <ChevronRight className="h-8 w-8 mb-2 opacity-50" />
        <p className="text-sm">Select a span to view details</p>
      </div>
    );
  }

  const typeConfig = getSpanTypeConfig(span.span_type);

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="flex items-start justify-between gap-2 p-3 border-b">
        <div className="flex items-start gap-2 min-w-0">
          <SpanTypeBadge type={span.span_type} size="md" />
          <div className="min-w-0">
            <h3 className="text-sm font-medium truncate">
              {span.tool_name || span.name}
            </h3>
            <p className="text-xs text-muted-foreground">{typeConfig.label}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <StatusBadge status={span.status} />
          {onClose && (
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Content tabs */}
      <Tabs defaultValue="info" className="flex-1 flex flex-col overflow-hidden">
        <TabsList className="w-full justify-start rounded-none border-b px-2 h-9">
          <TabsTrigger value="info" className="text-xs">Info</TabsTrigger>
          <TabsTrigger value="input" className="text-xs">Input</TabsTrigger>
          <TabsTrigger value="output" className="text-xs">Output</TabsTrigger>
          {span.error_message && (
            <TabsTrigger value="error" className="text-xs text-red-600 dark:text-red-400">
              Error
            </TabsTrigger>
          )}
          <TabsTrigger value="meta" className="text-xs">Meta</TabsTrigger>
        </TabsList>

        <ScrollArea className="flex-1">
          {/* Info tab */}
          <TabsContent value="info" className="m-0 p-3 space-y-4">
            {/* Timing section */}
            <div className="space-y-1">
              <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Timing
              </h4>
              <div className="bg-muted/30 rounded-md p-2">
                <InfoRow
                  label="Started"
                  value={formatTime(span.started_at)}
                  icon={Calendar}
                />
                {span.ended_at && (
                  <InfoRow label="Ended" value={formatTime(span.ended_at)} icon={Calendar} />
                )}
                <InfoRow
                  label="Duration"
                  value={formatDuration(span.duration_ms)}
                  icon={Clock}
                />
              </div>
            </div>

            {/* LLM section (if applicable) */}
            {(span.model_name || span.tokens_total) && (
              <div className="space-y-1">
                <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  LLM Details
                </h4>
                <div className="bg-muted/30 rounded-md p-2">
                  {span.model_name && (
                    <InfoRow
                      label="Model"
                      value={
                        <span className="font-mono text-xs">
                          {span.model_provider && `${span.model_provider}/`}
                          {span.model_name}
                        </span>
                      }
                      icon={MessageSquare}
                    />
                  )}
                  {span.tokens_input !== null && (
                    <InfoRow
                      label="Input Tokens"
                      value={span.tokens_input?.toLocaleString()}
                      icon={Hash}
                    />
                  )}
                  {span.tokens_output !== null && (
                    <InfoRow
                      label="Output Tokens"
                      value={span.tokens_output?.toLocaleString()}
                      icon={Hash}
                    />
                  )}
                  {span.tokens_total !== null && (
                    <InfoRow
                      label="Total Tokens"
                      value={span.tokens_total?.toLocaleString()}
                      icon={Hash}
                    />
                  )}
                  {span.cost_usd !== null && Number(span.cost_usd) > 0 && (
                    <InfoRow
                      label="Cost"
                      value={`$${Number(span.cost_usd).toFixed(6)}`}
                      icon={Coins}
                    />
                  )}
                </div>
              </div>
            )}

            {/* Tool section (if applicable) */}
            {span.tool_name && (
              <div className="space-y-1">
                <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Tool
                </h4>
                <div className="bg-muted/30 rounded-md p-2">
                  <InfoRow
                    label="Tool Name"
                    value={<span className="font-mono text-xs">{span.tool_name}</span>}
                    icon={Wrench}
                  />
                </div>
              </div>
            )}

            {/* Tags */}
            {span.tags && span.tags.length > 0 && (
              <div className="space-y-1">
                <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Tags
                </h4>
                <div className="flex flex-wrap gap-1">
                  {span.tags.map((tag) => (
                    <Badge key={tag} variant="secondary" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* IDs */}
            <div className="space-y-1">
              <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Identifiers
              </h4>
              <div className="bg-muted/30 rounded-md p-2 space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Span ID</span>
                  <span className="font-mono">{span.id}</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Trace ID</span>
                  <span className="font-mono truncate max-w-[180px]" title={span.trace_id}>
                    {span.trace_id}
                  </span>
                </div>
                {span.parent_span_id && (
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Parent ID</span>
                    <span className="font-mono">{span.parent_span_id}</span>
                  </div>
                )}
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Depth</span>
                  <span className="font-mono">{span.depth}</span>
                </div>
              </div>
            </div>
          </TabsContent>

          {/* Input tab */}
          <TabsContent value="input" className="m-0 group">
            <JsonViewer data={span.input} title="Input" />
          </TabsContent>

          {/* Output tab */}
          <TabsContent value="output" className="m-0 group">
            <JsonViewer data={span.output} title="Output" />
          </TabsContent>

          {/* Error tab */}
          {span.error_message && (
            <TabsContent value="error" className="m-0 p-3 space-y-4">
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
                  <AlertCircle className="h-4 w-4" />
                  <span className="font-medium text-sm">{span.error_type || 'Error'}</span>
                </div>
                <p className="text-sm bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 p-3 rounded-md">
                  {span.error_message}
                </p>
              </div>

              {span.error_stack && (
                <div className="space-y-1">
                  <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Stack Trace
                  </h4>
                  <pre className="text-xs p-3 bg-muted/50 rounded-md overflow-x-auto font-mono whitespace-pre-wrap break-words text-red-700 dark:text-red-300 thin-scrollbar">
                    {span.error_stack}
                  </pre>
                </div>
              )}
            </TabsContent>
          )}

          {/* Metadata tab */}
          <TabsContent value="meta" className="m-0">
            <div className="p-3 space-y-4">
              {span.model_parameters && Object.keys(span.model_parameters).length > 0 && (
                <div className="space-y-1">
                  <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Model Parameters
                  </h4>
                  <div className="group">
                    <JsonViewer data={span.model_parameters} title="Model Parameters" />
                  </div>
                </div>
              )}
              <div className="space-y-1">
                <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Custom Metadata
                </h4>
                <div className="group">
                  <JsonViewer data={span.meta} title="Metadata" />
                </div>
              </div>
            </div>
          </TabsContent>
        </ScrollArea>
      </Tabs>
    </div>
  );
}

export default SpanDetailPanel;
