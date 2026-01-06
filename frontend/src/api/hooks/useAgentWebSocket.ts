/**
 * WebSocket hook for real-time agent execution streaming.
 *
 * Connects to the backend WebSocket endpoint and streams execution events
 * (tool calls, tool results, errors, final answers) in real-time.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuthStore } from '@/stores/authStore';

// WebSocket Event Types
export interface WSEvent {
  type: 'session_start' | 'tool_call' | 'tool_result' | 'error' | 'final_answer' | 'session_end' | 'pong';
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
  | SessionEndPayload;

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

// Hook Options
export interface UseAgentWebSocketOptions {
  agentId: number;
  onSessionStart?: (payload: SessionStartPayload, sessionId: number) => void;
  onToolCall?: (payload: ToolCallPayload, sessionId: number) => void;
  onToolResult?: (payload: ToolResultPayload, sessionId: number) => void;
  onFinalAnswer?: (payload: FinalAnswerPayload, sessionId: number) => void;
  onError?: (payload: ErrorPayload, sessionId: number) => void;
  onSessionEnd?: (payload: SessionEndPayload, sessionId: number) => void;
  onConnectionChange?: (connected: boolean) => void;
  autoReconnect?: boolean;
  reconnectDelay?: number;
}

// Hook Return Type
export interface UseAgentWebSocketReturn {
  isConnected: boolean;
  isExecuting: boolean;
  connect: () => void;
  disconnect: () => void;
  invoke: (message: string, sessionId?: number) => void;
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
    onConnectionChange,
    autoReconnect = true,
    reconnectDelay = 3000,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
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
          onSessionEnd?.(data.payload as SessionEndPayload, data.session_id);
          break;

        case 'pong':
          // Heartbeat response - no action needed
          break;

        default:
          console.warn('Unknown WebSocket event type:', data.type);
      }
    } catch (err) {
      console.error('Failed to parse WebSocket message:', err);
    }
  }, [onSessionStart, onToolCall, onToolResult, onFinalAnswer, onError, onSessionEnd]);

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
  const invoke = useCallback((message: string, sessionId?: number) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError('WebSocket not connected');
      return;
    }

    setError(null);

    const payload: { type: string; message: string; session_id?: number } = {
      type: 'invoke',
      message,
    };

    if (sessionId) {
      payload.session_id = sessionId;
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
