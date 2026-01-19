/**
 * WebSocket hook for real-time agent execution streaming.
 *
 * Connects to the backend WebSocket endpoint and streams execution events
 * (tool calls, tool results, errors, final answers, span events) in real-time.
 *
 * Implements Phase 3 of ENHANCED_TRACING_SPEC.md for span events.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { useSpanStore, type SpanType, type SpanStatus, type LiveSpan } from '@/stores/spanStore';
import type { ContentBlock } from '../types';

// WebSocket Event Types
export interface WSEvent {
  type: 'session_start' | 'tool_call' | 'tool_result' | 'error' | 'final_answer' | 'session_end' | 'pong' | 'span_start' | 'span_end' | 'session_title_update' | 'task_created' | 'task_updated' | 'task_completed' | 'task_removed';
  session_id: number;
  timestamp: string;
  payload: WSPayload;
}

export type WSPayload =
  | SessionStartPayload
  | ToolCallPayload
  | ToolResultPayload
  | ErrorPayload
  | FinalAnswerPayload
  | SessionEndPayload
  | SpanStartPayload
  | SpanEndPayload
  | SessionTitleUpdatePayload
  | TaskCreatedPayload
  | TaskUpdatedPayload
  | TaskCompletedPayload
  | TaskRemovedPayload;

export interface SessionStartPayload {
  agent_id: number;
  agent_name: string;
}

export interface ToolCallPayload {
  step_number: number;
  tool_name: string;
  tool_input: Record<string, unknown>;
}

export interface ToolResultPayload {
  step_number: number;
  tool_name: string;
  tool_output: unknown;
  latency_ms: number;
}

export interface ErrorPayload {
  error: string;
  error_type: string;
  tool_name?: string;
}

export interface FinalAnswerPayload {
  output: string;
  content_blocks?: ContentBlock[];  // Multimodal content blocks (images, audio, video, files)
  token_usage: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
  };
  latency_ms: number;
}

export interface SessionEndPayload {
  success: boolean;
  total_steps: number;
}

export interface SessionTitleUpdatePayload {
  title: string;
}

// Span event payloads (Phase 3)
export interface SpanStartPayload {
  span_id: number;
  trace_id: string;
  parent_span_id: number | null;
  span_type: SpanType;
  name: string;
  depth: number;
  input?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface SpanEndPayload {
  span_id: number;
  status: SpanStatus;
  duration_ms?: number;
  output?: Record<string, unknown>;
  tokens_input?: number;
  tokens_output?: number;
  cost_usd?: number;
  error_message?: string;
}

// Task event payloads
export interface TaskCreatedPayload {
  task_id: number;
  message: string;
}

export interface TaskUpdatedPayload {
  task_id: number;
  status?: string;
  message: string;
}

export interface TaskCompletedPayload {
  task_id: number;
  message: string;
}

export interface TaskRemovedPayload {
  task_id: number;
  message: string;
}

// Hook Options
export interface UseAgentWebSocketOptions {
  agentId: number;
  onSessionStart?: (payload: SessionStartPayload, sessionId: number) => void;
  onToolCall?: (payload: ToolCallPayload, sessionId: number) => void;
  onToolResult?: (payload: ToolResultPayload, sessionId: number) => void;
  onFinalAnswer?: (payload: FinalAnswerPayload, sessionId: number) => void;
  onError?: (payload: ErrorPayload, sessionId: number) => void;
  onSessionEnd?: (payload: SessionEndPayload, sessionId: number) => void;
  onSessionTitleUpdate?: (payload: SessionTitleUpdatePayload, sessionId: number) => void;
  onSpanStart?: (payload: SpanStartPayload, sessionId: number) => void;
  onSpanEnd?: (payload: SpanEndPayload, sessionId: number) => void;
  onTaskCreated?: (payload: TaskCreatedPayload, sessionId: number) => void;
  onTaskUpdated?: (payload: TaskUpdatedPayload, sessionId: number) => void;
  onTaskCompleted?: (payload: TaskCompletedPayload, sessionId: number) => void;
  onTaskRemoved?: (payload: TaskRemovedPayload, sessionId: number) => void;
  onConnectionChange?: (connected: boolean) => void;
  autoReconnect?: boolean;
  reconnectDelay?: number;
  enableSpanTracking?: boolean;  // Auto-update spanStore on span events
}

// Attachment type for WebSocket
export interface WSAttachment {
  name: string;
  type: 'text' | 'image' | 'code' | 'other';
  mimeType: string;
  content?: string;
}

// Hook Return Type
export interface UseAgentWebSocketReturn {
  isConnected: boolean;
  isExecuting: boolean;
  connect: () => void;
  disconnect: () => void;
  invoke: (message: string, sessionId?: number, attachments?: WSAttachment[]) => void;
  error: string | null;
}

/**
 * Hook for WebSocket-based agent execution streaming.
 *
 * @example
 * ```tsx
 * const { isConnected, isExecuting, invoke } = useAgentWebSocket({
 *   agentId: 1,
 *   onToolCall: (payload) => console.log('Tool called:', payload.tool_name),
 *   onToolResult: (payload) => console.log('Tool result:', payload.tool_output),
 *   onFinalAnswer: (payload) => console.log('Answer:', payload.output),
 * });
 *
 * // Send a message
 * invoke("What is 2+2?");
 * ```
 */
export function useAgentWebSocket(options: UseAgentWebSocketOptions): UseAgentWebSocketReturn {
  const {
    agentId,
    onSessionStart,
    onToolCall,
    onToolResult,
    onFinalAnswer,
    onError,
    onSessionEnd,
    onSessionTitleUpdate,
    onSpanStart,
    onSpanEnd,
    onTaskCreated,
    onTaskUpdated,
    onTaskCompleted,
    onTaskRemoved,
    onConnectionChange,
    autoReconnect = true,
    reconnectDelay = 3000,
    enableSpanTracking = true,  // Auto-track spans by default
  } = options;

  // Get span store actions for auto-tracking
  const spanStore = useSpanStore();

  const [isConnected, setIsConnected] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const intentionalDisconnectRef = useRef(false);

  const token = useAuthStore((state) => state.token);

  // Get WebSocket URL
  const getWsUrl = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = import.meta.env.VITE_API_URL
      ? new URL(import.meta.env.VITE_API_URL).host
      : window.location.host;
    return `${protocol}//${host}/api/v1/ws/agents/${agentId}/stream?token=${token}`;
  }, [agentId, token]);

  // Handle incoming messages
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data: WSEvent = JSON.parse(event.data);

      switch (data.type) {
        case 'session_start':
          setIsExecuting(true);
          // Start span recording for this session
          if (enableSpanTracking) {
            spanStore.startRecording(data.session_id);
          }
          onSessionStart?.(data.payload as SessionStartPayload, data.session_id);
          break;

        case 'tool_call':
          onToolCall?.(data.payload as ToolCallPayload, data.session_id);
          break;

        case 'tool_result':
          onToolResult?.(data.payload as ToolResultPayload, data.session_id);
          break;

        case 'final_answer':
          onFinalAnswer?.(data.payload as FinalAnswerPayload, data.session_id);
          break;

        case 'error':
          const errorPayload = data.payload as ErrorPayload;
          setError(errorPayload.error);
          onError?.(errorPayload, data.session_id);
          break;

        case 'session_end':
          setIsExecuting(false);
          // Stop span recording
          if (enableSpanTracking) {
            spanStore.stopRecording();
          }
          onSessionEnd?.(data.payload as SessionEndPayload, data.session_id);
          break;

        case 'session_title_update':
          onSessionTitleUpdate?.(data.payload as SessionTitleUpdatePayload, data.session_id);
          break;

        case 'span_start': {
          const spanPayload = data.payload as SpanStartPayload;
          // Add span to store
          if (enableSpanTracking) {
            const newSpan: LiveSpan = {
              span_id: spanPayload.span_id,
              trace_id: spanPayload.trace_id,
              parent_span_id: spanPayload.parent_span_id,
              span_type: spanPayload.span_type,
              name: spanPayload.name,
              depth: spanPayload.depth,
              status: 'running',
              started_at: data.timestamp,
              input: spanPayload.input,
              metadata: spanPayload.metadata,
            };
            spanStore.addSpan(newSpan);
          }
          onSpanStart?.(spanPayload, data.session_id);
          break;
        }

        case 'span_end': {
          const spanPayload = data.payload as SpanEndPayload;
          // Complete span in store
          if (enableSpanTracking) {
            spanStore.completeSpan(spanPayload.span_id, spanPayload.status, {
              duration_ms: spanPayload.duration_ms,
              output: spanPayload.output,
              tokens_input: spanPayload.tokens_input,
              tokens_output: spanPayload.tokens_output,
              cost_usd: spanPayload.cost_usd,
              error_message: spanPayload.error_message,
            });
          }
          onSpanEnd?.(spanPayload, data.session_id);
          break;
        }

        case 'pong':
          // Heartbeat response - no action needed
          break;

        // Task events
        case 'task_created':
          onTaskCreated?.(data.payload as TaskCreatedPayload, data.session_id);
          break;

        case 'task_updated':
          onTaskUpdated?.(data.payload as TaskUpdatedPayload, data.session_id);
          break;

        case 'task_completed':
          onTaskCompleted?.(data.payload as TaskCompletedPayload, data.session_id);
          break;

        case 'task_removed':
          onTaskRemoved?.(data.payload as TaskRemovedPayload, data.session_id);
          break;

        default:
          console.warn('Unknown WebSocket event type:', data.type);
      }
    } catch (err) {
      console.error('Failed to parse WebSocket message:', err);
    }
  }, [onSessionStart, onToolCall, onToolResult, onFinalAnswer, onError, onSessionEnd, onSessionTitleUpdate, onSpanStart, onSpanEnd, onTaskCreated, onTaskUpdated, onTaskCompleted, onTaskRemoved, enableSpanTracking, spanStore]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!token) {
      setError('Not authenticated');
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    intentionalDisconnectRef.current = false;
    setError(null);

    try {
      const ws = new WebSocket(getWsUrl());

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
        onConnectionChange?.(true);
      };

      ws.onclose = (event) => {
        setIsConnected(false);
        setIsExecuting(false);
        onConnectionChange?.(false);

        // Auto-reconnect if not intentional close
        if (autoReconnect && !intentionalDisconnectRef.current && event.code !== 1000) {
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectDelay);
        }
      };

      ws.onerror = () => {
        setError('WebSocket connection error');
      };

      ws.onmessage = handleMessage;

      wsRef.current = ws;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect');
    }
  }, [token, getWsUrl, handleMessage, onConnectionChange, autoReconnect, reconnectDelay]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    intentionalDisconnectRef.current = true;

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }

    setIsConnected(false);
    setIsExecuting(false);
  }, []);

  // Send invoke message
  const invoke = useCallback((message: string, sessionId?: number, attachments?: WSAttachment[]) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError('WebSocket not connected');
      return;
    }

    setError(null);

    const payload: { type: string; message: string; session_id?: number; attachments?: WSAttachment[] } = {
      type: 'invoke',
      message,
    };

    if (sessionId) {
      payload.session_id = sessionId;
    }

    if (attachments && attachments.length > 0) {
      payload.attachments = attachments;
    }

    wsRef.current.send(JSON.stringify(payload));
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  // Reconnect when agentId changes
  useEffect(() => {
    if (isConnected) {
      disconnect();
      connect();
    }
  }, [agentId]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    isConnected,
    isExecuting,
    connect,
    disconnect,
    invoke,
    error,
  };
}
