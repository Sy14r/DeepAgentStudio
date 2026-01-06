import { useState, useRef, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Button,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
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
  History,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Clock,
  CheckCircle,
  AlertCircle,
  Loader2,
  Bot,
  User,
  Wrench,
  Brain,
  Eye,
  BarChart3,
  MessageSquare,
  Zap,
} from 'lucide-react';
import { useSessions, useSession, useSessionStatistics, useAgents, getErrorMessage } from '@/api/hooks';
import { Session, SessionStatus, TraceStep, Message, TraceStepType } from '@/api/types';

const STATUS_OPTIONS: { value: SessionStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All Statuses' },
  { value: 'completed', label: 'Completed' },
  { value: 'running', label: 'Running' },
  { value: 'pending', label: 'Pending' },
  { value: 'failed', label: 'Failed' },
];

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

function getStatusColor(status: SessionStatus) {
  switch (status) {
    case 'completed':
      return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
    case 'running':
      return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400';
    case 'pending':
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
    case 'failed':
      return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
    default:
      return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400';
  }
}

interface SessionCardProps {
  session: Session;
  onView: (id: number) => void;
  agentName?: string;
}

function SessionCard({ session, onView, agentName }: SessionCardProps) {
  return (
    <Card className="group hover:border-primary/50 transition-colors">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            {getStatusIcon(session.status)}
            <CardTitle className="text-lg">
              {session.title || `Session #${session.id}`}
            </CardTitle>
          </div>
          <Badge className={getStatusColor(session.status)}>
            {session.status}
          </Badge>
        </div>
        <CardDescription>
          {agentName || 'Unknown Agent'} - {new Date(session.started_at).toLocaleString()}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-4 text-sm mb-4">
          <div>
            <p className="text-muted-foreground">Tokens</p>
            <p className="font-medium">
              {(session.token_usage_input + session.token_usage_output).toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-muted-foreground">Latency</p>
            <p className="font-medium">
              {session.total_latency_ms ? `${session.total_latency_ms}ms` : '-'}
            </p>
          </div>
          <div>
            <p className="text-muted-foreground">Cost</p>
            <p className="font-medium">
              {session.total_cost ? `$${session.total_cost.toFixed(4)}` : '-'}
            </p>
          </div>
        </div>
        {session.error_message && (
          <Alert variant="destructive" className="mb-4">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="text-xs truncate">
              {session.error_message}
            </AlertDescription>
          </Alert>
        )}
        <Button
          variant="outline"
          size="sm"
          className="w-full"
          onClick={() => onView(session.id)}
        >
          <Eye className="h-4 w-4 mr-2" />
          View Details
        </Button>
      </CardContent>
    </Card>
  );
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

interface SessionDetailDialogProps {
  sessionId: number | null;
  open: boolean;
  onClose: () => void;
}

function SessionDetailDialog({ sessionId, open, onClose }: SessionDetailDialogProps) {
  const [activeTab, setActiveTab] = useState<'messages' | 'trace'>('messages');
  const { data: session, isLoading, error } = useSession(sessionId ?? undefined);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [showScrollIndicator, setShowScrollIndicator] = useState(false);

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

export function SessionsPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();

  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [agentFilter, setAgentFilter] = useState<string>('all');
  const [page, setPage] = useState(1);
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(
    id ? parseInt(id) : null
  );

  const pageSize = 12;

  const { data: agentsData } = useAgents({ pageSize: 100 });
  const agents = agentsData?.agents || [];

  const { data, isLoading, error } = useSessions({
    page,
    pageSize,
    status: statusFilter !== 'all' ? (statusFilter as SessionStatus) : undefined,
    agentId: agentFilter !== 'all' ? parseInt(agentFilter) : undefined,
  });

  const { data: stats } = useSessionStatistics(
    agentFilter !== 'all' ? parseInt(agentFilter) : undefined
  );

  const agentMap = new Map(agents.map((a) => [a.id, a.name]));

  const handleView = (sessionId: number) => {
    setSelectedSessionId(sessionId);
    navigate(`/sessions/${sessionId}`);
  };

  const handleCloseDetail = () => {
    setSelectedSessionId(null);
    navigate('/sessions');
  };

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;
  const sessions = data?.sessions || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Sessions</h1>
          <p className="text-muted-foreground">
            View your conversation history and session details.
          </p>
        </div>
      </div>

      {/* Statistics */}
      {stats && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <History className="h-4 w-4" />
                Total Sessions
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{stats.total_sessions}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-500" />
                Success Rate
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">
                {(stats.success_rate * 100).toFixed(1)}%
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Clock className="h-4 w-4" />
                Avg Latency
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">
                {stats.average_latency_ms
                  ? `${Math.round(stats.average_latency_ms)}ms`
                  : '-'}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <BarChart3 className="h-4 w-4" />
                Total Tokens
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">
                {stats.total_tokens_used.toLocaleString()}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <Select
          value={agentFilter}
          onValueChange={(value) => {
            setAgentFilter(value);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Filter by Agent" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Agents</SelectItem>
            {agents.map((agent) => (
              <SelectItem key={agent.id} value={agent.id.toString()}>
                {agent.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={statusFilter}
          onValueChange={(value) => {
            setStatusFilter(value);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Filter by Status" />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Error */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{getErrorMessage(error)}</AlertDescription>
        </Alert>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex justify-center py-12">
          <Spinner className="h-8 w-8" />
        </div>
      )}

      {/* Empty State */}
      {!isLoading && sessions.length === 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <History className="h-5 w-5" />
              No sessions yet
            </CardTitle>
            <CardDescription>
              Start a conversation in the playground to see sessions here.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Sessions track your conversations with agents, including messages,
              token usage, latency metrics, and execution traces.
            </p>
            <Button onClick={() => navigate('/playground')}>
              Go to Playground
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Sessions Grid */}
      {!isLoading && sessions.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {sessions.map((session) => (
            <SessionCard
              key={session.id}
              session={session}
              onView={handleView}
              agentName={session.agent_id ? agentMap.get(session.agent_id) : undefined}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {!isLoading && totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            <ChevronLeft className="h-4 w-4" />
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Session Detail Dialog */}
      <SessionDetailDialog
        sessionId={selectedSessionId}
        open={!!selectedSessionId}
        onClose={handleCloseDetail}
      />
    </div>
  );
}
