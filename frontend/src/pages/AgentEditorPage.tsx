import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import ReactMarkdown from 'react-markdown';
import {
  Button,
  Input,
  Textarea,
  Badge,
  Spinner,
  Alert,
  AlertDescription,
  ScrollArea,
  Checkbox,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui';
import { ChatInputWithAttachments, Attachment } from '@/components/chat';
import {
  Save,
  X,
  Play,
  Bot,
  User,
  AlertCircle,
  MessageSquare,
  RotateCcw,
  Settings,
  ChevronDown,
  ChevronRight,
  Info,
  Eye,
  Wifi,
  WifiOff,
  Copy,
  Lock,
  Paperclip,
} from 'lucide-react';
import {
  useAgent,
  useCreateAgent,
  useUpdateAgent,
  useCloneAgent,
  useLLMProviders,
  useTools,
  useMCPServers,
  useAgentMCPServers,
  useAssignAgentMCPServers,
  useInvokeAgent,
  useAgentTypes,
  useAgentWebSocket,
  getErrorMessage,
} from '@/api/hooks';
import type { ToolCallPayload, ToolResultPayload, FinalAnswerPayload, ErrorPayload } from '@/api/hooks/useAgentWebSocket';
import { AgentCreateRequest, TraceStep, ContentBlock } from '@/api/types';
import { ContentBlockRenderer } from '@/components/chat/content-blocks';
import { SessionDetailDialog } from '@/components/sessions';
import { PromptSelector } from '@/components/prompts';
import { AgentPermissionsPanel } from '@/components/agents/AgentPermissionsPanel';

// Form schema
const agentFormSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100, 'Name must be less than 100 characters'),
  description: z.string().max(2000, 'Description must be less than 2000 characters').optional(),
  agent_type_id: z.number().min(1, 'Agent type is required'),
  tags: z.array(z.string()).default([]),
  provider_id: z.number().nullable(),
  model: z.string().min(1, 'Model is required'),
  temperature: z.number().min(0).max(2).default(0.7),
  max_tokens: z.number().min(1).max(128000).default(4096),
  timeout_seconds: z.number().min(1).max(600).optional(),
  reflection_enabled: z.boolean().default(false),
  reflection_depth: z.number().min(1).max(10).default(2),
  iteration_limit: z.number().min(1).max(20).default(5),
  memory_type: z.string().default('buffer'),
  context_window: z.number().min(1).max(100).default(10),
  tool_ids: z.array(z.number()).default([]),
  // Prompt configuration
  prompt_id: z.number().nullable().default(null),
  prompt_variables: z.record(z.string()).default({}),
  use_prompt_library: z.boolean().default(false),
  system_prompt: z.string().max(10000, 'System prompt must be less than 10000 characters').optional(),
});

type AgentFormData = z.infer<typeof agentFormSchema>;

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  attachments?: Attachment[];
  content_blocks?: ContentBlock[];
}

// Field descriptions for tooltips
const FIELD_TOOLTIPS = {
  name: "A unique, descriptive name for your agent. This will be displayed in the agent list and used to identify the agent.",
  description: "A detailed description of what this agent does, its purpose, and any specific capabilities or limitations.",
  agent_type: "The execution strategy that determines how the agent processes requests. ReAct agents use reasoning and tool-calling, while custom types can have user-defined behavior.",
  tags: "Keywords or labels to help organize and filter agents. Useful for categorizing agents by purpose, domain, or project.",
  provider: "The LLM service provider (e.g., OpenAI, Anthropic) that will power this agent. You must configure a provider in Settings first.",
  model: "The specific model to use from your provider (e.g., gpt-4o, claude-3-opus). Different models have different capabilities and costs.",
  temperature: "Controls response randomness. 0 = deterministic and focused, 2 = highly creative and varied. Recommended: 0.7 for balanced responses.",
  max_tokens: "Maximum number of tokens the model can generate in a single response. Higher values allow longer responses but increase costs.",
  timeout: "Maximum time (in seconds) the agent can run before being stopped. Prevents runaway executions and controls costs.",
  reflection_enabled: "When enabled, the agent will review and potentially revise its responses for accuracy and quality.",
  reflection_depth: "Number of levels of self-reflection the agent performs. Higher values may improve quality but increase latency.",
  iteration_limit: "Maximum number of reflection cycles. Prevents infinite loops in the reflection process.",
  memory_type: "How the agent stores conversation context. Buffer keeps recent messages, Summary compresses history, Vector uses semantic search.",
  context_window: "Number of previous messages the agent can access. Larger windows provide more context but use more tokens.",
  tools: "External capabilities the agent can use to accomplish tasks. Select tools that match the agent's intended purpose.",
  mcp_servers: "Model Context Protocol servers that provide additional tools and capabilities to the agent.",
  system_prompt: "Instructions that define the agent's personality, behavior, and constraints. This shapes how the agent responds to all requests.",
};

// Info icon with tooltip component
function FieldInfo({ tooltip }: { tooltip: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button type="button" className="ml-1 text-muted-foreground hover:text-foreground inline-flex">
          <Info className="h-3.5 w-3.5" />
        </button>
      </TooltipTrigger>
      <TooltipContent side="right" className="max-w-xs text-xs">
        {tooltip}
      </TooltipContent>
    </Tooltip>
  );
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
        {/* Attachments */}
        {message.attachments && message.attachments.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-1.5">
            {message.attachments.map((attachment) => (
              <Badge
                key={attachment.id}
                variant={isUser ? 'secondary' : 'outline'}
                className="text-xs flex items-center gap-1 py-0"
              >
                <Paperclip className="h-2.5 w-2.5" />
                {attachment.name}
              </Badge>
            ))}
          </div>
        )}
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>
        {/* Content blocks (images, audio, video, files) */}
        {message.content_blocks && message.content_blocks.length > 0 && (
          <div className="mt-2 space-y-2">
            {message.content_blocks.map((block, index) => (
              <ContentBlockRenderer key={index} block={block} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function AgentEditorPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const isEditing = id !== undefined && id !== 'new';
  const agentId = isEditing ? parseInt(id) : null;

  // Form state
  const [activeTab, setActiveTab] = useState('basic');
  const [tagInput, setTagInput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Advanced settings expanded state
  const [executionExpanded, setExecutionExpanded] = useState(false);
  const [reflectionExpanded, setReflectionExpanded] = useState(false);
  const [memoryExpanded, setMemoryExpanded] = useState(false);

  // Chat state
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [traceSteps, setTraceSteps] = useState<TraceStep[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);
  const [sessionDetailOpen, setSessionDetailOpen] = useState(false);
  const [streamingEnabled, setStreamingEnabled] = useState(true);
  const [pendingAssistantMessage, setPendingAssistantMessage] = useState<string>('');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Data hooks
  const { data: agent, isLoading: isLoadingAgent } = useAgent(agentId ?? undefined);
  const { data: providersData } = useLLMProviders({ pageSize: 100 });
  const { data: toolsData } = useTools({ pageSize: 100 });
  const { data: mcpServersData } = useMCPServers({ pageSize: 100 });
  const { data: agentMCPServers } = useAgentMCPServers(agentId ?? undefined);
  const { data: agentTypesData } = useAgentTypes({ isActive: true });

  const createAgent = useCreateAgent();
  const updateAgent = useUpdateAgent(agentId ?? 0);
  const cloneAgent = useCloneAgent();
  const invokeAgent = useInvokeAgent(agentId ?? 0);
  const assignMCPServers = useAssignAgentMCPServers(agentId ?? 0);

  // Check if agent is built-in (read-only)
  const isBuiltIn = agent?.is_builtin ?? false;

  // WebSocket streaming callbacks
  const handleToolCall = (payload: ToolCallPayload, wsSessionId: number) => {
    setSessionId(wsSessionId);
    setPendingAssistantMessage(`Using tool: ${payload.tool_name}...`);
    const step: TraceStep = {
      id: Date.now(),
      session_id: wsSessionId,
      step_number: payload.step_number,
      step_type: 'tool_call',
      tool_name: payload.tool_name,
      tool_input: payload.tool_input,
      tool_output: null,
      latency_ms: null,
      content: `Calling ${payload.tool_name}`,
      created_at: new Date().toISOString(),
    };
    setTraceSteps((prev) => [...prev, step]);
  };

  const handleToolResult = (payload: ToolResultPayload, wsSessionId: number) => {
    setPendingAssistantMessage('Processing results...');
    const step: TraceStep = {
      id: Date.now(),
      session_id: wsSessionId,
      step_number: payload.step_number,
      step_type: 'tool_result',
      tool_name: payload.tool_name,
      tool_input: null,
      tool_output: typeof payload.tool_output === 'object' ? payload.tool_output as Record<string, unknown> : { result: payload.tool_output },
      latency_ms: payload.latency_ms,
      content: `Result from ${payload.tool_name}`,
      created_at: new Date().toISOString(),
    };
    setTraceSteps((prev) => [...prev, step]);
  };

  const handleFinalAnswer = (payload: FinalAnswerPayload, _wsSessionId: number) => {
    const assistantMessage: ChatMessage = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: payload.output,
      timestamp: new Date(),
      content_blocks: payload.content_blocks,
    };
    setMessages((prev) => [...prev, assistantMessage]);
    setPendingAssistantMessage('');
  };

  const handleStreamError = (payload: ErrorPayload) => {
    setChatError(payload.error);
    setPendingAssistantMessage('');
  };

  const handleSessionStart = (_payload: unknown, wsSessionId: number) => {
    setSessionId(wsSessionId);
    setPendingAssistantMessage('Thinking...');
  };

  // WebSocket hook for streaming
  const {
    isConnected,
    isExecuting,
    connect: wsConnect,
    disconnect: wsDisconnect,
    invoke: wsInvoke,
  } = useAgentWebSocket({
    agentId: agentId ?? 0,
    onSessionStart: handleSessionStart,
    onToolCall: handleToolCall,
    onToolResult: handleToolResult,
    onFinalAnswer: handleFinalAnswer,
    onError: handleStreamError,
    autoReconnect: true,
  });

  // Auto-connect WebSocket when streaming is enabled and agent is saved
  useEffect(() => {
    if (streamingEnabled && isEditing && agentId) {
      wsConnect();
    } else {
      wsDisconnect();
    }
    return () => {
      wsDisconnect();
    };
  }, [streamingEnabled, isEditing, agentId]); // eslint-disable-line react-hooks/exhaustive-deps

  const providers = providersData?.providers || [];
  const tools = toolsData?.tools || [];
  const mcpServers = mcpServersData?.servers || [];
  const agentTypes = agentTypesData?.agent_types || [];

  // Get default agent type (first ReAct builtin type)
  const defaultAgentTypeId = agentTypes.find(
    at => at.execution_strategy === 'react' && at.is_builtin
  )?.id ?? agentTypes[0]?.id ?? 0;

  // Get default provider
  const defaultProviderId = providers[0]?.id ?? null;

  const form = useForm<AgentFormData>({
    resolver: zodResolver(agentFormSchema),
    defaultValues: {
      name: 'My Agent',
      description: '',
      agent_type_id: 0,
      tags: [],
      provider_id: null,
      model: 'gpt-4',
      temperature: 0.7,
      max_tokens: 4096,
      timeout_seconds: 120,
      reflection_enabled: false,
      reflection_depth: 2,
      iteration_limit: 5,
      memory_type: 'buffer',
      context_window: 10,
      tool_ids: [],
      prompt_id: null,
      prompt_variables: {},
      use_prompt_library: false,
      system_prompt: 'You are a helpful AI assistant.',
    },
  });

  // Set defaults when data loads
  useEffect(() => {
    if (!isEditing && defaultAgentTypeId && form.getValues('agent_type_id') === 0) {
      form.setValue('agent_type_id', defaultAgentTypeId);
    }
    if (!isEditing && defaultProviderId && form.getValues('provider_id') === null) {
      form.setValue('provider_id', defaultProviderId);
    }
  }, [isEditing, defaultAgentTypeId, defaultProviderId, form]);

  // Apply agent type defaults when agent_type_id changes (for new agents only)
  const watchedAgentTypeId = form.watch('agent_type_id');
  useEffect(() => {
    // Only apply defaults for new agents, not when editing
    if (isEditing || !watchedAgentTypeId || watchedAgentTypeId === 0) return;

    const selectedAgentType = agentTypes.find(at => at.id === watchedAgentTypeId);
    if (!selectedAgentType) return;

    // Apply recommended tools (or clear if agent type has none)
    if (selectedAgentType.recommended_tools && selectedAgentType.recommended_tools.length > 0) {
      const toolIds = selectedAgentType.recommended_tools.map(t => t.id);
      form.setValue('tool_ids', toolIds);
    } else {
      // Clear tools if this agent type has no recommendations (e.g., Conversational)
      form.setValue('tool_ids', []);
    }

    // Apply system prompt template
    if (selectedAgentType.system_prompt_template) {
      form.setValue('system_prompt', selectedAgentType.system_prompt_template);
      form.setValue('use_prompt_library', false);
    }

    // Apply default LLM config
    if (selectedAgentType.default_llm_config) {
      const llmConfig = selectedAgentType.default_llm_config;
      if (llmConfig.model) {
        form.setValue('model', llmConfig.model);
      }
      if (llmConfig.temperature !== undefined) {
        form.setValue('temperature', llmConfig.temperature);
      }
      if (llmConfig.max_tokens !== undefined) {
        form.setValue('max_tokens', llmConfig.max_tokens);
      }
    }

    // Apply default memory config
    if (selectedAgentType.default_memory_config) {
      const memConfig = selectedAgentType.default_memory_config;
      if (memConfig.type) {
        form.setValue('memory_type', memConfig.type);
      }
      if (memConfig.context_window !== undefined) {
        form.setValue('context_window', memConfig.context_window);
      }
    }
  }, [watchedAgentTypeId, agentTypes, isEditing, form]);

  // Load agent data when editing
  useEffect(() => {
    if (agent && isEditing && providersData) {
      const providerType = agent.current_version?.config.llm_config.provider;
      const matchingProvider = providersData.providers.find(p => p.provider_type === providerType);
      const config = agent.current_version?.config;

      const hasPromptId = config?.prompt_id != null;
      form.reset({
        name: agent.name,
        description: agent.description || '',
        agent_type_id: agent.agent_type_id,
        tags: agent.tags || [],
        provider_id: matchingProvider?.id ?? null,
        model: config?.llm_config.model || 'gpt-4',
        temperature: config?.llm_config.temperature ?? 0.7,
        max_tokens: config?.llm_config.max_tokens ?? 4096,
        timeout_seconds: config?.timeout_seconds ?? 120,
        reflection_enabled: config?.reflection_config?.enabled ?? false,
        reflection_depth: config?.reflection_config?.depth ?? 2,
        iteration_limit: config?.reflection_config?.iteration_limit ?? 5,
        memory_type: config?.memory_config?.type ?? 'buffer',
        context_window: config?.memory_config?.context_window ?? 10,
        tool_ids: config?.tool_ids || [],
        prompt_id: config?.prompt_id ?? null,
        prompt_variables: config?.prompt_variables ?? {},
        use_prompt_library: hasPromptId,
        system_prompt: config?.system_prompt || '',
      });
      setHasUnsavedChanges(false);
    }
  }, [agent, isEditing, form, providersData]);

  // Track unsaved changes
  useEffect(() => {
    const subscription = form.watch(() => {
      if (!isLoadingAgent) {
        setHasUnsavedChanges(true);
      }
    });
    return () => subscription.unsubscribe();
  }, [form, isLoadingAgent]);

  // Scroll chat to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleAddTag = () => {
    const tag = tagInput.trim();
    if (tag && !form.getValues('tags').includes(tag)) {
      form.setValue('tags', [...form.getValues('tags'), tag]);
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    form.setValue(
      'tags',
      form.getValues('tags').filter((tag) => tag !== tagToRemove)
    );
  };

  const handleToolToggle = (toolId: number) => {
    const currentTools = form.getValues('tool_ids');
    if (currentTools.includes(toolId)) {
      form.setValue('tool_ids', currentTools.filter((id) => id !== toolId));
    } else {
      form.setValue('tool_ids', [...currentTools, toolId]);
    }
  };

  const onSubmit = async (data: AgentFormData) => {
    setError(null);

    const selectedProvider = providers.find(p => p.id === data.provider_id);
    const providerType = selectedProvider?.provider_type || 'openai';

    const payload: AgentCreateRequest = {
      name: data.name,
      description: data.description || undefined,
      agent_type_id: data.agent_type_id,
      tags: data.tags,
      config: {
        llm_config: {
          provider: providerType,
          provider_id: data.provider_id || 0,
          model: data.model,
          temperature: data.temperature,
          max_tokens: data.max_tokens,
        },
        tool_ids: data.tool_ids,
        prompt_id: data.use_prompt_library ? data.prompt_id : null,
        prompt_variables: data.use_prompt_library ? data.prompt_variables : undefined,
        system_prompt: data.use_prompt_library ? null : (data.system_prompt || null),
        timeout_seconds: data.timeout_seconds,
        reflection_config: {
          enabled: data.reflection_enabled,
          depth: data.reflection_depth,
          iteration_limit: data.iteration_limit,
        },
        memory_config: {
          type: data.memory_type,
          context_window: data.context_window,
        },
      },
    };

    try {
      if (isEditing && agentId) {
        await updateAgent.mutateAsync({
          name: payload.name,
          description: payload.description,
          agent_type_id: payload.agent_type_id,
          tags: payload.tags,
          config: payload.config,
        });
      } else {
        const created = await createAgent.mutateAsync(payload);
        navigate(`/agents/${created.id}/edit`, { replace: true });
      }
      setHasUnsavedChanges(false);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const handleCancel = () => {
    navigate('/agents');
  };

  // Chat handlers
  const handleSendMessage = async (message: string, attachments: Attachment[]) => {
    if ((!message.trim() && attachments.length === 0) || !agentId) return;

    // Build message content including attachment context
    let fullContent = message.trim();
    if (attachments.length > 0) {
      const attachmentContext = attachments
        .filter(a => a.content && (a.type === 'text' || a.type === 'code'))
        .map(a => `\n\n--- Attached file: ${a.name} ---\n${a.content}`)
        .join('');
      if (attachmentContext) {
        fullContent = `${fullContent}${attachmentContext}`;
      }
    }

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: message.trim(),
      timestamp: new Date(),
      attachments: attachments.length > 0 ? attachments : undefined,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setChatError(null);

    // Use WebSocket streaming if enabled and connected
    if (streamingEnabled && isConnected) {
      // Convert attachments to WebSocket format
      const wsAttachments = attachments.map(a => ({
        name: a.name,
        type: a.type,
        mimeType: a.mimeType,
        content: a.content,
      }));
      wsInvoke(fullContent, sessionId || undefined, wsAttachments.length > 0 ? wsAttachments : undefined);
      return;
    }

    // Fallback to REST API
    try {
      abortControllerRef.current = new AbortController();
      const response = await invokeAgent.mutateAsync({
        message: fullContent,
        session_id: sessionId || undefined,
        attachments: attachments.map(a => ({
          name: a.name,
          type: a.type,
          mimeType: a.mimeType,
          content: a.content,
        })),
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
      if ((err as Error).name !== 'AbortError') {
        setChatError(getErrorMessage(err));
      }
    } finally {
      abortControllerRef.current = null;
    }
  };

  const handleStopExecution = () => {
    // Stop WebSocket streaming
    if (streamingEnabled && isExecuting) {
      wsDisconnect();
      // Reconnect after a brief delay
      setTimeout(() => {
        if (streamingEnabled && isEditing && agentId) {
          wsConnect();
        }
      }, 500);
      setPendingAssistantMessage('');
      setChatError('Execution stopped by user');
      return;
    }

    // Abort REST request (limited effectiveness - server continues)
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setChatError('Request cancelled (server may continue processing)');
    }
  };

  const handleNewSession = () => {
    setMessages([]);
    setTraceSteps([]);
    setSessionId(null);
    setChatError(null);
    setPendingAssistantMessage('');
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
  const isChatBusy = isExecuting || invokeAgent.isPending;
  const currentAgentName = form.watch('name') || 'New Agent';

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
          <Settings className="h-6 w-6 text-primary" />
          <div>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              {currentAgentName}
              {isBuiltIn && (
                <Badge variant="secondary" className="text-xs">
                  <Lock className="mr-1 h-3 w-3" />
                  Built-in
                </Badge>
              )}
              {hasUnsavedChanges && !isBuiltIn && (
                <Badge variant="outline" className="text-yellow-600">
                  Unsaved
                </Badge>
              )}
            </h1>
            <p className="text-sm text-muted-foreground">
              {isBuiltIn
                ? 'View built-in agent configuration (read-only)'
                : isEditing
                ? 'Edit agent configuration'
                : 'Create a new agent'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleCancel}>
            <X className="mr-2 h-4 w-4" />
            {isBuiltIn ? 'Back' : 'Cancel'}
          </Button>
          {isBuiltIn ? (
            <Button
              onClick={async () => {
                try {
                  const cloned = await cloneAgent.mutateAsync(agentId!);
                  navigate(`/agents/${cloned.id}/edit`);
                } catch (err) {
                  setError(getErrorMessage(err));
                }
              }}
              disabled={cloneAgent.isPending}
            >
              {cloneAgent.isPending ? (
                <Spinner className="mr-2 h-4 w-4" />
              ) : (
                <Copy className="mr-2 h-4 w-4" />
              )}
              Clone to Edit
            </Button>
          ) : (
            <Button onClick={form.handleSubmit(onSubmit)} disabled={isPending}>
              {isPending ? (
                <Spinner className="mr-2 h-4 w-4" />
              ) : (
                <Save className="mr-2 h-4 w-4" />
              )}
              {isEditing ? 'Save' : 'Create'}
            </Button>
          )}
        </div>
      </div>

      {/* Error alerts */}
      {error && (
        <Alert variant="destructive" className="shrink-0">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Built-in agent read-only notice */}
      {isBuiltIn && (
        <Alert className="shrink-0 border-blue-200 bg-blue-50 dark:border-blue-900 dark:bg-blue-950">
          <Lock className="h-4 w-4 text-blue-600 dark:text-blue-400" />
          <AlertDescription className="text-blue-800 dark:text-blue-200">
            This is a built-in agent and cannot be modified. Click "Clone to Edit" to create your own editable copy.
          </AlertDescription>
        </Alert>
      )}

      {/* Main content - split view */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-4 min-h-0">
        {/* Left side - Form */}
        <div className="flex flex-col min-h-0 border rounded-lg overflow-hidden">
          <TooltipProvider delayDuration={300}>
            <Form {...form}>
              <form className="flex flex-col flex-1 overflow-hidden">
              <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden">
                <TabsList className="grid w-full grid-cols-4 mx-4 mt-4 mb-2" style={{ width: 'calc(100% - 2rem)' }}>
                  <TabsTrigger value="basic">Basic Info</TabsTrigger>
                  <TabsTrigger value="config">Configuration</TabsTrigger>
                  <TabsTrigger value="tools">Tools & Prompts</TabsTrigger>
                  <TabsTrigger value="permissions">Permissions</TabsTrigger>
                </TabsList>

                <ScrollArea className="flex-1 px-4">
                  {/* Basic Info Tab */}
                  <TabsContent value="basic" className="space-y-4 mt-2 pb-4">
                    <FormField
                      control={form.control}
                      name="name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="flex items-center">
                            Name
                            <FieldInfo tooltip={FIELD_TOOLTIPS.name} />
                          </FormLabel>
                          <FormControl>
                            <Input placeholder="My Agent" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="description"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="flex items-center">
                            Description
                            <FieldInfo tooltip={FIELD_TOOLTIPS.description} />
                          </FormLabel>
                          <FormControl>
                            <Textarea
                              placeholder="Describe what this agent does..."
                              className="resize-none"
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="agent_type_id"
                      render={({ field }) => {
                        const selectedType = agentTypes.find(at => at.id === field.value);
                        return (
                          <FormItem>
                            <FormLabel className="flex items-center">
                              Agent Type
                              <FieldInfo tooltip={FIELD_TOOLTIPS.agent_type} />
                            </FormLabel>
                            <Select
                              onValueChange={(value) => field.onChange(parseInt(value))}
                              value={field.value?.toString() || ''}
                            >
                              <FormControl>
                                <SelectTrigger>
                                  <SelectValue placeholder="Select agent type" />
                                </SelectTrigger>
                              </FormControl>
                              <SelectContent>
                                {agentTypes.map((agentType) => (
                                  <SelectItem key={agentType.id} value={agentType.id.toString()}>
                                    {agentType.name}
                                    {agentType.is_builtin && ' (Built-in)'}
                                    {!agentType.is_builtin && agentType.strategy_type === 'custom_code' && ' (Custom)'}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            <FormDescription>
                              {selectedType?.description || 'Select an agent type'}
                            </FormDescription>
                            <FormMessage />
                          </FormItem>
                        );
                      }}
                    />

                    <FormField
                      control={form.control}
                      name="tags"
                      render={() => (
                        <FormItem>
                          <FormLabel className="flex items-center">
                            Tags
                            <FieldInfo tooltip={FIELD_TOOLTIPS.tags} />
                          </FormLabel>
                          <div className="flex gap-2">
                            <Input
                              placeholder="Add a tag..."
                              value={tagInput}
                              onChange={(e) => setTagInput(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                  e.preventDefault();
                                  handleAddTag();
                                }
                              }}
                            />
                            <Button type="button" variant="secondary" onClick={handleAddTag}>
                              Add
                            </Button>
                          </div>
                          <div className="flex flex-wrap gap-2 mt-2">
                            {form.watch('tags').map((tag) => (
                              <Badge key={tag} variant="secondary" className="gap-1">
                                {tag}
                                <button
                                  type="button"
                                  onClick={() => handleRemoveTag(tag)}
                                  className="ml-1 hover:text-destructive"
                                >
                                  <X className="h-3 w-3" />
                                </button>
                              </Badge>
                            ))}
                          </div>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </TabsContent>

                  {/* Configuration Tab */}
                  <TabsContent value="config" className="space-y-4 mt-2 pb-4">
                    <FormField
                      control={form.control}
                      name="provider_id"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="flex items-center">
                            LLM Provider
                            <FieldInfo tooltip={FIELD_TOOLTIPS.provider} />
                          </FormLabel>
                          <Select
                            onValueChange={(value) => field.onChange(value ? parseInt(value) : null)}
                            value={field.value?.toString() || ''}
                          >
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue placeholder="Select a provider" />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              {providers.length === 0 ? (
                                <SelectItem value="none" disabled>
                                  No providers configured
                                </SelectItem>
                              ) : (
                                providers.map((provider) => (
                                  <SelectItem key={provider.id} value={provider.id.toString()}>
                                    {provider.name} ({provider.provider_type})
                                  </SelectItem>
                                ))
                              )}
                            </SelectContent>
                          </Select>
                          {providers.length === 0 && (
                            <FormDescription className="text-yellow-600">
                              Configure an LLM provider in Settings first
                            </FormDescription>
                          )}
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="model"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="flex items-center">
                            Model
                            <FieldInfo tooltip={FIELD_TOOLTIPS.model} />
                          </FormLabel>
                          <FormControl>
                            <Input placeholder="gpt-4" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="temperature"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="flex items-center">
                            Temperature: {field.value}
                            <FieldInfo tooltip={FIELD_TOOLTIPS.temperature} />
                          </FormLabel>
                          <FormControl>
                            <Input
                              type="range"
                              min="0"
                              max="2"
                              step="0.1"
                              {...field}
                              onChange={(e) => field.onChange(parseFloat(e.target.value))}
                              className="cursor-pointer"
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="max_tokens"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="flex items-center">
                            Max Tokens
                            <FieldInfo tooltip={FIELD_TOOLTIPS.max_tokens} />
                          </FormLabel>
                          <FormControl>
                            <Input
                              type="number"
                              min="1"
                              max="128000"
                              {...field}
                              onChange={(e) => field.onChange(parseInt(e.target.value) || 4096)}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    {/* Execution Settings */}
                    <div className="border rounded-lg">
                      <button
                        type="button"
                        onClick={() => setExecutionExpanded(!executionExpanded)}
                        className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium hover:bg-muted/50"
                      >
                        <span>Execution Settings</span>
                        {executionExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                      </button>
                      {executionExpanded && (
                        <div className="px-3 pb-3 space-y-3">
                          <FormField
                            control={form.control}
                            name="timeout_seconds"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel className="flex items-center">
                                  Timeout (seconds)
                                  <FieldInfo tooltip={FIELD_TOOLTIPS.timeout} />
                                </FormLabel>
                                <FormControl>
                                  <Input
                                    type="number"
                                    min="1"
                                    max="600"
                                    {...field}
                                    value={field.value || ''}
                                    onChange={(e) => field.onChange(parseInt(e.target.value) || undefined)}
                                  />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                        </div>
                      )}
                    </div>

                    {/* Reflection Settings */}
                    <div className="border rounded-lg">
                      <button
                        type="button"
                        onClick={() => setReflectionExpanded(!reflectionExpanded)}
                        className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium hover:bg-muted/50"
                      >
                        <span>Reflection Settings</span>
                        {reflectionExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                      </button>
                      {reflectionExpanded && (
                        <div className="px-3 pb-3 space-y-3">
                          <FormField
                            control={form.control}
                            name="reflection_enabled"
                            render={({ field }) => (
                              <FormItem className="flex flex-row items-center gap-2">
                                <FormControl>
                                  <Checkbox
                                    checked={field.value}
                                    onCheckedChange={field.onChange}
                                  />
                                </FormControl>
                                <FormLabel className="!mt-0 flex items-center">
                                  Enable Reflection
                                  <FieldInfo tooltip={FIELD_TOOLTIPS.reflection_enabled} />
                                </FormLabel>
                              </FormItem>
                            )}
                          />

                          {form.watch('reflection_enabled') && (
                            <>
                              <FormField
                                control={form.control}
                                name="reflection_depth"
                                render={({ field }) => (
                                  <FormItem>
                                    <FormLabel className="flex items-center">
                                      Reflection Depth
                                      <FieldInfo tooltip={FIELD_TOOLTIPS.reflection_depth} />
                                    </FormLabel>
                                    <FormControl>
                                      <Input
                                        type="number"
                                        min="1"
                                        max="10"
                                        {...field}
                                        onChange={(e) => field.onChange(parseInt(e.target.value) || 2)}
                                      />
                                    </FormControl>
                                    <FormMessage />
                                  </FormItem>
                                )}
                              />

                              <FormField
                                control={form.control}
                                name="iteration_limit"
                                render={({ field }) => (
                                  <FormItem>
                                    <FormLabel className="flex items-center">
                                      Iteration Limit
                                      <FieldInfo tooltip={FIELD_TOOLTIPS.iteration_limit} />
                                    </FormLabel>
                                    <FormControl>
                                      <Input
                                        type="number"
                                        min="1"
                                        max="20"
                                        {...field}
                                        onChange={(e) => field.onChange(parseInt(e.target.value) || 5)}
                                      />
                                    </FormControl>
                                    <FormMessage />
                                  </FormItem>
                                )}
                              />
                            </>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Memory Settings */}
                    <div className="border rounded-lg">
                      <button
                        type="button"
                        onClick={() => setMemoryExpanded(!memoryExpanded)}
                        className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium hover:bg-muted/50"
                      >
                        <span>Memory Settings</span>
                        {memoryExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                      </button>
                      {memoryExpanded && (
                        <div className="px-3 pb-3 space-y-3">
                          <FormField
                            control={form.control}
                            name="memory_type"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel className="flex items-center">
                                  Memory Type
                                  <FieldInfo tooltip={FIELD_TOOLTIPS.memory_type} />
                                </FormLabel>
                                <Select onValueChange={field.onChange} value={field.value}>
                                  <FormControl>
                                    <SelectTrigger>
                                      <SelectValue placeholder="Select memory type" />
                                    </SelectTrigger>
                                  </FormControl>
                                  <SelectContent>
                                    <SelectItem value="buffer">Buffer</SelectItem>
                                    <SelectItem value="summary">Summary</SelectItem>
                                    <SelectItem value="vector">Vector</SelectItem>
                                  </SelectContent>
                                </Select>
                                <FormMessage />
                              </FormItem>
                            )}
                          />

                          <FormField
                            control={form.control}
                            name="context_window"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel className="flex items-center">
                                  Context Window
                                  <FieldInfo tooltip={FIELD_TOOLTIPS.context_window} />
                                </FormLabel>
                                <FormControl>
                                  <Input
                                    type="number"
                                    min="1"
                                    max="100"
                                    {...field}
                                    onChange={(e) => field.onChange(parseInt(e.target.value) || 10)}
                                  />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                        </div>
                      )}
                    </div>
                  </TabsContent>

                  {/* Tools & Prompts Tab */}
                  <TabsContent value="tools" className="space-y-4 mt-2 pb-4">
                    <FormField
                      control={form.control}
                      name="tool_ids"
                      render={() => (
                        <FormItem>
                          <FormLabel className="flex items-center">
                            Tools
                            <FieldInfo tooltip={FIELD_TOOLTIPS.tools} />
                          </FormLabel>
                          <div className="border rounded-md p-4 space-y-2 max-h-48 overflow-y-auto">
                            {tools.length === 0 ? (
                              <p className="text-sm text-muted-foreground">
                                No tools available. Create tools first.
                              </p>
                            ) : (
                              tools.map((tool) => (
                                <div key={tool.id} className="flex items-center space-x-2">
                                  <Checkbox
                                    id={`tool-${tool.id}`}
                                    checked={form.watch('tool_ids').includes(tool.id)}
                                    onCheckedChange={() => handleToolToggle(tool.id)}
                                  />
                                  <label
                                    htmlFor={`tool-${tool.id}`}
                                    className="flex-1 text-sm cursor-pointer"
                                  >
                                    <span className="font-medium">{tool.name}</span>
                                    <span className="text-muted-foreground ml-2">
                                      ({tool.category})
                                    </span>
                                  </label>
                                </div>
                              ))
                            )}
                          </div>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    {/* MCP Servers */}
                    {mcpServers.length > 0 && isEditing && agentId && (
                      <div>
                        <FormLabel className="flex items-center">
                          MCP Servers
                          <FieldInfo tooltip={FIELD_TOOLTIPS.mcp_servers} />
                        </FormLabel>
                        <div className="border rounded-md p-4 space-y-2 max-h-48 overflow-y-auto">
                          {mcpServers.map((server) => {
                            const isAssigned = agentMCPServers?.some((s) => s.id === server.id);
                            return (
                              <div key={server.id} className="flex items-center space-x-2">
                                <Checkbox
                                  id={`mcp-${server.id}`}
                                  checked={isAssigned}
                                  onCheckedChange={(checked) =>
                                    handleMCPServerToggle(server.id, checked === true)
                                  }
                                  disabled={assignMCPServers.isPending}
                                />
                                <label
                                  htmlFor={`mcp-${server.id}`}
                                  className="flex-1 text-sm cursor-pointer"
                                >
                                  <span className="font-medium">{server.name}</span>
                                  <Badge variant="outline" className="ml-2 text-xs">
                                    {server.transport_type}
                                  </Badge>
                                  {server.cached_tools_count > 0 && (
                                    <span className="text-muted-foreground ml-2">
                                      ({server.cached_tools_count} tools)
                                    </span>
                                  )}
                                </label>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    <div className="space-y-2">
                      <FormLabel className="flex items-center">
                        System Prompt
                        <FieldInfo tooltip={FIELD_TOOLTIPS.system_prompt} />
                      </FormLabel>
                      <PromptSelector
                        selectedPromptId={form.watch('prompt_id')}
                        promptVariables={form.watch('prompt_variables')}
                        systemPromptOverride={form.watch('system_prompt') || ''}
                        usePromptLibrary={form.watch('use_prompt_library')}
                        onChange={(config) => {
                          form.setValue('prompt_id', config.prompt_id);
                          form.setValue('prompt_variables', config.prompt_variables);
                          form.setValue('system_prompt', config.system_prompt);
                          form.setValue('use_prompt_library', config.use_prompt_library);
                        }}
                      />
                    </div>
                  </TabsContent>

                  {/* Permissions Tab */}
                  <TabsContent value="permissions" className="space-y-4 mt-2 pb-4">
                    {isEditing && agentId ? (
                      <AgentPermissionsPanel
                        agentId={agentId}
                        isBuiltin={agent?.is_builtin}
                      />
                    ) : (
                      <div className="flex items-center justify-center py-8 text-muted-foreground text-sm">
                        Save the agent first to configure permissions.
                      </div>
                    )}
                  </TabsContent>
                </ScrollArea>
              </Tabs>
              </form>
            </Form>
          </TooltipProvider>
        </div>

        {/* Right side - Test Chat */}
        <div className="flex flex-col min-h-0 border rounded-lg overflow-hidden">
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
              {/* Streaming status */}
              {streamingEnabled && isEditing && (
                <Badge
                  variant={isConnected ? 'default' : 'secondary'}
                  className={`text-xs ${isConnected ? 'bg-green-600' : ''}`}
                >
                  {isConnected ? (
                    <><Wifi className="h-3 w-3 mr-1" /> Live</>
                  ) : (
                    <><WifiOff className="h-3 w-3 mr-1" /> Offline</>
                  )}
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-1">
              {/* Streaming toggle */}
              {isEditing && (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant={streamingEnabled ? 'default' : 'ghost'}
                        size="sm"
                        onClick={() => setStreamingEnabled(!streamingEnabled)}
                        className="h-7 px-2"
                      >
                        {streamingEnabled ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      {streamingEnabled ? 'Streaming enabled (click to disable)' : 'Streaming disabled (click to enable)'}
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
              <Button variant="ghost" size="sm" onClick={handleNewSession}>
                <RotateCcw className="h-3 w-3 mr-1" />
                Reset
              </Button>
            </div>
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
                    {/* Show pending indicator during streaming or REST API call */}
                    {(isChatBusy || pendingAssistantMessage) && (
                      <div className="flex gap-2">
                        <div className="h-7 w-7 rounded-full flex items-center justify-center bg-muted shrink-0">
                          <Bot className="h-3 w-3" />
                        </div>
                        <div className="bg-muted rounded-lg px-3 py-2 flex items-center gap-2">
                          <Spinner className="h-4 w-4" />
                          {pendingAssistantMessage && (
                            <span className="text-sm text-muted-foreground">{pendingAssistantMessage}</span>
                          )}
                        </div>
                      </div>
                    )}
                    <div ref={messagesEndRef} />
                  </div>
                )}
              </ScrollArea>

              {/* View session details button */}
              {sessionId && traceSteps.length > 0 && (
                <div className="border-t px-3 py-2 shrink-0">
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full"
                    onClick={() => setSessionDetailOpen(true)}
                  >
                    <Eye className="h-4 w-4 mr-2" />
                    View Session Details ({traceSteps.length} steps)
                  </Button>
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
                <ChatInputWithAttachments
                  value={inputValue}
                  onChange={setInputValue}
                  onSend={handleSendMessage}
                  placeholder="Type a message... (Shift+Enter for new line)"
                  disabled={false}
                  isLoading={isChatBusy}
                  maxHeight={120}
                  minHeight={36}
                  size="compact"
                  showStopButton={true}
                  onStop={handleStopExecution}
                />
              </div>
            </>
          )}
        </div>
      </div>

      {/* Session Detail Dialog */}
      <SessionDetailDialog
        sessionId={sessionId}
        open={sessionDetailOpen}
        onClose={() => setSessionDetailOpen(false)}
      />
    </div>
  );
}
