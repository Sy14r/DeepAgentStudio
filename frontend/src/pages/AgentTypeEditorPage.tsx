import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Editor, { OnMount } from '@monaco-editor/react';
import {
  Button,
  Input,
  Textarea,
  Badge,
  Spinner,
  Alert,
  AlertDescription,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Label,
  Slider,
  Checkbox,
  ScrollArea,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Switch,
} from '@/components/ui';
import {
  Save,
  X,
  AlertCircle,
  Copy,
  Info,
  Brain,
  ListChecks,
  MessageCircle,
  Sparkles,
  Settings2,
  FileText,
  Wrench,
  Code,
  CheckCircle,
  AlertTriangle,
} from 'lucide-react';
import {
  useAgentType,
  useCreateAgentType,
  useUpdateAgentType,
  useCloneAgentType,
  useTools,
  useValidateStrategyCode,
  useStrategyTemplates,
  useStrategyTemplate,
  getErrorMessage,
} from '@/api/hooks';
import { useUIStore } from '@/stores/uiStore';
import {
  ExecutionStrategy,
  StrategyType,
  AgentTypeConfigCreateRequest,
  AgentTypeConfigUpdateRequest,
  DefaultLLMConfig,
  DefaultMemoryConfig,
} from '@/api/types';

const EXECUTION_STRATEGIES: { value: ExecutionStrategy; label: string; description: string }[] = [
  { value: 'react', label: 'ReAct', description: 'Reasoning and Acting - uses tools iteratively' },
  { value: 'plan_and_execute', label: 'Plan & Execute', description: 'Creates plan first, then executes steps' },
  { value: 'conversational', label: 'Conversational', description: 'Simple chat without tool usage' },
];

const ICON_OPTIONS: { value: string; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { value: 'brain', label: 'Brain', icon: Brain },
  { value: 'list-checks', label: 'List Checks', icon: ListChecks },
  { value: 'message-circle', label: 'Message Circle', icon: MessageCircle },
  { value: 'sparkles', label: 'Sparkles', icon: Sparkles },
];

const MEMORY_TYPES = [
  { value: 'buffer', label: 'Buffer', description: 'Stores recent messages' },
  { value: 'summary', label: 'Summary', description: 'Summarizes conversation' },
  { value: 'vector', label: 'Vector', description: 'Semantic search retrieval' },
];

const DEFAULT_STRATEGY_CODE = `def execute(llm, tools, input_message, chat_history, config, helpers):
    """
    Custom execution strategy.

    Args:
        llm: LangChain chat model instance
        tools: List of available LangChain tools
        input_message: User's input message
        chat_history: List of previous messages
        config: Agent configuration dict
        helpers: ExecutionHelpers instance for tracked LLM/tool calls

    Returns:
        ExecutionResult with output and token usage
    """
    helpers.record_thought("Processing user input...")

    # Make an LLM call with tracking
    messages = [
        {"role": "system", "content": config.get("system_prompt", "You are a helpful assistant.")},
        {"role": "user", "content": input_message}
    ]

    response = helpers.call_llm(messages)

    return helpers.create_result(output=response)
`;

export function AgentTypeEditorPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { theme } = useUIStore();

  const isEditing = id !== undefined && id !== 'new';
  const typeId = isEditing ? parseInt(id) : null;

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [icon, setIcon] = useState('sparkles');
  const [executionStrategy, setExecutionStrategy] = useState<ExecutionStrategy>('react');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [maxIterations, setMaxIterations] = useState(10);

  // Custom strategy state
  const [strategyType, setStrategyType] = useState<StrategyType>('builtin');
  const [customStrategyCode, setCustomStrategyCode] = useState(DEFAULT_STRATEGY_CODE);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [codeValidation, setCodeValidation] = useState<{ isValid: boolean; error: string | null; warnings: string[] } | null>(null);
  const editorRef = useRef<any>(null);

  // LLM Config
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(4096);

  // Memory Config
  const [memoryType, setMemoryType] = useState('buffer');
  const [contextWindow, setContextWindow] = useState(10);

  // Recommended tools
  const [selectedToolIds, setSelectedToolIds] = useState<number[]>([]);

  // Editor state
  const [error, setError] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [activeTab, setActiveTab] = useState('configuration');

  // Data hooks
  const { data: agentType, isLoading: isLoadingType } = useAgentType(typeId ?? undefined);
  const { data: toolsData, isLoading: isLoadingTools } = useTools({ pageSize: 100 });
  const { data: strategyTemplatesData } = useStrategyTemplates();
  const { data: templateData } = useStrategyTemplate(selectedTemplate || undefined);
  const createAgentType = useCreateAgentType();
  const updateAgentType = useUpdateAgentType(typeId ?? 0);
  const cloneAgentType = useCloneAgentType();
  const validateStrategyCode = useValidateStrategyCode();

  const isBuiltin = isEditing && agentType?.is_builtin;
  const tools = toolsData?.tools || [];
  const strategyTemplates = strategyTemplatesData?.templates || [];

  // Initialize form with existing data
  useEffect(() => {
    if (agentType) {
      setName(agentType.name);
      setDescription(agentType.description || '');
      setIcon(agentType.icon || 'sparkles');
      setExecutionStrategy(agentType.execution_strategy);
      setSystemPrompt(agentType.system_prompt_template || '');
      setMaxIterations(agentType.max_iterations);

      // Custom strategy
      setStrategyType(agentType.strategy_type);
      setCustomStrategyCode(agentType.custom_strategy_code || DEFAULT_STRATEGY_CODE);

      // LLM Config
      const llmConfig = agentType.default_llm_config;
      setTemperature(llmConfig.temperature ?? 0.7);
      setMaxTokens(llmConfig.max_tokens ?? 4096);

      // Memory Config
      const memConfig = agentType.default_memory_config;
      setMemoryType(memConfig.type ?? 'buffer');
      setContextWindow(memConfig.context_window ?? 10);

      // Recommended tools
      setSelectedToolIds(agentType.recommended_tools.map(t => t.id));

      setHasUnsavedChanges(false);
    } else if (!isEditing) {
      // Reset for new type
      setName('');
      setDescription('');
      setIcon('sparkles');
      setExecutionStrategy('react');
      setSystemPrompt('');
      setMaxIterations(10);
      setStrategyType('builtin');
      setCustomStrategyCode(DEFAULT_STRATEGY_CODE);
      setCodeValidation(null);
      setTemperature(0.7);
      setMaxTokens(4096);
      setMemoryType('buffer');
      setContextWindow(10);
      setSelectedToolIds([]);
      setHasUnsavedChanges(false);
    }
  }, [agentType, isEditing]);

  // Load template code when selected
  useEffect(() => {
    if (templateData?.code) {
      setCustomStrategyCode(templateData.code);
      setSelectedTemplate(''); // Reset selection after loading
      setCodeValidation(null); // Clear validation
    }
  }, [templateData]);

  // Validate code when it changes (debounced)
  useEffect(() => {
    if (strategyType !== 'custom_code') return;

    const timeout = setTimeout(async () => {
      try {
        const result = await validateStrategyCode.mutateAsync({ code: customStrategyCode });
        setCodeValidation({
          isValid: result.is_valid,
          error: result.error,
          warnings: result.warnings,
        });
      } catch {
        // Ignore validation errors during typing
      }
    }, 500);

    return () => clearTimeout(timeout);
  }, [customStrategyCode, strategyType]);

  // Track unsaved changes
  useEffect(() => {
    if (!isLoadingType && (isEditing ? agentType : true)) {
      setHasUnsavedChanges(true);
    }
  }, [name, description, icon, executionStrategy, systemPrompt, maxIterations, strategyType, customStrategyCode, temperature, maxTokens, memoryType, contextWindow, selectedToolIds]);

  // Editor mount handler
  const handleEditorMount: OnMount = (editor) => {
    editorRef.current = editor;
  };

  const handleSave = async () => {
    if (!name.trim()) {
      setError('Name is required');
      return;
    }

    // Validate custom strategy code if using custom execution
    if (strategyType === 'custom_code') {
      if (!customStrategyCode.trim()) {
        setError('Custom strategy code is required when using custom execution');
        setActiveTab('code');
        return;
      }
      if (codeValidation && !codeValidation.isValid) {
        setError(`Invalid strategy code: ${codeValidation.error}`);
        setActiveTab('code');
        return;
      }
    }

    setError(null);

    const llmConfig: DefaultLLMConfig = {
      temperature,
      max_tokens: maxTokens,
    };

    const memoryConfig: DefaultMemoryConfig = {
      type: memoryType,
      context_window: contextWindow,
    };

    try {
      if (isEditing && typeId) {
        const updatePayload: AgentTypeConfigUpdateRequest = {
          name: name.trim(),
          description: description.trim() || undefined,
          icon,
          execution_strategy: executionStrategy,
          system_prompt_template: systemPrompt.trim() || undefined,
          default_llm_config: llmConfig,
          default_memory_config: memoryConfig,
          max_iterations: maxIterations,
          strategy_type: strategyType,
          custom_strategy_code: strategyType === 'custom_code' ? customStrategyCode : undefined,
          recommended_tool_ids: selectedToolIds,
        };
        await updateAgentType.mutateAsync(updatePayload);
      } else {
        const createPayload: AgentTypeConfigCreateRequest = {
          name: name.trim(),
          description: description.trim() || undefined,
          icon,
          execution_strategy: executionStrategy,
          system_prompt_template: systemPrompt.trim() || undefined,
          default_llm_config: llmConfig,
          default_memory_config: memoryConfig,
          max_iterations: maxIterations,
          strategy_type: strategyType,
          custom_strategy_code: strategyType === 'custom_code' ? customStrategyCode : undefined,
          recommended_tool_ids: selectedToolIds,
        };
        const created = await createAgentType.mutateAsync(createPayload);
        navigate(`/agent-types/${created.id}/edit`, { replace: true });
      }
      setHasUnsavedChanges(false);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const handleCancel = () => {
    navigate('/agent-types');
  };

  const handleClone = async () => {
    if (typeId) {
      try {
        const cloned = await cloneAgentType.mutateAsync({ id: typeId });
        navigate(`/agent-types/${cloned.id}/edit`);
      } catch (err) {
        setError(getErrorMessage(err));
      }
    }
  };

  const toggleToolSelection = (toolId: number) => {
    setSelectedToolIds(prev =>
      prev.includes(toolId)
        ? prev.filter(id => id !== toolId)
        : [...prev, toolId]
    );
  };

  const isPending = createAgentType.isPending || updateAgentType.isPending || cloneAgentType.isPending;
  const isLoading = isLoadingType && isEditing;

  // Get icon component
  const IconComponent = ICON_OPTIONS.find(opt => opt.value === icon)?.icon || Sparkles;

  if (isLoading) {
    return (
      <div className="h-[calc(100vh-8rem)] flex items-center justify-center">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10">
            <IconComponent className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              {name || 'New Agent Type'}
              {isBuiltin && (
                <Badge variant="secondary" className="text-gray-600">
                  Built-in
                </Badge>
              )}
              {!isBuiltin && hasUnsavedChanges && (
                <Badge variant="outline" className="text-yellow-600">
                  Unsaved
                </Badge>
              )}
            </h1>
            <p className="text-sm text-muted-foreground">
              {isBuiltin
                ? 'View built-in agent type (read-only)'
                : isEditing
                  ? 'Edit agent type configuration'
                  : 'Create a new agent type'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleCancel}>
            <X className="mr-2 h-4 w-4" />
            {isBuiltin ? 'Close' : 'Cancel'}
          </Button>
          {isBuiltin ? (
            <Button onClick={handleClone} disabled={isPending}>
              {isPending ? (
                <Spinner className="mr-2 h-4 w-4" />
              ) : (
                <Copy className="mr-2 h-4 w-4" />
              )}
              Clone to Edit
            </Button>
          ) : (
            <Button onClick={handleSave} disabled={isPending}>
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

      {/* Built-in info banner */}
      {isBuiltin && (
        <Alert className="border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950/30">
          <Info className="h-4 w-4 text-blue-600 dark:text-blue-400" />
          <AlertDescription className="text-blue-800 dark:text-blue-200">
            This is a built-in agent type and cannot be modified. Use "Clone to Edit" to create a customizable copy.
          </AlertDescription>
        </Alert>
      )}

      {/* Error */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Main content with Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList>
          <TabsTrigger value="configuration" className="flex items-center gap-2">
            <Settings2 className="h-4 w-4" />
            Configuration
          </TabsTrigger>
          <TabsTrigger value="code" className="flex items-center gap-2">
            <Code className="h-4 w-4" />
            Custom Code
            {strategyType === 'custom_code' && (
              codeValidation?.isValid ? (
                <CheckCircle className="h-3 w-3 text-green-500" />
              ) : codeValidation?.error ? (
                <AlertCircle className="h-3 w-3 text-red-500" />
              ) : null
            )}
          </TabsTrigger>
        </TabsList>

        {/* Configuration Tab */}
        <TabsContent value="configuration">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Left column - Basic info */}
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Settings2 className="h-5 w-5" />
                    Basic Information
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label>Name</Label>
                    <Input
                      placeholder="My Custom Agent Type"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      disabled={isBuiltin}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Description</Label>
                    <Textarea
                      placeholder="Describe what this agent type is best suited for..."
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                  className="resize-none h-20"
                  disabled={isBuiltin}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Icon</Label>
                  <Select value={icon} onValueChange={setIcon} disabled={isBuiltin}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ICON_OPTIONS.map((opt) => {
                        const Icon = opt.icon;
                        return (
                          <SelectItem key={opt.value} value={opt.value}>
                            <div className="flex items-center gap-2">
                              <Icon className="h-4 w-4" />
                              {opt.label}
                            </div>
                          </SelectItem>
                        );
                      })}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Execution Strategy</Label>
                  <Select
                    value={executionStrategy}
                    onValueChange={(v) => setExecutionStrategy(v as ExecutionStrategy)}
                    disabled={isBuiltin}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {EXECUTION_STRATEGIES.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    {EXECUTION_STRATEGIES.find(s => s.value === executionStrategy)?.description}
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                    <Label>Max Iterations: {maxIterations}</Label>
                    <Slider
                      value={[maxIterations]}
                      onValueChange={([v]) => setMaxIterations(v)}
                      min={1}
                      max={50}
                      step={1}
                      disabled={isBuiltin}
                    />
                    <p className="text-xs text-muted-foreground">
                      Maximum number of reasoning/tool-use iterations before stopping
                    </p>
                  </div>

                  {/* Strategy Type Toggle */}
                  <div className="pt-4 border-t space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <Label className="text-base">Custom Execution Code</Label>
                        <p className="text-xs text-muted-foreground">
                          Write custom Python code to define execution logic
                        </p>
                      </div>
                      <Switch
                        checked={strategyType === 'custom_code'}
                        onCheckedChange={(checked) => {
                          setStrategyType(checked ? 'custom_code' : 'builtin');
                          if (checked) {
                            setActiveTab('code');
                          }
                        }}
                        disabled={isBuiltin}
                      />
                    </div>
                    {strategyType === 'custom_code' && (
                      <Alert className="border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30">
                        <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                        <AlertDescription className="text-amber-800 dark:text-amber-200 text-sm">
                          Custom code will override the built-in execution strategy. Go to the Custom Code tab to edit.
                        </AlertDescription>
                      </Alert>
                    )}
                  </div>
                </CardContent>
              </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <FileText className="h-5 w-5" />
                Default System Prompt
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Textarea
                placeholder="You are a helpful AI assistant..."
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                className="resize-none h-40 font-mono text-sm"
                disabled={isBuiltin}
              />
              <p className="text-xs text-muted-foreground mt-2">
                This prompt will be used as the default system prompt for agents of this type.
                Agents can override this with their own custom prompt.
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Right column - LLM Config, Memory, Tools */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Brain className="h-5 w-5" />
                Default LLM Configuration
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Temperature: {temperature.toFixed(2)}</Label>
                <Slider
                  value={[temperature]}
                  onValueChange={([v]) => setTemperature(v)}
                  min={0}
                  max={2}
                  step={0.1}
                  disabled={isBuiltin}
                />
                <p className="text-xs text-muted-foreground">
                  Controls randomness. Lower = more focused, higher = more creative.
                </p>
              </div>

              <div className="space-y-2">
                <Label>Max Tokens: {maxTokens}</Label>
                <Slider
                  value={[maxTokens]}
                  onValueChange={([v]) => setMaxTokens(v)}
                  min={256}
                  max={16384}
                  step={256}
                  disabled={isBuiltin}
                />
                <p className="text-xs text-muted-foreground">
                  Maximum number of tokens in the response.
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <MessageCircle className="h-5 w-5" />
                Default Memory Configuration
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Memory Type</Label>
                <Select value={memoryType} onValueChange={setMemoryType} disabled={isBuiltin}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {MEMORY_TYPES.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  {MEMORY_TYPES.find(m => m.value === memoryType)?.description}
                </p>
              </div>

              <div className="space-y-2">
                <Label>Context Window: {contextWindow} messages</Label>
                <Slider
                  value={[contextWindow]}
                  onValueChange={([v]) => setContextWindow(v)}
                  min={1}
                  max={50}
                  step={1}
                  disabled={isBuiltin}
                />
                <p className="text-xs text-muted-foreground">
                  Number of previous messages to include in context.
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Wrench className="h-5 w-5" />
                Recommended Tools
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">
                Select tools that are recommended for agents of this type. These will be suggested
                when creating new agents.
              </p>
              <ScrollArea className="h-48 border rounded-md p-2">
                {isLoadingTools ? (
                  <div className="flex items-center justify-center h-full">
                    <Spinner className="h-6 w-6" />
                  </div>
                ) : tools.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No tools available. Create some tools first.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {tools.map((tool) => (
                      <div
                        key={tool.id}
                        className="flex items-center space-x-3 p-2 rounded hover:bg-muted/50"
                      >
                        <Checkbox
                          id={`tool-${tool.id}`}
                          checked={selectedToolIds.includes(tool.id)}
                          onCheckedChange={() => !isBuiltin && toggleToolSelection(tool.id)}
                          disabled={isBuiltin}
                        />
                        <label
                          htmlFor={`tool-${tool.id}`}
                          className="flex-1 cursor-pointer"
                        >
                          <div className="font-medium text-sm">{tool.name}</div>
                          <div className="text-xs text-muted-foreground line-clamp-1">
                            {tool.description}
                          </div>
                        </label>
                        <Badge variant="outline" className="text-xs">
                          {tool.category}
                        </Badge>
                      </div>
                    ))}
                  </div>
                )}
              </ScrollArea>
              {selectedToolIds.length > 0 && (
                <p className="text-xs text-muted-foreground mt-2">
                  {selectedToolIds.length} tool{selectedToolIds.length !== 1 ? 's' : ''} selected
                </p>
              )}
            </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        {/* Custom Code Tab */}
        <TabsContent value="code" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Code className="h-5 w-5" />
                Custom Execution Strategy Code
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Strategy Type Info */}
              {strategyType !== 'custom_code' && (
                <Alert className="border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950/30">
                  <Info className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                  <AlertDescription className="text-blue-800 dark:text-blue-200">
                    Custom code is disabled. Enable "Custom Execution Code" in the Configuration tab to use custom strategy code.
                  </AlertDescription>
                </Alert>
              )}

              {/* Template Selector */}
              {strategyType === 'custom_code' && (
                <div className="flex items-center gap-4">
                  <div className="flex-1">
                    <Label>Load Template</Label>
                    <Select value={selectedTemplate} onValueChange={setSelectedTemplate} disabled={isBuiltin}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select a template to start from..." />
                      </SelectTrigger>
                      <SelectContent>
                        {strategyTemplates.map((template) => (
                          <SelectItem key={template.name} value={template.name}>
                            <div>
                              <div className="font-medium">{template.name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</div>
                              <div className="text-xs text-muted-foreground">{template.description}</div>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              )}

              {/* Validation Status */}
              {strategyType === 'custom_code' && codeValidation && (
                <div>
                  {codeValidation.isValid ? (
                    <Alert className="border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950/30">
                      <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                      <AlertDescription className="text-green-800 dark:text-green-200">
                        Code is valid
                        {codeValidation.warnings.length > 0 && (
                          <span className="ml-2 text-yellow-600 dark:text-yellow-400">
                            ({codeValidation.warnings.length} warning{codeValidation.warnings.length !== 1 ? 's' : ''})
                          </span>
                        )}
                      </AlertDescription>
                    </Alert>
                  ) : (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>{codeValidation.error}</AlertDescription>
                    </Alert>
                  )}
                  {codeValidation.warnings.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {codeValidation.warnings.map((warning, i) => (
                        <Alert key={i} className="border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-950/30 py-2">
                          <AlertTriangle className="h-3 w-3 text-yellow-600 dark:text-yellow-400" />
                          <AlertDescription className="text-yellow-800 dark:text-yellow-200 text-sm">
                            {warning}
                          </AlertDescription>
                        </Alert>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Monaco Editor */}
              <div className="border rounded-md overflow-hidden">
                <Editor
                  height="500px"
                  language="python"
                  theme={theme === 'dark' ? 'vs-dark' : 'light'}
                  value={customStrategyCode}
                  onChange={(value) => setCustomStrategyCode(value || '')}
                  onMount={handleEditorMount}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                    lineNumbers: 'on',
                    roundedSelection: true,
                    scrollBeyondLastLine: false,
                    readOnly: isBuiltin || strategyType !== 'custom_code',
                    wordWrap: 'on',
                    tabSize: 4,
                    automaticLayout: true,
                  }}
                />
              </div>

              {/* Helper Documentation */}
              <Card className="bg-muted/30">
                <CardHeader className="py-3">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Info className="h-4 w-4" />
                    Available Helpers
                  </CardTitle>
                </CardHeader>
                <CardContent className="py-3 text-sm space-y-2">
                  <p><code className="bg-muted px-1 rounded">helpers.record_thought(content)</code> - Record a reasoning step</p>
                  <p><code className="bg-muted px-1 rounded">helpers.call_llm(messages)</code> - Make an LLM call with tracking</p>
                  <p><code className="bg-muted px-1 rounded">helpers.call_tool(name, input)</code> - Execute a tool by name</p>
                  <p><code className="bg-muted px-1 rounded">helpers.list_tools()</code> - Get list of available tools</p>
                  <p><code className="bg-muted px-1 rounded">helpers.get_token_usage()</code> - Get current token counts</p>
                  <p><code className="bg-muted px-1 rounded">helpers.create_result(output)</code> - Create the final result</p>
                </CardContent>
              </Card>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
