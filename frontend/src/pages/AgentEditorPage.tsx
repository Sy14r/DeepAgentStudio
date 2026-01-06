import { useEffect, useState, useRef, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Editor, { OnMount } from '@monaco-editor/react';
import ReactMarkdown from 'react-markdown';
import {
  Button,
  Textarea,
  Badge,
  Spinner,
  Alert,
  AlertDescription,
  ScrollArea,
  Checkbox,
} from '@/components/ui';
import {
  Save,
  X,
  Play,
  Send,
  Bot,
  User,
  Wrench,
  Brain,
  AlertCircle,
  CheckCircle,
  Clock,
  GitBranch,
  MessageSquare,
  RotateCcw,
  Code,
  Server,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import {
  useAgent,
  useCreateAgent,
  useUpdateAgent,
  useLLMProviders,
  useTools,
  useMCPServers,
  useAgentMCPServers,
  useAssignAgentMCPServers,
  useInvokeAgent,
  getErrorMessage,
} from '@/api/hooks';
import { useUIStore } from '@/stores/uiStore';
import { AgentCreateRequest, TraceStep } from '@/api/types';
import { ModelParameterHelper } from '@/components/agents/ModelParameterHelper';

// Default agent configuration template
// This structure matches what the backend returns for saved agents
const DEFAULT_AGENT_CONFIG: AgentCreateRequest = {
  name: 'My Agent',
  description: 'A helpful AI agent',
  agent_type: 'ReAct',
  tags: [],
  config: {
    llm_config: {
      provider: 'openai',
      provider_id: 0,
      model: 'gpt-4',
      temperature: 0.7,
      max_tokens: 4096,
      stop_sequences: [],
    },
    reflection_config: {
      enabled: false,
      depth: 2,
      iteration_limit: 5,
    },
    memory_config: {
      type: 'buffer',
      context_window: 10,
      retrieval_strategy: 'similarity',
    },
    tool_ids: [],
    prompt_id: null,
    system_prompt: 'You are a helpful AI assistant.',
  },
};

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface TraceStepDisplay extends TraceStep {
  timestamp?: Date;
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-2 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div
        className={`h-7 w-7 rounded-full flex items-center justify-center shrink-0 ${
          isUser ? 'bg-primary text-primary-foreground' : 'bg-muted'
        }`}
      >
        {isUser ? <User className="h-3 w-3" /> : <Bot className="h-3 w-3" />}
      </div>
      <div
        className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
          isUser ? 'bg-primary text-primary-foreground' : 'bg-muted'
        }`}
      >
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}

function TraceStepItem({ step }: { step: TraceStepDisplay }) {
  const getStepIcon = () => {
    switch (step.step_type) {
      case 'thought':
        return <Brain className="h-3 w-3 text-blue-500" />;
      case 'tool_call':
        return <Wrench className="h-3 w-3 text-orange-500" />;
      case 'tool_result':
        return <CheckCircle className="h-3 w-3 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-3 w-3 text-red-500" />;
      case 'final_answer':
        return <CheckCircle className="h-3 w-3 text-green-600" />;
      default:
        return <Clock className="h-3 w-3 text-gray-500" />;
    }
  };

  return (
    <div className="text-xs border rounded p-2 bg-muted/30">
      <div className="flex items-center gap-1 mb-1">
        {getStepIcon()}
        <span className="font-medium capitalize">
          {step.step_type.replace('_', ' ')}
        </span>
        {step.tool_name && (
          <Badge variant="outline" className="text-[10px] h-4">
            {step.tool_name}
          </Badge>
        )}
      </div>
      {step.content && (
        <p className="text-muted-foreground whitespace-pre-wrap line-clamp-3">
          {step.content}
        </p>
      )}
    </div>
  );
}

export function AgentEditorPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { theme } = useUIStore();

  const isEditing = id !== undefined && id !== 'new';
  const agentId = isEditing ? parseInt(id) : null;

  // Editor state
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const editorRef = useRef<any>(null);

  // Chat state
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [traceSteps, setTraceSteps] = useState<TraceStepDisplay[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);

  // MCP server panel state
  const [mcpExpanded, setMcpExpanded] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Data hooks
  const { data: agent, isLoading: isLoadingAgent } = useAgent(agentId ?? undefined);
  const { data: providersData } = useLLMProviders({ pageSize: 100 });
  const { data: toolsData } = useTools({ pageSize: 100 });
  const { data: mcpServersData } = useMCPServers({ pageSize: 100 });
  const { data: agentMCPServers } = useAgentMCPServers(agentId ?? undefined);

  const createAgent = useCreateAgent();
  const updateAgent = useUpdateAgent(agentId ?? 0);
  const invokeAgent = useInvokeAgent(agentId ?? 0);
  const assignMCPServers = useAssignAgentMCPServers(agentId ?? 0);

  const providers = providersData?.providers || [];
  const tools = toolsData?.tools || [];
  const mcpServers = mcpServersData?.servers || [];

  // Determine Monaco theme
  const getMonacoTheme = () => {
    if (theme === 'system') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'deepagent-dark'
        : 'deepagent-light';
    }
    return theme === 'dark' ? 'deepagent-dark' : 'deepagent-light';
  };

  // Initialize editor with agent data or default template
  useEffect(() => {
    if (isEditing && agent) {
      const agentConfig: AgentCreateRequest = {
        name: agent.name,
        description: agent.description || undefined,
        agent_type: agent.agent_type,
        tags: agent.tags || [],
        config: agent.current_version?.config || DEFAULT_AGENT_CONFIG.config,
      };
      setCode(JSON.stringify(agentConfig, null, 2));
      setHasUnsavedChanges(false);
    } else if (!isEditing) {
      const defaultConfig = { ...DEFAULT_AGENT_CONFIG };
      if (providers.length > 0) {
        const firstProvider = providers[0];
        defaultConfig.config.llm_config.provider_id = firstProvider.id;
        defaultConfig.config.llm_config.provider = firstProvider.provider_type;
      }
      setCode(JSON.stringify(defaultConfig, null, 2));
      setHasUnsavedChanges(false);
    }
  }, [isEditing, agent, providers]);

  // Track unsaved changes
  useEffect(() => {
    if (code && !isLoadingAgent) {
      setHasUnsavedChanges(true);
    }
  }, [code]);

  // Scroll chat to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-resize textarea as content changes
  useEffect(() => {
    const textarea = inputRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
  }, [inputValue]);

  // Validate JSON on code change
  useEffect(() => {
    if (!code) {
      setValidationError(null);
      return;
    }

    try {
      const parsed = JSON.parse(code);

      if (!parsed.name || typeof parsed.name !== 'string') {
        setValidationError('name is required and must be a string');
        return;
      }

      if (
        !parsed.agent_type ||
        !['ReAct', 'Plan-and-Execute', 'Conversational', 'Custom'].includes(parsed.agent_type)
      ) {
        setValidationError('agent_type must be one of: ReAct, Plan-and-Execute, Conversational, Custom');
        return;
      }

      if (!parsed.config || !parsed.config.llm_config) {
        setValidationError('config.llm_config is required');
        return;
      }

      if (!parsed.config.llm_config.model) {
        setValidationError('config.llm_config.model is required');
        return;
      }

      if (typeof parsed.config.llm_config.provider_id !== 'number') {
        setValidationError('config.llm_config.provider_id must be a number');
        return;
      }

      setValidationError(null);
    } catch (e) {
      if (e instanceof SyntaxError) {
        setValidationError(`JSON syntax error: ${e.message}`);
      } else {
        setValidationError('Invalid JSON');
      }
    }
  }, [code]);

  const handleEditorMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;

    // Define custom themes
    monaco.editor.defineTheme('deepagent-dark', {
      base: 'vs-dark',
      inherit: true,
      rules: [
        { token: 'string.key.json', foreground: '9CDCFE' },
        { token: 'string.value.json', foreground: 'CE9178' },
        { token: 'number', foreground: 'B5CEA8' },
        { token: 'keyword', foreground: '569CD6' },
      ],
      colors: {
        'editor.background': '#0f0f17',
        'editor.foreground': '#e4e4e7',
        'editor.lineHighlightBackground': '#1a1a2e',
        'editor.selectionBackground': '#3d3d5c',
        'editorCursor.foreground': '#60a5fa',
        'editorLineNumber.foreground': '#6b7280',
        'editorLineNumber.activeForeground': '#e4e4e7',
        'editor.inactiveSelectionBackground': '#2d2d44',
      },
    });

    monaco.editor.defineTheme('deepagent-light', {
      base: 'vs',
      inherit: true,
      rules: [
        { token: 'string.key.json', foreground: '0451A5' },
        { token: 'string.value.json', foreground: 'A31515' },
        { token: 'number', foreground: '098658' },
        { token: 'keyword', foreground: '0000FF' },
      ],
      colors: {
        'editor.background': '#fafafa',
        'editor.foreground': '#1f2937',
        'editor.lineHighlightBackground': '#f3f4f6',
        'editor.selectionBackground': '#add6ff',
        'editorCursor.foreground': '#2563eb',
        'editorLineNumber.foreground': '#9ca3af',
        'editorLineNumber.activeForeground': '#1f2937',
        'editor.inactiveSelectionBackground': '#e5ebf1',
      },
    });

    monaco.editor.setTheme(getMonacoTheme());
  };

  const handleSave = async () => {
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);

    try {
      const agentData: AgentCreateRequest = JSON.parse(code);

      if (isEditing && agentId) {
        await updateAgent.mutateAsync({
          name: agentData.name,
          description: agentData.description,
          agent_type: agentData.agent_type,
          tags: agentData.tags,
          config: agentData.config,
        });
      } else {
        const created = await createAgent.mutateAsync(agentData);
        // Navigate to edit page for newly created agent
        navigate(`/agents/${created.id}/edit`, { replace: true });
      }
      setHasUnsavedChanges(false);
    } catch (err) {
      if (err instanceof SyntaxError) {
        setError(`Invalid JSON: ${err.message}`);
      } else {
        setError(getErrorMessage(err));
      }
    }
  };

  const handleFormatCode = () => {
    try {
      const parsed = JSON.parse(code);
      setCode(JSON.stringify(parsed, null, 2));
    } catch {
      // Can't format invalid JSON
    }
  };

  const handleCancel = () => {
    navigate('/agents');
  };

  // Chat handlers
  const handleSendMessage = async () => {
    if (!inputValue.trim() || !agentId) return;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setChatError(null);

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
        setChatError(response.error);
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
      setChatError(getErrorMessage(err));
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
    setChatError(null);
    inputRef.current?.focus();
  };

  // Build helpful comment header
  const getHelpText = () => {
    let help = 'Available LLM Providers:\n';
    if (providers.length === 0) {
      help += '  (No providers configured - add one in Settings)\n';
    } else {
      providers.forEach((p) => {
        help += `  - provider_id: ${p.id} → ${p.name} (${p.provider_type})\n`;
      });
    }

    help += '\nAvailable Tools:\n';
    if (tools.length === 0) {
      help += '  (No tools available)\n';
    } else {
      tools.forEach((t) => {
        help += `  - tool_id: ${t.id} → ${t.name}\n`;
      });
    }

    help += '\nMCP Servers (assign via API or checkbox below):\n';
    if (mcpServers.length === 0) {
      help += '  (No MCP servers - add in Settings)\n';
    } else {
      mcpServers.forEach((s) => {
        const assigned = agentMCPServers?.some((a) => a.id === s.id) ? ' [assigned]' : '';
        help += `  - ${s.name} (${s.transport_type})${assigned}\n`;
      });
    }

    help += '\nAgent Types: ReAct, Plan-and-Execute, Conversational, Custom';

    return help;
  };

  // Parse current llm_config from JSON code
  const currentLLMConfig = useMemo(() => {
    try {
      const parsed = JSON.parse(code);
      return parsed?.config?.llm_config || {};
    } catch {
      return {};
    }
  }, [code]);

  // Handle applying config updates from the helper panel
  const handleApplyConfig = (updates: Record<string, unknown>) => {
    try {
      const parsed = JSON.parse(code);
      if (!parsed.config) {
        parsed.config = {};
      }
      if (!parsed.config.llm_config) {
        parsed.config.llm_config = {};
      }
      // Merge updates into llm_config
      parsed.config.llm_config = {
        ...parsed.config.llm_config,
        ...updates,
      };
      setCode(JSON.stringify(parsed, null, 2));
    } catch {
      // If JSON is invalid, can't apply updates
      console.error('Cannot apply config updates to invalid JSON');
    }
  };

  // Handle MCP server toggle
  const handleMCPServerToggle = async (serverId: number, checked: boolean) => {
    if (!agentId) return;

    const currentIds = agentMCPServers?.map((s) => s.id) || [];
    let newIds: number[];

    if (checked) {
      newIds = [...currentIds, serverId];
    } else {
      newIds = currentIds.filter((id) => id !== serverId);
    }

    try {
      await assignMCPServers.mutateAsync(newIds);
    } catch (err) {
      console.error('Failed to update MCP server assignment:', err);
    }
  };

  const isPending = createAgent.isPending || updateAgent.isPending;

  // Parse current agent name from code for display
  let currentAgentName = 'New Agent';
  try {
    const parsed = JSON.parse(code);
    if (parsed.name) currentAgentName = parsed.name;
  } catch {
    // ignore
  }

  if (isLoadingAgent && isEditing) {
    return (
      <div className="h-[calc(100vh-8rem)] flex items-center justify-center">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <Code className="h-6 w-6 text-primary" />
          <div>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              {currentAgentName}
              {hasUnsavedChanges && (
                <Badge variant="outline" className="text-yellow-600">
                  Unsaved
                </Badge>
              )}
            </h1>
            <p className="text-sm text-muted-foreground">
              {isEditing ? 'Edit agent configuration' : 'Create a new agent'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleCancel}>
            <X className="mr-2 h-4 w-4" />
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={isPending || !!validationError}>
            {isPending ? (
              <Spinner className="mr-2 h-4 w-4" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            {isEditing ? 'Save' : 'Create'}
          </Button>
        </div>
      </div>

      {/* Error alerts */}
      {(error || validationError) && (
        <Alert variant="destructive" className="shrink-0">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error || validationError}</AlertDescription>
        </Alert>
      )}

      {/* Main content - split view */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-4 min-h-0">
        {/* Left side - Code Editor */}
        <div className="flex flex-col min-h-0 border rounded-lg overflow-hidden">
          {/* Editor header */}
          <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/30 shrink-0">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Code className="h-4 w-4" />
              Configuration
            </div>
            <Button variant="ghost" size="sm" onClick={handleFormatCode}>
              Format
            </Button>
          </div>

          {/* Help text */}
          <div className="px-4 py-2 border-b bg-muted/20 text-xs font-mono text-muted-foreground whitespace-pre overflow-x-auto shrink-0">
            {getHelpText()}
          </div>

          {/* Monaco Editor */}
          <div className="flex-1 min-h-0">
            <Editor
              height="100%"
              defaultLanguage="json"
              value={code}
              onChange={(value) => setCode(value || '')}
              onMount={handleEditorMount}
              theme={getMonacoTheme()}
              options={{
                minimap: { enabled: false },
                fontSize: 13,
                fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                wordWrap: 'on',
                automaticLayout: true,
                tabSize: 2,
                folding: true,
                bracketPairColorization: { enabled: true },
                guides: {
                  bracketPairs: true,
                  indentation: true,
                },
              }}
            />
          </div>
        </div>

        {/* Right side - Model Settings + Test Chat */}
        <div className="flex flex-col min-h-0 gap-4">
          {/* Model Parameter Helper - collapsible */}
          <div className="shrink-0">
            <ModelParameterHelper
              providers={providers}
              currentConfig={currentLLMConfig}
              onApply={handleApplyConfig}
              defaultExpanded={true}
            />
          </div>

          {/* MCP Servers Panel - collapsible */}
          {mcpServers.length > 0 && isEditing && agentId && (
            <div className="shrink-0 border rounded-lg">
              <button
                onClick={() => setMcpExpanded(!mcpExpanded)}
                className="w-full flex items-center justify-between px-4 py-2 text-sm font-medium hover:bg-muted/50"
              >
                <div className="flex items-center gap-2">
                  <Server className="h-4 w-4" />
                  MCP Servers
                  {agentMCPServers && agentMCPServers.length > 0 && (
                    <Badge variant="outline" className="text-xs">
                      {agentMCPServers.length} assigned
                    </Badge>
                  )}
                </div>
                {mcpExpanded ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
              </button>
              {mcpExpanded && (
                <div className="px-4 pb-3 space-y-2">
                  <p className="text-xs text-muted-foreground mb-2">
                    Select MCP servers to provide additional tools for this agent:
                  </p>
                  {mcpServers.map((server) => {
                    const isAssigned = agentMCPServers?.some((s) => s.id === server.id);
                    return (
                      <label
                        key={server.id}
                        className="flex items-center gap-2 text-sm cursor-pointer hover:bg-muted/30 p-1 rounded"
                      >
                        <Checkbox
                          checked={isAssigned}
                          onCheckedChange={(checked) =>
                            handleMCPServerToggle(server.id, checked === true)
                          }
                          disabled={assignMCPServers.isPending}
                        />
                        <span className="flex-1">{server.name}</span>
                        <Badge variant="outline" className="text-xs">
                          {server.transport_type}
                        </Badge>
                        {server.cached_tools_count > 0 && (
                          <span className="text-xs text-muted-foreground">
                            {server.cached_tools_count} tools
                          </span>
                        )}
                      </label>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Test Chat */}
          <div className="flex flex-col flex-1 min-h-0 border rounded-lg overflow-hidden">
            {/* Chat header */}
            <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/30 shrink-0">
              <div className="flex items-center gap-2 text-sm font-medium">
                <Play className="h-4 w-4" />
                Test Chat
                {sessionId && (
                  <Badge variant="outline" className="text-xs">
                    Session #{sessionId}
                  </Badge>
                )}
              </div>
              <Button variant="ghost" size="sm" onClick={handleNewSession}>
                <RotateCcw className="h-3 w-3 mr-1" />
                Reset
              </Button>
            </div>

            {!isEditing || !agentId ? (
              <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm p-4 text-center">
                <div>
                  <Bot className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>Save the agent first to enable testing.</p>
                  <p className="text-xs mt-1">
                    The test chat will appear here after you create the agent.
                  </p>
                </div>
              </div>
            ) : (
            <>
              {/* Chat messages */}
              <ScrollArea className="flex-1 p-3">
                {messages.length === 0 && !chatError ? (
                  <div className="h-full flex items-center justify-center text-muted-foreground text-sm text-center">
                    <div>
                      <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      <p>Send a message to test your agent.</p>
                      {hasUnsavedChanges && (
                        <p className="text-xs text-yellow-600 mt-2">
                          Save changes to test the latest config.
                        </p>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {messages.map((msg) => (
                      <MessageBubble key={msg.id} message={msg} />
                    ))}
                    {invokeAgent.isPending && (
                      <div className="flex gap-2">
                        <div className="h-7 w-7 rounded-full flex items-center justify-center bg-muted shrink-0">
                          <Bot className="h-3 w-3" />
                        </div>
                        <div className="bg-muted rounded-lg px-3 py-2">
                          <Spinner className="h-4 w-4" />
                        </div>
                      </div>
                    )}
                    <div ref={messagesEndRef} />
                  </div>
                )}
              </ScrollArea>

              {/* Trace steps (collapsible) */}
              {traceSteps.length > 0 && (
                <div className="border-t shrink-0">
                  <details className="group">
                    <summary className="px-3 py-2 cursor-pointer flex items-center gap-2 text-xs font-medium text-muted-foreground hover:text-foreground">
                      <GitBranch className="h-3 w-3" />
                      Execution Trace ({traceSteps.length} steps)
                    </summary>
                    <div className="px-3 pb-2 space-y-2 max-h-32 overflow-y-auto">
                      {traceSteps.slice(-5).map((step, index) => (
                        <TraceStepItem key={`${step.id}-${index}`} step={step} />
                      ))}
                    </div>
                  </details>
                </div>
              )}

              {/* Chat error */}
              {chatError && (
                <div className="px-3 py-2 border-t shrink-0">
                  <Alert variant="destructive" className="py-2">
                    <AlertDescription className="text-xs">{chatError}</AlertDescription>
                  </Alert>
                </div>
              )}

              {/* Chat input */}
              <div className="p-3 border-t shrink-0">
                <div className="flex gap-2 items-end">
                  <Textarea
                    ref={inputRef}
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Type a message... (Shift+Enter for new line)"
                    disabled={invokeAgent.isPending}
                    className="text-sm min-h-[36px] max-h-[120px] resize-none"
                    rows={1}
                  />
                  <Button
                    size="sm"
                    onClick={handleSendMessage}
                    disabled={!inputValue.trim() || invokeAgent.isPending}
                    className="shrink-0 h-[36px]"
                  >
                    <Send className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
