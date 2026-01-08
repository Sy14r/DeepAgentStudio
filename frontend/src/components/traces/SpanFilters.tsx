/**
 * SpanFilters - Advanced filtering controls for span tree.
 *
 * Provides multi-select type filter, status filter, duration range,
 * error toggle, and clear all functionality.
 *
 * Implements Phase 5 of ENHANCED_TRACING_SPEC.md.
 */
import { useCallback } from 'react';
import { SpanType, SpanStatus } from '@/api/types';
import { SpanTypeIcon, getSpanTypeConfig } from './SpanTypeIcon';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from '@/components/ui/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Filter,
  X,
  ChevronDown,
  Clock,
  AlertCircle,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';

// All available span types
const ALL_SPAN_TYPES: SpanType[] = [
  'agent',
  'chain',
  'llm',
  'tool',
  'retriever',
  'embedding',
  'parser',
  'prompt',
  'memory',
  'thought',
  'error',
];

export interface SpanFilterState {
  spanTypes: Set<SpanType>;
  status: SpanStatus | 'all';
  minDurationMs: number | null;
  maxDurationMs: number | null;
  hasError: boolean | null;
  search: string;
  toolName: string;
  modelName: string;
}

export const defaultFilterState: SpanFilterState = {
  spanTypes: new Set(),
  status: 'all',
  minDurationMs: null,
  maxDurationMs: null,
  hasError: null,
  search: '',
  toolName: '',
  modelName: '',
};

interface SpanFiltersProps {
  filters: SpanFilterState;
  onFiltersChange: (filters: SpanFilterState) => void;
  availableTypes?: Set<SpanType>;
  className?: string;
  compact?: boolean;
}

/**
 * Check if any filters are active.
 */
export function hasActiveFilters(filters: SpanFilterState): boolean {
  return (
    filters.spanTypes.size > 0 ||
    filters.status !== 'all' ||
    filters.minDurationMs !== null ||
    filters.maxDurationMs !== null ||
    filters.hasError !== null ||
    filters.search !== '' ||
    filters.toolName !== '' ||
    filters.modelName !== ''
  );
}

/**
 * Count number of active filters.
 */
export function countActiveFilters(filters: SpanFilterState): number {
  let count = 0;
  if (filters.spanTypes.size > 0) count++;
  if (filters.status !== 'all') count++;
  if (filters.minDurationMs !== null || filters.maxDurationMs !== null) count++;
  if (filters.hasError !== null) count++;
  if (filters.search) count++;
  if (filters.toolName) count++;
  if (filters.modelName) count++;
  return count;
}

export function SpanFilters({
  filters,
  onFiltersChange,
  availableTypes = new Set(ALL_SPAN_TYPES),
  className,
  compact = false,
}: SpanFiltersProps) {
  const activeCount = countActiveFilters(filters);

  const toggleType = useCallback(
    (type: SpanType) => {
      const newTypes = new Set(filters.spanTypes);
      if (newTypes.has(type)) {
        newTypes.delete(type);
      } else {
        newTypes.add(type);
      }
      onFiltersChange({ ...filters, spanTypes: newTypes });
    },
    [filters, onFiltersChange]
  );

  const setStatus = useCallback(
    (status: SpanStatus | 'all') => {
      onFiltersChange({ ...filters, status });
    },
    [filters, onFiltersChange]
  );

  const setMinDuration = useCallback(
    (value: string) => {
      const num = value === '' ? null : parseInt(value, 10);
      onFiltersChange({ ...filters, minDurationMs: isNaN(num!) ? null : num });
    },
    [filters, onFiltersChange]
  );

  const setMaxDuration = useCallback(
    (value: string) => {
      const num = value === '' ? null : parseInt(value, 10);
      onFiltersChange({ ...filters, maxDurationMs: isNaN(num!) ? null : num });
    },
    [filters, onFiltersChange]
  );

  const toggleHasError = useCallback(
    (checked: boolean) => {
      onFiltersChange({ ...filters, hasError: checked ? true : null });
    },
    [filters, onFiltersChange]
  );

  const clearFilters = useCallback(() => {
    onFiltersChange(defaultFilterState);
  }, [onFiltersChange]);

  if (compact) {
    return (
      <div className={cn('flex items-center gap-2', className)}>
        {/* Compact filter button with dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className={cn('gap-1', activeCount > 0 && 'border-primary')}
            >
              <Filter className="h-4 w-4" />
              Filters
              {activeCount > 0 && (
                <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-xs">
                  {activeCount}
                </Badge>
              )}
              <ChevronDown className="h-3 w-3 ml-1" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-72 p-3">
            <CompactFilterContent
              filters={filters}
              availableTypes={availableTypes}
              toggleType={toggleType}
              setStatus={setStatus}
              setMinDuration={setMinDuration}
              setMaxDuration={setMaxDuration}
              toggleHasError={toggleHasError}
            />
            {activeCount > 0 && (
              <>
                <DropdownMenuSeparator />
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start text-muted-foreground"
                  onClick={clearFilters}
                >
                  <X className="h-4 w-4 mr-2" />
                  Clear all filters
                </Button>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Active filter badges */}
        {activeCount > 0 && (
          <div className="flex items-center gap-1 flex-wrap">
            {filters.spanTypes.size > 0 && (
              <Badge variant="secondary" className="gap-1">
                Types: {filters.spanTypes.size}
                <button
                  onClick={() => onFiltersChange({ ...filters, spanTypes: new Set() })}
                  className="hover:text-destructive"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            )}
            {filters.status !== 'all' && (
              <Badge variant="secondary" className="gap-1">
                Status: {filters.status}
                <button
                  onClick={() => onFiltersChange({ ...filters, status: 'all' })}
                  className="hover:text-destructive"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            )}
            {(filters.minDurationMs !== null || filters.maxDurationMs !== null) && (
              <Badge variant="secondary" className="gap-1">
                Duration
                <button
                  onClick={() =>
                    onFiltersChange({ ...filters, minDurationMs: null, maxDurationMs: null })
                  }
                  className="hover:text-destructive"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            )}
            {filters.hasError && (
              <Badge variant="secondary" className="gap-1 text-red-600">
                Errors only
                <button
                  onClick={() => onFiltersChange({ ...filters, hasError: null })}
                  className="hover:text-destructive"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            )}
          </div>
        )}
      </div>
    );
  }

  // Full filter bar
  return (
    <div className={cn('flex items-center gap-3 flex-wrap', className)}>
      {/* Type multi-select */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="gap-1">
            <Filter className="h-4 w-4" />
            Types
            {filters.spanTypes.size > 0 && (
              <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-xs">
                {filters.spanTypes.size}
              </Badge>
            )}
            <ChevronDown className="h-3 w-3" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-48">
          <DropdownMenuLabel>Span Types</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {Array.from(availableTypes).map((type) => {
            const config = getSpanTypeConfig(type);
            return (
              <DropdownMenuCheckboxItem
                key={type}
                checked={filters.spanTypes.has(type)}
                onCheckedChange={() => toggleType(type)}
              >
                <span className="flex items-center gap-2">
                  <SpanTypeIcon type={type} size="sm" />
                  {config.label}
                </span>
              </DropdownMenuCheckboxItem>
            );
          })}
          {filters.spanTypes.size > 0 && (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuCheckboxItem
                checked={false}
                onCheckedChange={() => onFiltersChange({ ...filters, spanTypes: new Set() })}
              >
                Clear selection
              </DropdownMenuCheckboxItem>
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Status filter */}
      <Select value={filters.status} onValueChange={(v) => setStatus(v as SpanStatus | 'all')}>
        <SelectTrigger className="w-32 h-9">
          <SelectValue placeholder="Status" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Status</SelectItem>
          <SelectItem value="success">Success</SelectItem>
          <SelectItem value="error">Error</SelectItem>
          <SelectItem value="running">Running</SelectItem>
        </SelectContent>
      </Select>

      {/* Duration range */}
      <div className="flex items-center gap-1">
        <Clock className="h-4 w-4 text-muted-foreground" />
        <Input
          type="number"
          placeholder="Min ms"
          className="w-20 h-9"
          value={filters.minDurationMs ?? ''}
          onChange={(e) => setMinDuration(e.target.value)}
          min={0}
        />
        <span className="text-muted-foreground">-</span>
        <Input
          type="number"
          placeholder="Max ms"
          className="w-20 h-9"
          value={filters.maxDurationMs ?? ''}
          onChange={(e) => setMaxDuration(e.target.value)}
          min={0}
        />
      </div>

      {/* Error toggle */}
      <div className="flex items-center gap-2">
        <Switch
          id="has-error"
          checked={filters.hasError === true}
          onCheckedChange={toggleHasError}
        />
        <Label htmlFor="has-error" className="flex items-center gap-1 text-sm cursor-pointer">
          <AlertCircle className="h-4 w-4 text-red-500" />
          Errors only
        </Label>
      </div>

      {/* Clear all */}
      {activeCount > 0 && (
        <Button variant="ghost" size="sm" onClick={clearFilters} className="text-muted-foreground">
          <X className="h-4 w-4 mr-1" />
          Clear ({activeCount})
        </Button>
      )}
    </div>
  );
}

/**
 * Compact filter content for dropdown.
 */
function CompactFilterContent({
  filters,
  availableTypes,
  toggleType,
  setStatus,
  setMinDuration,
  setMaxDuration,
  toggleHasError,
}: {
  filters: SpanFilterState;
  availableTypes: Set<SpanType>;
  toggleType: (type: SpanType) => void;
  setStatus: (status: SpanStatus | 'all') => void;
  setMinDuration: (value: string) => void;
  setMaxDuration: (value: string) => void;
  toggleHasError: (checked: boolean) => void;
}) {
  return (
    <div className="space-y-4">
      {/* Types */}
      <div className="space-y-2">
        <Label className="text-xs font-medium text-muted-foreground">Span Types</Label>
        <div className="flex flex-wrap gap-1">
          {Array.from(availableTypes).map((type) => {
            const config = getSpanTypeConfig(type);
            const isSelected = filters.spanTypes.has(type);
            return (
              <button
                key={type}
                onClick={() => toggleType(type)}
                className={cn(
                  'flex items-center gap-1 px-2 py-1 rounded-md text-xs transition-colors',
                  isSelected
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted hover:bg-muted/80'
                )}
              >
                <SpanTypeIcon type={type} size="sm" className={isSelected ? 'text-primary-foreground' : ''} />
                {config.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Status */}
      <div className="space-y-2">
        <Label className="text-xs font-medium text-muted-foreground">Status</Label>
        <Select value={filters.status} onValueChange={(v) => setStatus(v as SpanStatus | 'all')}>
          <SelectTrigger className="w-full h-8 text-sm">
            <SelectValue placeholder="All" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="success">Success</SelectItem>
            <SelectItem value="error">Error</SelectItem>
            <SelectItem value="running">Running</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Duration */}
      <div className="space-y-2">
        <Label className="text-xs font-medium text-muted-foreground">Duration (ms)</Label>
        <div className="flex items-center gap-2">
          <Input
            type="number"
            placeholder="Min"
            className="h-8 text-sm"
            value={filters.minDurationMs ?? ''}
            onChange={(e) => setMinDuration(e.target.value)}
            min={0}
          />
          <span className="text-muted-foreground">-</span>
          <Input
            type="number"
            placeholder="Max"
            className="h-8 text-sm"
            value={filters.maxDurationMs ?? ''}
            onChange={(e) => setMaxDuration(e.target.value)}
            min={0}
          />
        </div>
      </div>

      {/* Errors only */}
      <div className="flex items-center justify-between">
        <Label htmlFor="errors-only" className="flex items-center gap-1 text-sm cursor-pointer">
          <AlertCircle className="h-4 w-4 text-red-500" />
          Errors only
        </Label>
        <Switch
          id="errors-only"
          checked={filters.hasError === true}
          onCheckedChange={toggleHasError}
        />
      </div>
    </div>
  );
}

export default SpanFilters;
