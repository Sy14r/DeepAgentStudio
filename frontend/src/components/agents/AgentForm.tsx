import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  Button,
  Input,
  Textarea,
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
  Checkbox,
  Spinner,
  Alert,
  AlertDescription,
  Badge,
  ScrollArea,
} from '@/components/ui';
import { X } from 'lucide-react';
import {
  useAgent,
  useCreateAgent,
  useUpdateAgent,
  useTools,
  useLLMProviders,
  useAgentTypes,
  getErrorMessage,
} from '@/api/hooks';
import { AgentCreateRequest } from '@/api/types';

const agentFormSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100, 'Name must be less than 100 characters'),
  description: z.string().max(500, 'Description must be less than 500 characters').optional(),
  agent_type_id: z.number().min(1, 'Agent type is required'),
  tags: z.array(z.string()).default([]),
  provider_id: z.number().nullable(),
  model: z.string().min(1, 'Model is required'),
  temperature: z.number().min(0).max(2).default(0.7),
  max_tokens: z.number().min(1).max(32000).default(4096),
  tool_ids: z.array(z.number()).default([]),
  system_prompt: z.string().max(10000, 'System prompt must be less than 10000 characters').optional(),
});

type AgentFormData = z.infer<typeof agentFormSchema>;

interface AgentFormProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  agentId: number | null;
}

export function AgentForm({ open, onClose, onSuccess, agentId }: AgentFormProps) {
  const [tagInput, setTagInput] = useState('');
  const [activeTab, setActiveTab] = useState('basic');
  const [error, setError] = useState<string | null>(null);

  const isEditing = agentId !== null;

  const { data: agent, isLoading: isLoadingAgent } = useAgent(agentId ?? undefined);
  const { data: toolsData } = useTools({ pageSize: 100 });
  const { data: providersData } = useLLMProviders({ pageSize: 100 });
  const { data: agentTypesData, isLoading: isLoadingAgentTypes } = useAgentTypes({ isActive: true });

  const createAgent = useCreateAgent();
  const updateAgent = useUpdateAgent(agentId ?? 0);

  // Get default agent type (first ReAct builtin type)
  const defaultAgentTypeId = agentTypesData?.agent_types.find(
    at => at.execution_strategy === 'react' && at.is_builtin
  )?.id ?? 0;

  const form = useForm<AgentFormData>({
    resolver: zodResolver(agentFormSchema),
    defaultValues: {
      name: '',
      description: '',
      agent_type_id: 0,
      tags: [],
      provider_id: null,
      model: 'gpt-4',
      temperature: 0.7,
      max_tokens: 4096,
      tool_ids: [],
      system_prompt: '',
    },
  });

  // Set default agent type when creating new agent
  useEffect(() => {
    if (!isEditing && defaultAgentTypeId && form.getValues('agent_type_id') === 0) {
      form.setValue('agent_type_id', defaultAgentTypeId);
    }
  }, [isEditing, defaultAgentTypeId, form]);

  // Load agent data when editing
  useEffect(() => {
    if (agent && isEditing && providersData) {
      // Find the provider ID based on the provider type string
      const providerType = agent.current_version?.config.llm_config.provider;
      const matchingProvider = providersData.providers.find(p => p.provider_type === providerType);

      form.reset({
        name: agent.name,
        description: agent.description || '',
        agent_type_id: agent.agent_type_id,
        tags: agent.tags || [],
        provider_id: matchingProvider?.id ?? null,
        model: agent.current_version?.config.llm_config.model || 'gpt-4',
        temperature: agent.current_version?.config.llm_config.temperature ?? 0.7,
        max_tokens: agent.current_version?.config.llm_config.max_tokens ?? 4096,
        tool_ids: agent.current_version?.config.tool_ids || [],
        system_prompt: agent.current_version?.config.system_prompt || '',
      });
    }
  }, [agent, isEditing, form, providersData]);

  // Reset form when dialog closes
  useEffect(() => {
    if (!open) {
      form.reset();
      setTagInput('');
      setActiveTab('basic');
      setError(null);
    }
  }, [open, form]);

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
      form.setValue(
        'tool_ids',
        currentTools.filter((id) => id !== toolId)
      );
    } else {
      form.setValue('tool_ids', [...currentTools, toolId]);
    }
  };

  const onSubmit = async (data: AgentFormData) => {
    setError(null);

    // Find the selected provider to get its type
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
        prompt_id: null,
        system_prompt: data.system_prompt || null,
      },
    };

    try {
      if (isEditing) {
        await updateAgent.mutateAsync({
          name: payload.name,
          description: payload.description,
          agent_type_id: payload.agent_type_id,
          tags: payload.tags,
          config: payload.config,
        });
      } else {
        await createAgent.mutateAsync(payload);
      }
      onSuccess();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const isPending = createAgent.isPending || updateAgent.isPending;
  const tools = toolsData?.tools || [];
  const providers = providersData?.providers || [];

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Edit Agent' : 'Create Agent'}</DialogTitle>
        </DialogHeader>

        {isLoadingAgent && isEditing ? (
          <div className="flex justify-center py-8">
            <Spinner className="h-8 w-8" />
          </div>
        ) : (
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col flex-1 overflow-hidden">
              {error && (
                <Alert variant="destructive" className="mb-4">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 overflow-hidden flex flex-col">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="basic">Basic Info</TabsTrigger>
                  <TabsTrigger value="config">Configuration</TabsTrigger>
                  <TabsTrigger value="tools">Tools & Prompts</TabsTrigger>
                </TabsList>

                <ScrollArea className="flex-1 pr-4">
                  <TabsContent value="basic" className="space-y-4 mt-4">
                    <FormField
                      control={form.control}
                      name="name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Name</FormLabel>
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
                          <FormLabel>Description</FormLabel>
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
                        const agentTypes = agentTypesData?.agent_types || [];
                        const selectedType = agentTypes.find(at => at.id === field.value);
                        return (
                          <FormItem>
                            <FormLabel>Agent Type</FormLabel>
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
                                {isLoadingAgentTypes ? (
                                  <SelectItem value="loading" disabled>
                                    Loading agent types...
                                  </SelectItem>
                                ) : agentTypes.length === 0 ? (
                                  <SelectItem value="none" disabled>
                                    No agent types available
                                  </SelectItem>
                                ) : (
                                  agentTypes.map((agentType) => (
                                    <SelectItem key={agentType.id} value={agentType.id.toString()}>
                                      {agentType.name}
                                      {agentType.is_builtin && ' (Built-in)'}
                                      {!agentType.is_builtin && agentType.strategy_type === 'custom_code' && ' (Custom)'}
                                    </SelectItem>
                                  ))
                                )}
                              </SelectContent>
                            </Select>
                            <FormDescription>
                              {selectedType?.description || 'Select an agent type to see its description'}
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
                          <FormLabel>Tags</FormLabel>
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

                  <TabsContent value="config" className="space-y-4 mt-4">
                    <FormField
                      control={form.control}
                      name="provider_id"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>LLM Provider</FormLabel>
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
                          <FormLabel>Model</FormLabel>
                          <FormControl>
                            <Input placeholder="gpt-4" {...field} />
                          </FormControl>
                          <FormDescription>
                            Model identifier (e.g., gpt-4, claude-3-opus, etc.)
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="temperature"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Temperature: {field.value}</FormLabel>
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
                          <FormDescription>
                            Controls randomness. Lower values are more deterministic.
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="max_tokens"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Max Tokens</FormLabel>
                          <FormControl>
                            <Input
                              type="number"
                              min="1"
                              max="32000"
                              {...field}
                              onChange={(e) => field.onChange(parseInt(e.target.value) || 4096)}
                            />
                          </FormControl>
                          <FormDescription>
                            Maximum number of tokens in the response
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </TabsContent>

                  <TabsContent value="tools" className="space-y-4 mt-4">
                    <FormField
                      control={form.control}
                      name="tool_ids"
                      render={() => (
                        <FormItem>
                          <FormLabel>Tools</FormLabel>
                          <FormDescription>
                            Select the tools this agent can use
                          </FormDescription>
                          <div className="border rounded-md p-4 space-y-2 max-h-48 overflow-y-auto">
                            {tools.length === 0 ? (
                              <p className="text-sm text-muted-foreground">
                                No tools available. Create tools first.
                              </p>
                            ) : (
                              tools.map((tool) => (
                                <div
                                  key={tool.id}
                                  className="flex items-center space-x-2"
                                >
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

                    <FormField
                      control={form.control}
                      name="system_prompt"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>System Prompt</FormLabel>
                          <FormControl>
                            <Textarea
                              placeholder="You are a helpful assistant..."
                              className="resize-none min-h-[150px]"
                              {...field}
                            />
                          </FormControl>
                          <FormDescription>
                            Instructions for how the agent should behave
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </TabsContent>
                </ScrollArea>
              </Tabs>

              <div className="flex justify-end gap-2 pt-4 border-t mt-4">
                <Button type="button" variant="outline" onClick={onClose}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isPending}>
                  {isPending ? (
                    <Spinner className="h-4 w-4" />
                  ) : isEditing ? (
                    'Save Changes'
                  ) : (
                    'Create Agent'
                  )}
                </Button>
              </div>
            </form>
          </Form>
        )}
      </DialogContent>
    </Dialog>
  );
}
