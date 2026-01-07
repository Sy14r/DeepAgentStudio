import { useState, useRef, useEffect } from 'react';
import {
  Button,
  Badge,
  Spinner,
  Alert,
  AlertDescription,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui';
import {
  ChevronDown,
  Clock,
  CheckCircle,
  AlertCircle,
  Loader2,
  Bot,
  User,
  Wrench,
  Brain,
  MessageSquare,
  Zap,
} from 'lucide-react';
import { useSession, getErrorMessage } from '@/api/hooks';
import { SessionStatus, TraceStep, Message, TraceStepType } from '@/api/types';

function getStatusIcon(status: SessionStatus) {
  switch (status) {
    case 'completed':
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case 'running':
      return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
    case 'pending':
      return <Clock className="h-4 w-4 text-yellow-500" />;
    case 'failed':
      return <AlertCircle className="h-4 w-4 text-red-500" />;
    default:
      return <Clock className="h-4 w-4 text-gray-500" />;
  }
}

function getTraceStepIcon(stepType: TraceStepType) {
  switch (stepType) {
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
}

function getTraceStepColor(stepType: TraceStepType) {
  switch (stepType) {
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
}

function TraceStepItem({ step }: { step: TraceStep }) {
  return (
    <div className={`rounded-lg border p-3 overflow-hidden ${getTraceStepColor(step.step_type)}`}>
      <div className="flex items-center gap-2 mb-2">
        {getTraceStepIcon(step.step_type)}
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
        <pre className="text-xs bg-background/50 rounded p-2 mt-2 overflow-auto whitespace-pre-wrap break-all">
          {JSON.stringify(step.tool_input, null, 2)}
        </pre>
      )}
      {step.tool_output && (
        <pre className="text-xs bg-background/50 rounded p-2 mt-2 overflow-auto whitespace-pre-wrap break-all">
          {JSON.stringify(step.tool_output, null, 2)}
        </pre>
      )}
    </div>
  );
}

function MessageItem({ message }: { message: Message }) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  const isTool = message.role === 'tool';

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div
        className={`h-8 w-8 rounded-full flex items-center justify-center shrink-0 ${
          isUser
            ? 'bg-primary text-primary-foreground'
            : isSystem
            ? 'bg-yellow-500 text-white'
            : isTool
            ? 'bg-orange-500 text-white'
            : 'bg-muted'
        }`}
      >
        {isUser ? (
          <User className="h-4 w-4" />
        ) : isTool ? (
          <Wrench className="h-4 w-4" />
        ) : (
          <Bot className="h-4 w-4" />
        )}
      </div>
      <div
        className={`max-w-[80%] rounded-lg p-3 ${
          isUser
            ? 'bg-primary text-primary-foreground'
            : isSystem
            ? 'bg-yellow-50 dark:bg-yellow-950/30'
            : 'bg-muted'
        }`}
      >
        <p className="text-xs font-medium mb-1 capitalize">{message.role}</p>
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        <p className="text-xs opacity-70 mt-1">
          {new Date(message.created_at).toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
}

export interface SessionDetailDialogProps {
  sessionId: number | null;
  open: boolean;
  onClose: () => void;
}

export function SessionDetailDialog({ sessionId, open, onClose }: SessionDetailDialogProps) {
  const [activeTab, setActiveTab] = useState<'messages' | 'trace'>('messages');
  const { data: session, isLoading, error, refetch } = useSession(sessionId ?? undefined);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [showScrollIndicator, setShowScrollIndicator] = useState(false);

  // Auto-refresh while session is running or pending
  useEffect(() => {
    if (!open || !session) return;

    // Only poll if session is still in progress
    const isInProgress = session.status === 'running' || session.status === 'pending';
    if (!isInProgress) return;

    const interval = setInterval(() => {
      refetch();
    }, 1000); // Poll every second while running

    return () => clearInterval(interval);
  }, [open, session?.status, refetch]);

  // Check if content overflows and update scroll indicator
  useEffect(() => {
    const checkScroll = () => {
      const container = scrollContainerRef.current;
      if (container) {
        const hasOverflow = container.scrollHeight > container.clientHeight;
        const isAtBottom = container.scrollTop + container.clientHeight >= container.scrollHeight - 20;
        setShowScrollIndicator(hasOverflow && !isAtBottom);
      }
    };

    // Check on mount and when session/tab changes
    checkScroll();

    const container = scrollContainerRef.current;
    if (container) {
      container.addEventListener('scroll', checkScroll);
      return () => container.removeEventListener('scroll', checkScroll);
    }
  }, [session, activeTab]);

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-4xl h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>
            {session?.title || `Session #${sessionId}`}
          </DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex justify-center py-8">
            <Spinner className="h-8 w-8" />
          </div>
        ) : error ? (
          <Alert variant="destructive">
            <AlertDescription>{getErrorMessage(error)}</AlertDescription>
          </Alert>
        ) : session ? (
          <div className="flex flex-col flex-1 min-h-0 overflow-hidden">
            {/* Session Stats */}
            <div className="grid grid-cols-4 gap-4 mb-4">
              <div className="text-center p-3 bg-muted rounded-lg">
                <p className="text-xs text-muted-foreground">Status</p>
                <div className="flex items-center justify-center gap-1 mt-1">
                  {getStatusIcon(session.status)}
                  <span className="font-medium capitalize">{session.status}</span>
                </div>
              </div>
              <div className="text-center p-3 bg-muted rounded-lg">
                <p className="text-xs text-muted-foreground">Total Tokens</p>
                <p className="font-medium">
                  {(session.token_usage_input + session.token_usage_output).toLocaleString()}
                </p>
              </div>
              <div className="text-center p-3 bg-muted rounded-lg">
                <p className="text-xs text-muted-foreground">Latency</p>
                <p className="font-medium">
                  {session.total_latency_ms ? `${session.total_latency_ms}ms` : '-'}
                </p>
              </div>
              <div className="text-center p-3 bg-muted rounded-lg">
                <p className="text-xs text-muted-foreground">Cost</p>
                <p className="font-medium">
                  {session.total_cost ? `$${session.total_cost.toFixed(4)}` : '-'}
                </p>
              </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-2 mb-4">
              <Button
                variant={activeTab === 'messages' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setActiveTab('messages')}
              >
                <MessageSquare className="h-4 w-4 mr-2" />
                Messages ({session.messages?.length || 0})
              </Button>
              <Button
                variant={activeTab === 'trace' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setActiveTab('trace')}
              >
                <Zap className="h-4 w-4 mr-2" />
                Trace ({session.trace_steps?.length || 0})
              </Button>
            </div>

            {/* Content area with scroll indicator */}
            <div className="relative flex-1 min-h-0">
              <div
                ref={scrollContainerRef}
                className="h-full overflow-y-auto custom-scrollbar pr-2"
              >
                {activeTab === 'messages' ? (
                  <div className="space-y-4 pb-4">
                    {session.messages && session.messages.length > 0 ? (
                      session.messages.map((msg) => (
                        <MessageItem key={msg.id} message={msg} />
                      ))
                    ) : (
                      <p className="text-center text-muted-foreground py-8">
                        No messages in this session.
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="space-y-3 pb-4">
                    {session.trace_steps && session.trace_steps.length > 0 ? (
                      session.trace_steps.map((step) => (
                        <TraceStepItem key={step.id} step={step} />
                      ))
                    ) : (
                      <p className="text-center text-muted-foreground py-8">
                        No trace steps recorded.
                      </p>
                    )}
                  </div>
                )}
              </div>

              {/* Scroll indicator - shows when there's more content below */}
              {showScrollIndicator && (
                <div className="absolute bottom-0 left-0 right-0 pointer-events-none">
                  <div className="h-16 bg-gradient-to-t from-background via-background/80 to-transparent" />
                  <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex items-center gap-1 text-xs text-muted-foreground bg-background/90 px-3 py-1 rounded-full border shadow-sm pointer-events-auto">
                    <ChevronDown className="h-3 w-3 animate-bounce" />
                    <span>Scroll for more</span>
                  </div>
                </div>
              )}
            </div>

            {session.error_message && (
              <Alert variant="destructive" className="mt-4">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  <strong>{session.error_type}:</strong> {session.error_message}
                </AlertDescription>
              </Alert>
            )}
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
