/**
 * SpanStats - Statistics visualization for span data.
 *
 * Displays aggregated statistics with CSS-based charts:
 * - Type breakdown (horizontal bar chart)
 * - Token usage (input/output breakdown)
 * - Cost summary
 * - Error count
 * - Timing stats
 *
 * Implements Phase 5 of ENHANCED_TRACING_SPEC.md.
 */
import { useMemo } from 'react';
import { SpanStats as SpanStatsType, SpanType } from '@/api/types';
import { SpanTypeIcon, getSpanTypeConfig } from './SpanTypeIcon';
import { cn } from '@/lib/utils';
import {
  Hash,
  Clock,
  Coins,
  AlertCircle,
  Zap,
} from 'lucide-react';

interface SpanStatsProps {
  stats: SpanStatsType;
  className?: string;
  layout?: 'horizontal' | 'vertical' | 'compact';
}

/**
 * Format duration for display.
 */
function formatDuration(ms: number | null): string {
  if (ms === null || ms === undefined) return '-';
  if (ms < 1) return '<1ms';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

/**
 * Format cost for display.
 * Handles both number and Decimal string inputs from API.
 */
function formatCost(cost: number | string): string {
  const numCost = Number(cost);
  if (numCost === 0 || isNaN(numCost)) return '$0';
  if (numCost < 0.0001) return '<$0.0001';
  if (numCost < 0.01) return `$${numCost.toFixed(4)}`;
  return `$${numCost.toFixed(2)}`;
}

/**
 * Simple horizontal bar chart component.
 */
function HorizontalBarChart({
  data,
  className,
}: {
  data: { label: string; value: number; color: string; icon?: React.ReactNode }[];
  className?: string;
}) {
  const maxValue = Math.max(...data.map((d) => d.value), 1);

  return (
    <div className={cn('space-y-2', className)}>
      {data.map((item) => (
        <div key={item.label} className="space-y-1">
          <div className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-1.5 text-muted-foreground">
              {item.icon}
              {item.label}
            </span>
            <span className="font-medium">{item.value}</span>
          </div>
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-300"
              style={{
                width: `${(item.value / maxValue) * 100}%`,
                backgroundColor: item.color,
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Token usage donut/ring chart.
 */
function TokenRingChart({
  input,
  output,
  className,
}: {
  input: number;
  output: number;
  className?: string;
}) {
  const total = input + output;
  if (total === 0) return null;

  const inputPercent = (input / total) * 100;

  // CSS conic gradient for donut chart
  const gradient = `conic-gradient(
    #3b82f6 0% ${inputPercent}%,
    #10b981 ${inputPercent}% 100%
  )`;

  return (
    <div className={cn('flex items-center gap-4', className)}>
      {/* Ring chart */}
      <div
        className="relative w-16 h-16 rounded-full"
        style={{ background: gradient }}
      >
        <div className="absolute inset-2 bg-background rounded-full flex items-center justify-center">
          <span className="text-xs font-medium">{total.toLocaleString()}</span>
        </div>
      </div>

      {/* Legend */}
      <div className="space-y-1 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-sm bg-blue-500" />
          <span className="text-muted-foreground">Input</span>
          <span className="font-medium">{input.toLocaleString()}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-sm bg-green-500" />
          <span className="text-muted-foreground">Output</span>
          <span className="font-medium">{output.toLocaleString()}</span>
        </div>
      </div>
    </div>
  );
}

/**
 * Stat card component.
 */
function StatCard({
  icon: Icon,
  label,
  value,
  subValue,
  className,
  variant = 'default',
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
  subValue?: string;
  className?: string;
  variant?: 'default' | 'success' | 'error' | 'warning';
}) {
  const variantStyles = {
    default: 'text-muted-foreground',
    success: 'text-green-600 dark:text-green-400',
    error: 'text-red-600 dark:text-red-400',
    warning: 'text-yellow-600 dark:text-yellow-400',
  };

  return (
    <div className={cn('p-3 rounded-lg bg-muted/30 border', className)}>
      <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
        <Icon className={cn('h-4 w-4', variantStyles[variant])} />
        {label}
      </div>
      <div className="text-lg font-semibold">{value}</div>
      {subValue && <div className="text-xs text-muted-foreground">{subValue}</div>}
    </div>
  );
}

export function SpanStats({ stats, className, layout = 'horizontal' }: SpanStatsProps) {
  // Prepare type breakdown data
  const typeBreakdown = useMemo(() => {
    const entries = Object.entries(stats.span_count_by_type);
    return entries
      .map(([type, count]) => {
        const config = getSpanTypeConfig(type as SpanType);
        return {
          label: config.label,
          value: count,
          color: config.color.replace('text-', '').replace(' dark:', ''),
          icon: <SpanTypeIcon type={type as SpanType} size="sm" />,
          // Extract hex color from tailwind class
          hexColor: getTypeColor(type as SpanType),
        };
      })
      .sort((a, b) => b.value - a.value);
  }, [stats.span_count_by_type]);

  if (layout === 'compact') {
    return (
      <div className={cn('flex items-center gap-4 text-sm', className)}>
        <span className="flex items-center gap-1">
          <Hash className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">{stats.total_spans}</span>
          <span className="text-muted-foreground">spans</span>
        </span>
        <span className="flex items-center gap-1">
          <Clock className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">{formatDuration(stats.total_duration_ms)}</span>
        </span>
        <span className="flex items-center gap-1">
          <Zap className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">{stats.total_tokens.toLocaleString()}</span>
          <span className="text-muted-foreground">tokens</span>
        </span>
        {Number(stats.total_cost_usd) > 0 && (
          <span className="flex items-center gap-1">
            <Coins className="h-4 w-4 text-muted-foreground" />
            <span className="font-medium">{formatCost(stats.total_cost_usd)}</span>
          </span>
        )}
        {stats.error_count > 0 && (
          <span className="flex items-center gap-1 text-red-600 dark:text-red-400">
            <AlertCircle className="h-4 w-4" />
            <span className="font-medium">{stats.error_count}</span>
            <span>errors</span>
          </span>
        )}
      </div>
    );
  }

  if (layout === 'vertical') {
    return (
      <div className={cn('space-y-6', className)}>
        {/* Summary stats */}
        <div className="grid grid-cols-2 gap-3">
          <StatCard icon={Hash} label="Total Spans" value={stats.total_spans} />
          <StatCard
            icon={Clock}
            label="Duration"
            value={formatDuration(stats.total_duration_ms)}
            subValue={
              stats.average_duration_ms
                ? `Avg: ${formatDuration(stats.average_duration_ms)}`
                : undefined
            }
          />
          <StatCard
            icon={Zap}
            label="Tokens"
            value={stats.total_tokens.toLocaleString()}
            subValue={`${stats.total_tokens_input.toLocaleString()} in / ${stats.total_tokens_output.toLocaleString()} out`}
          />
          <StatCard
            icon={Coins}
            label="Cost"
            value={formatCost(stats.total_cost_usd)}
            variant={Number(stats.total_cost_usd) > 1 ? 'warning' : 'default'}
          />
        </div>

        {/* Error count if any */}
        {stats.error_count > 0 && (
          <StatCard
            icon={AlertCircle}
            label="Errors"
            value={stats.error_count}
            variant="error"
          />
        )}

        {/* Type breakdown */}
        {typeBreakdown.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Breakdown by Type
            </h4>
            <HorizontalBarChart
              data={typeBreakdown.map((t) => ({
                label: t.label,
                value: t.value,
                color: t.hexColor,
                icon: t.icon,
              }))}
            />
          </div>
        )}

        {/* Token breakdown */}
        {stats.total_tokens > 0 && (
          <div className="space-y-3">
            <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Token Distribution
            </h4>
            <TokenRingChart
              input={stats.total_tokens_input}
              output={stats.total_tokens_output}
            />
          </div>
        )}
      </div>
    );
  }

  // Horizontal layout (default)
  return (
    <div className={cn('space-y-4', className)}>
      {/* Top stats row */}
      <div className="grid grid-cols-5 gap-4">
        <StatCard icon={Hash} label="Total Spans" value={stats.total_spans} />
        <StatCard
          icon={Clock}
          label="Duration"
          value={formatDuration(stats.total_duration_ms)}
          subValue={
            stats.average_duration_ms
              ? `Avg: ${formatDuration(stats.average_duration_ms)}`
              : undefined
          }
        />
        <StatCard
          icon={Zap}
          label="Tokens"
          value={stats.total_tokens.toLocaleString()}
          subValue={`${stats.total_tokens_input.toLocaleString()} in / ${stats.total_tokens_output.toLocaleString()} out`}
        />
        <StatCard
          icon={Coins}
          label="Cost"
          value={formatCost(stats.total_cost_usd)}
          variant={Number(stats.total_cost_usd) > 1 ? 'warning' : 'default'}
        />
        <StatCard
          icon={AlertCircle}
          label="Errors"
          value={stats.error_count}
          variant={stats.error_count > 0 ? 'error' : 'default'}
        />
      </div>

      {/* Type breakdown and token distribution */}
      <div className="grid grid-cols-2 gap-6">
        {typeBreakdown.length > 0 && (
          <div className="p-4 rounded-lg border bg-muted/10">
            <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-4">
              Breakdown by Type
            </h4>
            <HorizontalBarChart
              data={typeBreakdown.map((t) => ({
                label: t.label,
                value: t.value,
                color: t.hexColor,
                icon: t.icon,
              }))}
            />
          </div>
        )}

        {stats.total_tokens > 0 && (
          <div className="p-4 rounded-lg border bg-muted/10">
            <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-4">
              Token Distribution
            </h4>
            <TokenRingChart
              input={stats.total_tokens_input}
              output={stats.total_tokens_output}
            />
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Get hex color for span type (for charts).
 */
function getTypeColor(type: SpanType): string {
  const colors: Record<SpanType, string> = {
    agent: '#9333ea', // purple-600
    chain: '#2563eb', // blue-600
    llm: '#16a34a', // green-600
    tool: '#ea580c', // orange-600
    retriever: '#0891b2', // cyan-600
    embedding: '#4f46e5', // indigo-600
    parser: '#475569', // slate-600
    prompt: '#db2777', // pink-600
    memory: '#0d9488', // teal-600
    thought: '#ca8a04', // yellow-600
    error: '#dc2626', // red-600
  };
  return colors[type] || '#6b7280';
}

export default SpanStats;
