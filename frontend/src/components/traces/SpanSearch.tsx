/**
 * SpanSearch - Text search component for span tree.
 *
 * Provides debounced search across span names, inputs, and outputs
 * with match highlighting support.
 *
 * Implements Phase 5 of ENHANCED_TRACING_SPEC.md.
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { SpanTreeNode as SpanTreeNodeType } from '@/api/types';
import { cn } from '@/lib/utils';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Search, X, ChevronUp, ChevronDown, Loader2 } from 'lucide-react';

interface SpanSearchProps {
  value: string;
  onChange: (value: string) => void;
  onSearch?: (value: string) => void;
  matchCount?: number;
  currentMatch?: number;
  onNextMatch?: () => void;
  onPrevMatch?: () => void;
  isSearching?: boolean;
  placeholder?: string;
  className?: string;
}

/**
 * Debounce hook for search input.
 */
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}

export function SpanSearch({
  value,
  onChange,
  onSearch,
  matchCount = 0,
  currentMatch = 0,
  onNextMatch,
  onPrevMatch,
  isSearching = false,
  placeholder = 'Search spans...',
  className,
}: SpanSearchProps) {
  const debouncedValue = useDebounce(value, 300);

  // Trigger search on debounced value change
  useEffect(() => {
    onSearch?.(debouncedValue);
  }, [debouncedValue, onSearch]);

  const handleClear = useCallback(() => {
    onChange('');
  }, [onChange]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        if (e.shiftKey) {
          onPrevMatch?.();
        } else {
          onNextMatch?.();
        }
      }
      if (e.key === 'Escape') {
        handleClear();
      }
    },
    [onNextMatch, onPrevMatch, handleClear]
  );

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className="relative flex-1">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          type="text"
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          className="pl-9 pr-20 h-9"
        />
        {/* Right side controls inside input */}
        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
          {isSearching && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
          {value && !isSearching && matchCount > 0 && (
            <Badge variant="secondary" className="text-xs h-5 px-1.5">
              {currentMatch}/{matchCount}
            </Badge>
          )}
          {value && !isSearching && matchCount === 0 && (
            <span className="text-xs text-muted-foreground">No matches</span>
          )}
          {value && (
            <Button
              variant="ghost"
              size="icon"
              className="h-5 w-5"
              onClick={handleClear}
            >
              <X className="h-3 w-3" />
            </Button>
          )}
        </div>
      </div>

      {/* Match navigation */}
      {matchCount > 1 && (
        <div className="flex items-center gap-0.5">
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={onPrevMatch}
            title="Previous match (Shift+Enter)"
          >
            <ChevronUp className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={onNextMatch}
            title="Next match (Enter)"
          >
            <ChevronDown className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  );
}

/**
 * Search through a span tree and find matching spans.
 * Returns IDs of matching spans.
 */
export function searchSpanTree(
  node: SpanTreeNodeType,
  query: string,
  searchFields: ('name' | 'toolName')[] = ['name', 'toolName']
): number[] {
  if (!query.trim()) return [];

  const matches: number[] = [];
  const lowerQuery = query.toLowerCase();

  function searchNode(n: SpanTreeNodeType) {
    let isMatch = false;

    // Check name
    if (searchFields.includes('name') && n.name.toLowerCase().includes(lowerQuery)) {
      isMatch = true;
    }

    // Check tool name
    if (
      searchFields.includes('toolName') &&
      n.tool_name &&
      n.tool_name.toLowerCase().includes(lowerQuery)
    ) {
      isMatch = true;
    }

    if (isMatch) {
      matches.push(n.id);
    }

    // Recurse into children
    for (const child of n.children) {
      searchNode(child);
    }
  }

  searchNode(node);
  return matches;
}

/**
 * Find spans that should be expanded to show search matches.
 * Returns set of span IDs that are ancestors of matches.
 */
export function findExpandedForMatches(
  node: SpanTreeNodeType,
  matchIds: Set<number>
): Set<number> {
  const expanded = new Set<number>();

  function findPath(n: SpanTreeNodeType): boolean {
    // Check if this node or any descendant is a match
    let hasMatchInSubtree = matchIds.has(n.id);

    for (const child of n.children) {
      if (findPath(child)) {
        hasMatchInSubtree = true;
      }
    }

    // If there's a match in subtree, this node should be expanded
    if (hasMatchInSubtree && n.children.length > 0) {
      expanded.add(n.id);
    }

    return hasMatchInSubtree;
  }

  findPath(node);
  return expanded;
}

/**
 * Highlight matches in text.
 */
export function highlightMatches(
  text: string,
  query: string,
  className = 'bg-yellow-200 dark:bg-yellow-800 rounded px-0.5'
): React.ReactNode {
  if (!query.trim()) return text;

  const lowerText = text.toLowerCase();
  const lowerQuery = query.toLowerCase();
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;

  let index = lowerText.indexOf(lowerQuery);
  while (index !== -1) {
    // Add text before match
    if (index > lastIndex) {
      parts.push(text.slice(lastIndex, index));
    }

    // Add highlighted match
    parts.push(
      <mark key={index} className={className}>
        {text.slice(index, index + query.length)}
      </mark>
    );

    lastIndex = index + query.length;
    index = lowerText.indexOf(lowerQuery, lastIndex);
  }

  // Add remaining text
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length > 0 ? <>{parts}</> : text;
}

/**
 * Custom hook for managing search state and results.
 */
export function useSpanSearch(rootSpan: SpanTreeNodeType | null) {
  const [searchQuery, setSearchQuery] = useState('');
  const [currentMatchIndex, setCurrentMatchIndex] = useState(0);

  // Find all matches
  const matches = useMemo(() => {
    if (!rootSpan || !searchQuery.trim()) return [];
    return searchSpanTree(rootSpan, searchQuery);
  }, [rootSpan, searchQuery]);

  // Get expanded nodes for matches
  const expandedForSearch = useMemo(() => {
    if (!rootSpan || matches.length === 0) return new Set<number>();
    return findExpandedForMatches(rootSpan, new Set(matches));
  }, [rootSpan, matches]);

  // Current match ID
  const currentMatchId = matches[currentMatchIndex] ?? null;

  // Navigation functions
  const goToNextMatch = useCallback(() => {
    if (matches.length === 0) return;
    setCurrentMatchIndex((prev) => (prev + 1) % matches.length);
  }, [matches.length]);

  const goToPrevMatch = useCallback(() => {
    if (matches.length === 0) return;
    setCurrentMatchIndex((prev) => (prev - 1 + matches.length) % matches.length);
  }, [matches.length]);

  // Reset current match when query changes
  useEffect(() => {
    setCurrentMatchIndex(0);
  }, [searchQuery]);

  return {
    searchQuery,
    setSearchQuery,
    matches,
    matchCount: matches.length,
    currentMatchIndex,
    currentMatchId,
    expandedForSearch,
    goToNextMatch,
    goToPrevMatch,
  };
}

export default SpanSearch;
