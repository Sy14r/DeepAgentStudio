/**
 * Span Store for Real-Time Tracing.
 *
 * Manages hierarchical span state during agent execution,
 * updated via WebSocket events for real-time UI updates.
 *
 * Implements Phase 3 of ENHANCED_TRACING_SPEC.md.
 */
import { create } from 'zustand';

// Span types matching backend SpanType enum
export type SpanType =
  | 'agent'
  | 'chain'
  | 'llm'
  | 'tool'
  | 'retriever'
  | 'embedding'
  | 'parser'
  | 'prompt'
  | 'memory'
  | 'thought'
  | 'error';

// Span status matching backend SpanStatus enum
export type SpanStatus = 'running' | 'success' | 'error';

// Span data structure for real-time updates
export interface LiveSpan {
  span_id: number;
  trace_id: string;
  parent_span_id: number | null;
  span_type: SpanType;
  name: string;
  depth: number;
  status: SpanStatus;
  started_at: string;
  ended_at?: string;
  duration_ms?: number;
  input?: Record<string, unknown>;
  output?: Record<string, unknown>;
  tokens_input?: number;
  tokens_output?: number;
  cost_usd?: number;
  error_message?: string;
  metadata?: Record<string, unknown>;
}

// Tree node for hierarchical display
export interface SpanTreeNode extends LiveSpan {
  children: SpanTreeNode[];
}

interface SpanState {
  // Current session being traced
  activeSessionId: number | null;

  // Active trace ID
  activeTraceId: string | null;

  // Map of span_id -> span data
  spans: Map<number, LiveSpan>;

  // Whether recording is in progress
  isRecording: boolean;

  // Total span count for this trace
  spanCount: number;

  // Running span count
  runningCount: number;

  // Error span count
  errorCount: number;

  // Actions
  startRecording: (sessionId: number) => void;
  stopRecording: () => void;
  addSpan: (span: LiveSpan) => void;
  updateSpan: (spanId: number, updates: Partial<LiveSpan>) => void;
  completeSpan: (
    spanId: number,
    status: SpanStatus,
    updates?: Partial<LiveSpan>
  ) => void;
  clearSpans: () => void;
  getSpanTree: () => SpanTreeNode[];
  getSpan: (spanId: number) => LiveSpan | undefined;
}

// Build tree structure from flat span map
function buildSpanTree(spans: Map<number, LiveSpan>): SpanTreeNode[] {
  const spanArray = Array.from(spans.values());
  const nodeMap = new Map<number, SpanTreeNode>();

  // Create nodes with empty children arrays
  spanArray.forEach((span) => {
    nodeMap.set(span.span_id, { ...span, children: [] });
  });

  // Build tree structure
  const roots: SpanTreeNode[] = [];
  spanArray.forEach((span) => {
    const node = nodeMap.get(span.span_id)!;
    if (span.parent_span_id === null) {
      roots.push(node);
    } else {
      const parent = nodeMap.get(span.parent_span_id);
      if (parent) {
        parent.children.push(node);
      } else {
        // Orphan span - add to roots
        roots.push(node);
      }
    }
  });

  // Sort children by span_id (order of creation)
  const sortChildren = (node: SpanTreeNode) => {
    node.children.sort((a, b) => a.span_id - b.span_id);
    node.children.forEach(sortChildren);
  };
  roots.forEach(sortChildren);

  return roots.sort((a, b) => a.span_id - b.span_id);
}

export const useSpanStore = create<SpanState>()((set, get) => ({
  activeSessionId: null,
  activeTraceId: null,
  spans: new Map(),
  isRecording: false,
  spanCount: 0,
  runningCount: 0,
  errorCount: 0,

  startRecording: (sessionId: number) => {
    set({
      activeSessionId: sessionId,
      activeTraceId: null,
      spans: new Map(),
      isRecording: true,
      spanCount: 0,
      runningCount: 0,
      errorCount: 0,
    });
  },

  stopRecording: () => {
    set({ isRecording: false });
  },

  addSpan: (span: LiveSpan) => {
    const { spans, activeTraceId } = get();
    const newSpans = new Map(spans);
    newSpans.set(span.span_id, span);

    // Update trace ID if this is the first span
    const newTraceId = activeTraceId || span.trace_id;

    set({
      spans: newSpans,
      activeTraceId: newTraceId,
      spanCount: newSpans.size,
      runningCount:
        get().runningCount + (span.status === 'running' ? 1 : 0),
      errorCount: get().errorCount + (span.status === 'error' ? 1 : 0),
    });
  },

  updateSpan: (spanId: number, updates: Partial<LiveSpan>) => {
    const { spans } = get();
    const span = spans.get(spanId);
    if (!span) return;

    const newSpans = new Map(spans);
    newSpans.set(spanId, { ...span, ...updates });

    set({ spans: newSpans });
  },

  completeSpan: (
    spanId: number,
    status: SpanStatus,
    updates?: Partial<LiveSpan>
  ) => {
    const { spans, runningCount, errorCount } = get();
    const span = spans.get(spanId);
    if (!span) return;

    const wasRunning = span.status === 'running';
    const newSpans = new Map(spans);
    newSpans.set(spanId, {
      ...span,
      status,
      ended_at: new Date().toISOString(),
      ...updates,
    });

    set({
      spans: newSpans,
      runningCount: wasRunning ? runningCount - 1 : runningCount,
      errorCount: status === 'error' ? errorCount + 1 : errorCount,
    });
  },

  clearSpans: () => {
    set({
      activeSessionId: null,
      activeTraceId: null,
      spans: new Map(),
      isRecording: false,
      spanCount: 0,
      runningCount: 0,
      errorCount: 0,
    });
  },

  getSpanTree: () => {
    return buildSpanTree(get().spans);
  },

  getSpan: (spanId: number) => {
    return get().spans.get(spanId);
  },
}));

// Selector hooks for common queries
export const useActiveSpans = () =>
  useSpanStore((state) => Array.from(state.spans.values()));

export const useSpanTree = () => useSpanStore((state) => state.getSpanTree());

export const useRecordingStatus = () =>
  useSpanStore((state) => ({
    isRecording: state.isRecording,
    spanCount: state.spanCount,
    runningCount: state.runningCount,
    errorCount: state.errorCount,
  }));
