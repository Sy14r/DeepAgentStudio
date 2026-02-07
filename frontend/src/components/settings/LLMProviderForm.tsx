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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  Spinner,
  Alert,
  AlertDescription,
} from '@/components/ui';
import { ChevronDown, ChevronUp, Settings2, RefreshCw } from 'lucide-react';
import {
  useLLMProvider,
  useCreateLLMProvider,
  useUpdateLLMProvider,
  useUpdateLLMProviderAPIKey,
  useDiscoverModels,
  getErrorMessage,
} from '@/api/hooks';
import { LLMProviderType, CustomModelConfig } from '@/api/types';
import { CustomModelsEditor } from './CustomModelsEditor';

const PROVIDER_TYPES: { value: LLMProviderType; label: string; description: string }[] = [
  { value: 'openai', label: 'OpenAI', description: 'GPT-4, GPT-3.5, and more' },
  { value: 'anthropic', label: 'Anthropic', description: 'Claude models' },
  { value: 'openai_compatible', label: 'OpenAI-Compatible', description: 'vLLM, LM Studio, Ollama, llama.cpp, Groq, and more' },
  { value: 'google', label: 'Google', description: 'Gemini models' },
  { value: 'azure_openai', label: 'Azure OpenAI', description: 'OpenAI models on Azure' },
  { value: 'ollama', label: 'Ollama', description: 'Local models via Ollama' },
  { value: 'llamacpp', label: 'LlamaCpp', description: 'Local GGUF models' },
];

// Base schema - api_key is optional (for editing)
const providerFormSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100, 'Name must be less than 100 characters'),
  provider_type: z.enum(['openai', 'anthropic', 'google', 'azure_openai', 'ollama', 'llamacpp', 'openai_compatible']),
  api_key: z.string().optional(),
  base_url: z.string().optional(),
});

type ProviderFormData = z.infer<typeof providerFormSchema>;

interface LLMProviderFormProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  providerId: number | null;
}

export function LLMProviderForm({ open, onClose, onSuccess, providerId }: LLMProviderFormProps) {
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [customModels, setCustomModels] = useState<CustomModelConfig[]>([]);
  const [discoveredModels, setDiscoveredModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [modelSearchQuery, setModelSearchQuery] = useState('');
  const [discoverError, setDiscoverError] = useState<string | null>(null);

  const isEditing = providerId !== null;

  const { data: provider, isLoading: isLoadingProvider } = useLLMProvider(providerId ?? undefined);

  const createProvider = useCreateLLMProvider();
  const updateProvider = useUpdateLLMProvider(providerId ?? 0);
  const updateApiKey = useUpdateLLMProviderAPIKey(providerId ?? 0);
  const discoverModels = useDiscoverModels();

  const form = useForm<ProviderFormData>({
    resolver: zodResolver(providerFormSchema),
    defaultValues: {
      name: '',
      provider_type: 'openai',
      api_key: '',
      base_url: '',
    },
  });

  // Load provider data when editing
  useEffect(() => {
    if (provider && isEditing) {
      form.reset({
        name: provider.name,
        provider_type: provider.provider_type,
        api_key: '', // Don't show existing API key for security
        base_url: (provider.config?.base_url as string) || '',
      });
      // Load custom models from provider config
      const savedModels = provider.config?.custom_models as CustomModelConfig[] | undefined;
      setCustomModels(savedModels || []);
      setShowAdvanced((savedModels?.length ?? 0) > 0);
      // Load selected model for openai_compatible
      if (provider.provider_type === 'openai_compatible') {
        setSelectedModel((provider.config?.default_model as string) || '');
      }
    }
  }, [provider, isEditing, form]);

  // Reset form when dialog closes
  useEffect(() => {
    if (!open) {
      form.reset({
        name: '',
        provider_type: 'openai',
        api_key: '',
        base_url: '',
      });
      setError(null);
      setShowAdvanced(false);
      setCustomModels([]);
      setDiscoveredModels([]);
      setSelectedModel('');
      setModelSearchQuery('');
      setDiscoverError(null);
    }
  }, [open, form]);

  const selectedProviderType = form.watch('provider_type');
  const baseUrlValue = form.watch('base_url');
  const isOpenAICompatible = selectedProviderType === 'openai_compatible';
  const needsBaseUrl = ['openai', 'azure_openai', 'ollama', 'llamacpp', 'openai_compatible'].includes(selectedProviderType);
  const isLocalProvider = ['ollama', 'llamacpp', 'openai_compatible'].includes(selectedProviderType);
  const isApiKeyOptional = isLocalProvider || (selectedProviderType === 'openai' && !!baseUrlValue?.trim());

  const handleDiscoverModels = () => {
    if (!baseUrlValue?.trim()) return;
    setDiscoverError(null);

    discoverModels.mutate(
      {
        base_url: baseUrlValue,
        api_key: form.getValues('api_key') || undefined,
      },
      {
        onSuccess: (data) => {
          if (data.success) {
            setDiscoveredModels(data.models);
            setDiscoverError(null);
          } else {
            setDiscoverError(data.error || 'Failed to discover models');
            setDiscoveredModels([]);
          }
        },
        onError: (err) => {
          setDiscoverError(getErrorMessage(err));
          setDiscoveredModels([]);
        },
      }
    );
  };

  const filteredModels = modelSearchQuery
    ? discoveredModels.filter((m) => m.toLowerCase().includes(modelSearchQuery.toLowerCase()))
    : discoveredModels;

  const onSubmit = async (data: ProviderFormData) => {
    setError(null);

    const config: Record<string, unknown> = {};
    if (data.base_url) {
      config.base_url = data.base_url;
    }
    // Include custom models in config
    if (customModels.length > 0) {
      config.custom_models = customModels;
    }
    // Include selected model for openai_compatible
    if (isOpenAICompatible && selectedModel) {
      config.default_model = selectedModel;
    }

    // Validate openai_compatible requires base_url
    if (isOpenAICompatible && !data.base_url?.trim()) {
      setError('Base URL is required for OpenAI-Compatible providers');
      return;
    }

    try {
      if (isEditing) {
        // For editing, update provider details separately from API key
        const updatePayload = {
          name: data.name,
          provider_type: data.provider_type,
          config: Object.keys(config).length > 0 ? config : undefined,
        };
        await updateProvider.mutateAsync(updatePayload);

        // If API key was provided, update it separately
        if (data.api_key && data.api_key.trim()) {
          await updateApiKey.mutateAsync(data.api_key);
        }
      } else {
        // For creating, API key is required unless local/compatible provider or custom base_url is set
        const hasBaseUrl = !!data.base_url?.trim();
        if (!data.api_key && !hasBaseUrl && !isOpenAICompatible) {
          setError('API key is required when no custom base URL is configured');
          return;
        }
        const createPayload = {
          name: data.name,
          provider_type: data.provider_type,
          api_key: data.api_key || '',
          config: Object.keys(config).length > 0 ? config : undefined,
        };
        await createProvider.mutateAsync(createPayload);
      }
      onSuccess();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const isPending = createProvider.isPending || updateProvider.isPending || updateApiKey.isPending;

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? 'Edit LLM Provider' : 'Add LLM Provider'}
          </DialogTitle>
        </DialogHeader>

        {isLoadingProvider && isEditing ? (
          <div className="flex justify-center py-8">
            <Spinner className="h-8 w-8" />
          </div>
        ) : (
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name</FormLabel>
                    <FormControl>
                      <Input
                        placeholder={
                          isOpenAICompatible
                            ? 'My Local vLLM Server'
                            : 'My OpenAI Provider'
                        }
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      A friendly name for this provider configuration
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="provider_type"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Provider Type</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select provider type" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {PROVIDER_TYPES.map((pt) => (
                          <SelectItem key={pt.value} value={pt.value}>
                            <div className="flex flex-col">
                              <span>{pt.label}</span>
                              <span className="text-xs text-muted-foreground">
                                {pt.description}
                              </span>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {needsBaseUrl && (
                <FormField
                  control={form.control}
                  name="base_url"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>
                        {isOpenAICompatible ? 'Base URL *' : 'Base URL'}
                      </FormLabel>
                      <FormControl>
                        <Input
                          placeholder={
                            isOpenAICompatible
                              ? 'http://localhost:8000/v1'
                              : selectedProviderType === 'openai'
                              ? 'http://localhost:8000/v1'
                              : selectedProviderType === 'ollama'
                              ? 'http://localhost:11434'
                              : selectedProviderType === 'llamacpp'
                              ? 'http://localhost:8080'
                              : 'https://your-resource.openai.azure.com/'
                          }
                          {...field}
                        />
                      </FormControl>
                      <FormDescription>
                        {isOpenAICompatible
                          ? 'The base URL of your OpenAI-compatible server (required)'
                          : selectedProviderType === 'openai'
                          ? 'Custom endpoint for OpenAI-compatible APIs (vLLM, LM Studio, Ollama, etc.). Leave blank for official OpenAI API.'
                          : 'The base URL for the API endpoint'}
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}

              <FormField
                control={form.control}
                name="api_key"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      {isApiKeyOptional ? 'API Key (optional)' : 'API Key'}
                    </FormLabel>
                    <FormControl>
                      <Input
                        type="password"
                        placeholder={isEditing ? '••••••••••••••••' : 'sk-...'}
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      {isEditing
                        ? 'Leave blank to keep existing key'
                        : isOpenAICompatible
                        ? 'Required for cloud services (Together AI, Groq, OpenRouter). Not needed for most local servers.'
                        : 'Your API key for this provider'}
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Model Discovery for OpenAI-Compatible */}
              {isOpenAICompatible && (
                <div className="space-y-2">
                  <FormLabel>Default Model</FormLabel>
                  <div className="flex gap-2">
                    <Input
                      placeholder="Enter model name or fetch from server"
                      value={selectedModel || modelSearchQuery}
                      onChange={(e) => {
                        const val = e.target.value;
                        setModelSearchQuery(val);
                        setSelectedModel(val);
                      }}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      className="shrink-0"
                      disabled={!baseUrlValue?.trim() || discoverModels.isPending}
                      onClick={handleDiscoverModels}
                      title="Fetch models from server"
                    >
                      {discoverModels.isPending ? (
                        <Spinner className="h-4 w-4" />
                      ) : (
                        <RefreshCw className="h-4 w-4" />
                      )}
                    </Button>
                  </div>

                  {discoverError && (
                    <p className="text-xs text-destructive">{discoverError}</p>
                  )}

                  {discoveredModels.length > 0 && (
                    <div className="max-h-40 overflow-y-auto border rounded-md divide-y">
                      {filteredModels.map((model) => (
                        <button
                          key={model}
                          type="button"
                          className={`w-full text-left px-3 py-1.5 text-sm hover:bg-accent transition-colors ${
                            selectedModel === model ? 'bg-accent font-medium' : ''
                          }`}
                          onClick={() => {
                            setSelectedModel(model);
                            setModelSearchQuery('');
                          }}
                        >
                          {model}
                        </button>
                      ))}
                      {filteredModels.length === 0 && (
                        <p className="px-3 py-1.5 text-sm text-muted-foreground">
                          No models match "{modelSearchQuery}"
                        </p>
                      )}
                    </div>
                  )}

                  <p className="text-xs text-muted-foreground">
                    {discoveredModels.length > 0
                      ? `${discoveredModels.length} model${discoveredModels.length !== 1 ? 's' : ''} found. Click to select or type a custom name.`
                      : 'Click the refresh button to discover available models, or type a model name manually.'}
                  </p>
                </div>
              )}

              {/* Advanced Settings - hide for openai_compatible */}
              {!isOpenAICompatible && (
                <div className="border-t pt-4">
                  <button
                    type="button"
                    onClick={() => setShowAdvanced(!showAdvanced)}
                    className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors w-full"
                  >
                    <Settings2 className="h-4 w-4" />
                    Advanced Settings
                    {showAdvanced ? (
                      <ChevronUp className="h-4 w-4 ml-auto" />
                    ) : (
                      <ChevronDown className="h-4 w-4 ml-auto" />
                    )}
                    {customModels.length > 0 && (
                      <span className="text-xs bg-primary/10 text-primary px-1.5 py-0.5 rounded">
                        {customModels.length} custom model{customModels.length !== 1 ? 's' : ''}
                      </span>
                    )}
                  </button>

                  {showAdvanced && (
                    <div className="mt-4 space-y-4">
                      <CustomModelsEditor
                        models={customModels}
                        onChange={setCustomModels}
                      />
                      <p className="text-xs text-muted-foreground">
                        Custom models let you add models not in the default list, with specific parameter constraints.
                      </p>
                    </div>
                  )}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-4">
                <Button type="button" variant="outline" onClick={onClose}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isPending}>
                  {isPending ? (
                    <Spinner className="h-4 w-4" />
                  ) : isEditing ? (
                    'Save Changes'
                  ) : (
                    'Add Provider'
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
