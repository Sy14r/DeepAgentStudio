import { useState, useRef, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Button,
  Textarea,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  ScrollArea,
  Badge,
  Spinner,
  Alert,
  AlertDescription,
  Switch,
  Label,
} from '@/components/ui';
import {
  Play,
  MessageSquare,
  GitBranch,
  Send,
  Bot,
  User,
  Wrench,
  Brain,
  AlertCircle,
  CheckCircle,
  Clock,
  History,
  RotateCcw,
  Wifi,
  WifiOff,
  Zap,
} from 'lucide-react';
import { useAgents, useInvokeAgent, useAgentWebSocket, getErrorMessage } from '@/api/hooks';
import type { ToolCallPayload, ToolResultPayload, FinalAnswerPayload, ErrorPayload } from '@/api/hooks';
import { useSessions, useSessionMessages } from '@/api/hooks/useSessions';
import { TraceStep, Session } from '@/api/types';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

interface TraceStepDisplay extends TraceStep {
  timestamp?: Date;
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div
        className={`h-8 w-8 rounded-full flex items-center justify-center shrink-0 ${
          isUser ? 'bg-primary text-primary-foreground' : 'bg-muted'
        }`}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div
        className={`max-w-[80%] rounded-lg p-3 ${
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted'
        }`}
      >
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>
        <p className="text-xs opacity-70 mt-1">
          {message.timestamp.toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
}

function TraceStepItem({ step }: { step: TraceStepDisplay }) {
  const getStepIcon = () => {
    switch (step.step_type) {
      case 'thought':
        return <Brain className="h-4 w-4 text-blue-500" />;
      case 'tool_call':
        return <Wrench className="h-4 w-4 text-orange-500" />;
      case 'tool_result':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      case 'final_answer':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStepColor = () => {
    switch (step.step_type) {
      case 'thought':
        return 'border-blue-200 bg-blue-50 dark:bg-blue-950/30';
      case 'tool_call':
        return 'border-orange-200 bg-orange-50 dark:bg-orange-950/30';
      case 'tool_result':
        return 'border-green-200 bg-green-50 dark:bg-green-950/30';
      case 'error':
        return 'border-red-200 bg-red-50 dark:bg-red-950/30';
      case 'final_answer':
        return 'border-green-200 bg-green-50 dark:bg-green-950/30';
      default:
        return 'border-gray-200 bg-gray-50 dark:bg-gray-950/30';
    }
  };

  return (
    <div className={`rounded-lg border p-3 ${getStepColor()}`}>
      <div className="flex items-center gap-2 mb-2">
        {getStepIcon()}
        <span className="font-medium capitalize text-sm">
          {step.step_type.replace('_', ' ')}
        </span>
        {step.tool_name && (
          <Badge variant="outline" className="text-xs">
            {step.tool_name}
          </Badge>
        )}
        {step.latency_ms && (
          <span className="text-xs text-muted-foreground ml-auto">
            {step.latency_ms}ms
          </span>
        )}
      </div>
      {step.content && (
        <p className="text-sm text-muted-foreground whitespace-pre-wrap">
          {step.content}
        </p>
      )}
      {step.tool_input && (
        <pre className="text-xs bg-background/50 rounded p-2 mt-2 overflow-x-auto">
          {JSON.stringify(step.tool_input, null, 2)}
        </pre>
      )}
      {step.tool_output && (
        <pre className="text-xs bg-background/50 rounded p-2 mt-2 overflow-x-auto">
          {JSON.stringify(step.tool_output, null, 2)}
        </pre>
      )}
    </div>
  );
}

export function PlaygroundPage() {
  const { agentId: paramAgentId } = useParams<{ agentId: string }>();
  const [selectedAgentId, setSelectedAgentId] = useState<number | null>(
    paramAgentId ? parseInt(paramAgentId) : null
  );
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [traceSteps, setTraceSteps] = useState<TraceStepDisplay[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [streamingEnabled, setStreamingEnabled] = useState(true);
  const [pendingStreamMessage, setPendingStreamMessage] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const traceStepIdRef = useRef(0);

  const { data: agentsData, isLoading: isLoadingAgents } = useAgents({
    pageSize: 100,
    isActive: true,
  });

  // Fetch sessions for the selected agent (for continue session feature)
  const { data: sessionsData } = useSessions({
    agentId: selectedAgentId || undefined,
    pageSize: 10,
  });

  // Fetch messages when a session is selected for continuation
  const { data: sessionMessages } = useSessionMessages(sessionId || undefined);

  const invokeAgent = useInvokeAgent(selectedAgentId || 0);

  // WebSocket streaming callbacks
  const handleToolCall = useCallback((payload: ToolCallPayload, wsSessionId: number) => {
    setSessionId(wsSessionId);
    const step: TraceStepDisplay = {
      id: ++traceStepIdRef.current,
      session_id: wsSessionId,
      step_number: payload.step_number,
      step_type: 'tool_call',
      content: null,
      tool_name: payload.tool_name,
      tool_input: payload.tool_input,
      tool_output: null,
      latency_ms: null,
      created_at: new Date().toISOString(),
      timestamp: new Date(),
    };
    setTraceSteps((prev) => [...prev, step]);
  }, []);

  const handleToolResult = useCallback((payload: ToolResultPayload, wsSessionId: number) => {
    const step: TraceStepDisplay = {
      id: ++traceStepIdRef.current,
      session_id: wsSessionId,
      step_number: payload.step_number,
      step_type: 'tool_result',
      content: null,
      tool_name: payload.tool_name,
      tool_input: null,
      tool_output: typeof payload.tool_output === 'object' ? payload.tool_output as Record<string, unknown> : { result: payload.tool_output },
      latency_ms: payload.latency_ms,
      created_at: new Date().toISOString(),
      timestamp: new Date(),
    };
    setTraceSteps((prev) => [...prev, step]);
  }, []);

  const handleFinalAnswer = useCallback((payload: FinalAnswerPayload, wsSessionId: number) => {
    setSessionId(wsSessionId);
    setPendingStreamMessage(null);

    // Add assistant message
    const assistantMessage: ChatMessage = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: payload.output,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, assistantMessage]);

    // Add final answer trace step
    const step: TraceStepDisplay = {
      id: ++traceStepIdRef.current,
      session_id: wsSessionId,
      step_number: 999,
      step_type: 'final_answer',
      content: payload.output,
      tool_name: null,
      tool_input: null,
      tool_output: null,
      latency_ms: payload.latency_ms,
      created_at: new Date().toISOString(),
      timestamp: new Date(),
    };
    setTraceSteps((prev) => [...prev, step]);
  }, []);

  const handleStreamError = useCallback((payload: ErrorPayload) => {
    setError(payload.error);
    setPendingStreamMessage(null);
  }, []);

  // WebSocket hook
  const {
    isConnected,
    isExecuting,
    connect,
    disconnect,
    invoke: wsInvoke,
    error: wsError,
  } = useAgentWebSocket({
    agentId: selectedAgentId || 0,
    onToolCall: handleToolCall,
    onToolResult: handleToolResult,
    onFinalAnswer: handleFinalAnswer,
    onError: handleStreamError,
  });

  const agents = agentsData?.agents || [];
  const recentSessions = sessionsData?.sessions || [];

  // Connect/disconnect WebSocket when streaming enabled and agent selected
  useEffect(() => {
    if (streamingEnabled && selectedAgentId) {
      connect();
    } else {
      disconnect();
    }
  }, [streamingEnabled, selectedAgentId, connect, disconnect]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-resize textarea as content changes
  useEffect(() => {
    const textarea = inputRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [inputValue]);

  useEffect(() => {
    if (paramAgentId) {
      setSelectedAgentId(parseInt(paramAgentId));
    }
  }, [paramAgentId]);

  // Load messages when resuming a session
  useEffect(() => {
    if (sessionMessages && sessionMessages.length > 0 && isLoadingHistory) {
      const loadedMessages: ChatMessage[] = sessionMessages
        .filter((msg) => msg.role === 'user' || msg.role === 'assistant')
        .map((msg) => ({
          id: `loaded-${msg.id}`,
          role: msg.role as 'user' | 'assistant',
          content: msg.content,
          timestamp: new Date(msg.created_at),
        }));
      setMessages(loadedMessages);
      setIsLoadingHistory(false);
    }
  }, [sessionMessages, isLoadingHistory]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || !selectedAgentId) return;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setError(null);

    // Use WebSocket streaming if enabled and connected
    if (streamingEnabled && isConnected) {
      setPendingStreamMessage(userMessage.content);
      wsInvoke(userMessage.content, sessionId || undefined);
      return;
    }

    // Fallback to REST API
    try {
      const response = await invokeAgent.mutateAsync({
        message: userMessage.content,
        session_id: sessionId || undefined,
      });

      if (response.session_id) {
        setSessionId(response.session_id);
      }

      if (response.success && response.output) {
        const assistantMessage: ChatMessage = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: response.output,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } else if (response.error) {
        setError(response.error);
      }

      if (response.steps && response.steps.length > 0) {
        setTraceSteps((prev) => [
          ...prev,
          ...response.steps.map((step) => ({
            ...step,
            timestamp: new Date(),
          })),
        ]);
      }
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleNewSession = () => {
    setMessages([]);
    setTraceSteps([]);
    setSessionId(null);
    setError(null);
    inputRef.current?.focus();
  };

  const handleContinueSession = (session: Session) => {
    setSessionId(session.id);
    setMessages([]);
    setTraceSteps([]);
    setError(null);
    setIsLoadingHistory(true);
  };

  const selectedAgent = agents.find((a) => a.id === selectedAgentId);

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Playground</h1>
          <p className="text-muted-foreground">
            Test your agents interactively.
          </p>
        </div>
        <div className="flex items-center gap-4">
          {/* Streaming toggle */}
          <div className="flex items-center gap-2">
            <Switch
              id="streaming-mode"
              checked={streamingEnabled}
              onCheckedChange={setStreamingEnabled}
            />
            <Label htmlFor="streaming-mode" className="flex items-center gap-1.5 cursor-pointer">
              <Zap className={`h-4 w-4 ${streamingEnabled ? 'text-yellow-500' : 'text-muted-foreground'}`} />
              <span className="text-sm">Streaming</span>
            </Label>
            {streamingEnabled && selectedAgentId && (
              <Badge variant={isConnected ? 'default' : 'secondary'} className="flex items-center gap-1">
                {isConnected ? (
                  <>
                    <Wifi className="h-3 w-3" />
                    Connected
                  </>
                ) : (
                  <>
                    <WifiOff className="h-3 w-3" />
                    Disconnected
                  </>
                )}
              </Badge>
            )}
          </div>
          {/* Continue Session dropdown */}
          {recentSessions.length > 0 && selectedAgentId && (
            <Select
              value=""
              onValueChange={(value) => {
                const session = recentSessions.find((s) => s.id === parseInt(value));
                if (session) handleContinueSession(session);
              }}
            >
              <SelectTrigger className="w-[200px]">
                <History className="h-4 w-4 mr-2" />
                <SelectValue placeholder="Continue Session" />
              </SelectTrigger>
              <SelectContent>
                {recentSessions.map((session) => (
                  <SelectItem key={session.id} value={session.id.toString()}>
                    #{session.id} - {new Date(session.started_at).toLocaleDateString()}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          <Button variant="outline" onClick={handleNewSession}>
            <RotateCcw className="h-4 w-4 mr-2" />
            New Session
          </Button>
        </div>
      </div>

      {/* Agent Selection */}
      <Card>
        <CardHeader className="py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Play className="h-5 w-5" />
              <CardTitle className="text-lg">Agent</CardTitle>
            </div>
            <Select
              value={selectedAgentId?.toString() || ''}
              onValueChange={(value) => {
                setSelectedAgentId(value ? parseInt(value) : null);
                handleNewSession();
              }}
            >
              <SelectTrigger className="w-[250px]">
                <SelectValue placeholder="Select an agent" />
              </SelectTrigger>
              <SelectContent>
                {isLoadingAgents ? (
                  <SelectItem value="loading" disabled>
                    Loading agents...
                  </SelectItem>
                ) : agents.length === 0 ? (
                  <SelectItem value="none" disabled>
                    No agents available
                  </SelectItem>
                ) : (
                  agents.map((agent) => (
                    <SelectItem key={agent.id} value={agent.id.toString()}>
                      {agent.name}
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          </div>
          {selectedAgent && (
            <CardDescription className="mt-2">
              {selectedAgent.description || 'No description'} -{' '}
              <Badge variant="secondary">{selectedAgent.agent_type}</Badge>
            </CardDescription>
          )}
        </CardHeader>
      </Card>

      {(error || wsError) && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error || wsError}</AlertDescription>
        </Alert>
      )}

      <div className="flex-1 grid gap-4 lg:grid-cols-2 min-h-0">
        {/* Chat Panel */}
        <Card className="flex flex-col min-h-0">
          <CardHeader className="py-3 border-b shrink-0">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              <CardTitle className="text-lg">Chat</CardTitle>
              <div className="flex items-center gap-2 ml-auto">
                {sessionId && messages.length > 0 && (
                  <Badge variant="secondary" className="flex items-center gap-1">
                    <History className="h-3 w-3" />
                    Memory Active
                  </Badge>
                )}
                {sessionId && (
                  <Badge variant="outline">
                    Session #{sessionId}
                  </Badge>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col p-0 min-h-0">
            <ScrollArea className="flex-1 p-4">
              {isLoadingHistory ? (
                <div className="h-full flex flex-col items-center justify-center gap-2 text-muted-foreground">
                  <Spinner className="h-6 w-6" />
                  <span>Loading conversation history...</span>
                </div>
              ) : messages.length === 0 ? (
                <div className="h-full flex items-center justify-center text-muted-foreground text-center">
                  {selectedAgentId
                    ? 'Start a conversation with your agent.'
                    : 'Select an agent to start chatting.'}
                </div>
              ) : (
                <div className="space-y-4">
                  {messages.map((msg) => (
                    <MessageBubble key={msg.id} message={msg} />
                  ))}
                  {(invokeAgent.isPending || isExecuting) && (
                    <div className="flex gap-3">
                      <div className="h-8 w-8 rounded-full flex items-center justify-center bg-muted shrink-0">
                        <Bot className="h-4 w-4" />
                      </div>
                      <div className="bg-muted rounded-lg p-3 flex items-center gap-2">
                        <Spinner className="h-4 w-4" />
                        {isExecuting && streamingEnabled && (
                          <span className="text-sm text-muted-foreground">
                            Executing...
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </ScrollArea>
            <div className="p-4 border-t shrink-0">
              <div className="flex gap-2 items-end">
                <Textarea
                  ref={inputRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={
                    selectedAgentId
                      ? 'Type your message... (Shift+Enter for new line)'
                      : 'Select an agent first'
                  }
                  disabled={!selectedAgentId || invokeAgent.isPending || isExecuting}
                  className="min-h-[44px] max-h-[200px] resize-none"
                  rows={1}
                />
                <Button
                  onClick={handleSendMessage}
                  disabled={
                    !inputValue.trim() ||
                    !selectedAgentId ||
                    invokeAgent.isPending ||
                    isExecuting
                  }
                  className="shrink-0 h-[44px]"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Trace Panel */}
        <Card className="flex flex-col min-h-0">
          <CardHeader className="py-3 border-b shrink-0">
            <div className="flex items-center gap-2">
              <GitBranch className="h-5 w-5" />
              <CardTitle className="text-lg">Execution Trace</CardTitle>
              {traceSteps.length > 0 && (
                <Badge variant="outline" className="ml-auto">
                  {traceSteps.length} steps
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="flex-1 p-0 min-h-0">
            <ScrollArea className="h-full p-4">
              {traceSteps.length === 0 ? (
                <div className="h-full flex items-center justify-center text-muted-foreground text-center">
                  Execution trace will appear here during conversations.
                </div>
              ) : (
                <div className="space-y-3">
                  {traceSteps.map((step, index) => (
                    <TraceStepItem key={`${step.id}-${index}`} step={step} />
                  ))}
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
