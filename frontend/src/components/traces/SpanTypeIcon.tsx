/**
 * Icon component for span types.
 *
 * Displays appropriate icon based on span type with consistent styling.
 * Implements Phase 4 of ENHANCED_TRACING_SPEC.md.
 */
import { SpanType } from '@/api/types';
import { cn } from '@/lib/utils';
import {
  Bot,
  Link2,
  MessageSquare,
  Wrench,
  Search,
  Hash,
  FileText,
  Sparkles,
  Database,
  Brain,
  AlertCircle,
  LucideIcon,
} from 'lucide-react';

interface SpanTypeIconProps {
  type: SpanType;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

interface SpanTypeConfig {
  icon: LucideIcon;
  label: string;
  color: string;
  bgColor: string;
}

const spanTypeConfigs: Record<SpanType, SpanTypeConfig> = {
  agent: {
    icon: Bot,
    label: 'Agent',
    color: 'text-purple-600 dark:text-purple-400',
    bgColor: 'bg-purple-100 dark:bg-purple-900/30',
  },
  chain: {
    icon: Link2,
    label: 'Chain',
    color: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-100 dark:bg-blue-900/30',
  },
  llm: {
    icon: MessageSquare,
    label: 'LLM',
    color: 'text-green-600 dark:text-green-400',
    bgColor: 'bg-green-100 dark:bg-green-900/30',
  },
  tool: {
    icon: Wrench,
    label: 'Tool',
    color: 'text-orange-600 dark:text-orange-400',
    bgColor: 'bg-orange-100 dark:bg-orange-900/30',
  },
  retriever: {
    icon: Search,
    label: 'Retriever',
    color: 'text-cyan-600 dark:text-cyan-400',
    bgColor: 'bg-cyan-100 dark:bg-cyan-900/30',
  },
  embedding: {
    icon: Hash,
    label: 'Embedding',
    color: 'text-indigo-600 dark:text-indigo-400',
    bgColor: 'bg-indigo-100 dark:bg-indigo-900/30',
  },
  parser: {
    icon: FileText,
    label: 'Parser',
    color: 'text-slate-600 dark:text-slate-400',
    bgColor: 'bg-slate-100 dark:bg-slate-900/30',
  },
  prompt: {
    icon: Sparkles,
    label: 'Prompt',
    color: 'text-pink-600 dark:text-pink-400',
    bgColor: 'bg-pink-100 dark:bg-pink-900/30',
  },
  memory: {
    icon: Database,
    label: 'Memory',
    color: 'text-teal-600 dark:text-teal-400',
    bgColor: 'bg-teal-100 dark:bg-teal-900/30',
  },
  thought: {
    icon: Brain,
    label: 'Thought',
    color: 'text-yellow-600 dark:text-yellow-400',
    bgColor: 'bg-yellow-100 dark:bg-yellow-900/30',
  },
  error: {
    icon: AlertCircle,
    label: 'Error',
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-100 dark:bg-red-900/30',
  },
};

const sizeClasses = {
  sm: 'h-3.5 w-3.5',
  md: 'h-4 w-4',
  lg: 'h-5 w-5',
};

export function SpanTypeIcon({ type, className, size = 'md' }: SpanTypeIconProps) {
  const config = spanTypeConfigs[type];
  const Icon = config.icon;

  return (
    <Icon
      className={cn(sizeClasses[size], config.color, className)}
      aria-label={config.label}
    />
  );
}

/**
 * Badge version of the icon with background.
 */
export function SpanTypeBadge({ type, className, size = 'md' }: SpanTypeIconProps) {
  const config = spanTypeConfigs[type];
  const Icon = config.icon;

  const badgeSizes = {
    sm: 'p-1',
    md: 'p-1.5',
    lg: 'p-2',
  };

  return (
    <div
      className={cn(
        'inline-flex items-center justify-center rounded-md',
        config.bgColor,
        badgeSizes[size],
        className
      )}
    >
      <Icon className={cn(sizeClasses[size], config.color)} aria-label={config.label} />
    </div>
  );
}

/**
 * Get configuration for a span type (for custom usage).
 */
export function getSpanTypeConfig(type: SpanType): SpanTypeConfig {
  return spanTypeConfigs[type];
}

export default SpanTypeIcon;
