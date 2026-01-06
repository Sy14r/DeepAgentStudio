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
import { ChevronDown, ChevronUp, Settings2 } from 'lucide-react';
import {
  useLLMProvider,
  useCreateLLMProvider,
  useUpdateLLMProvider,
  useUpdateLLMProviderAPIKey,
  getErrorMessage,
} from '@/api/hooks';
import { LLMProviderType, CustomModelConfig } from '@/api/types';
import { CustomModelsEditor } from './CustomModelsEditor';

const PROVIDER_TYPES: { value: LLMProviderType; label: string; description: string }[] = [
  { value: 'openai', label: 'OpenAI', description: 'GPT-4, GPT-3.5, and more' },
  { value: 'anthropic', label: 'Anthropic', description: 'Claude models' },
  { value: 'google', label: 'Google', description: 'Gemini models' },
  { value: 'azure_openai', label: 'Azure OpenAI', description: 'OpenAI models on Azure' },
  { value: 'ollama', label: 'Ollama', description: 'Local models via Ollama' },
  { value: 'llamacpp', label: 'LlamaCpp', description: 'Local GGUF models' },
];

// Base schema - api_key is optional (for editing)
const providerFormSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100, 'Name must be less than 100 characters'),
  provider_type: z.enum(['openai', 'anthropic', 'google', 'azure_openai', 'ollama', 'llamacpp']),
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

  const isEditing = providerId !== null;

  const { data: provider, isLoading: isLoadingProvider } = useLLMProvider(providerId ?? undefined);

  const createProvider = useCreateLLMProvider();
  const updateProvider = useUpdateLLMProvider(providerId ?? 0);
  const updateApiKey = useUpdateLLMProviderAPIKey(providerId ?? 0);

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
    }
  }, [open, form]);

  const selectedProviderType = form.watch('provider_type');
  const needsBaseUrl = ['azure_openai', 'ollama', 'llamacpp'].includes(selectedProviderType);
  const isLocalProvider = ['ollama', 'llamacpp'].includes(selectedProviderType);

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
        // For creating, API key is required
        if (!data.api_key) {
          setError('API key is required for new providers');
          return;
        }
        const createPayload = {
          name: data.name,
          provider_type: data.provider_type,
          api_key: data.api_key,
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
                      <Input placeholder="My OpenAI Provider" {...field} />
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

              <FormField
                control={form.control}
                name="api_key"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      {isLocalProvider ? 'API Key (optional)' : 'API Key'}
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
                        : 'Your API key for this provider'}
                    </FormDescription>
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
                      <FormLabel>Base URL</FormLabel>
                      <FormControl>
                        <Input
                          placeholder={
                            selectedProviderType === 'ollama'
                              ? 'http://localhost:11434'
                              : selectedProviderType === 'llamacpp'
                              ? 'http://localhost:8080'
                              : 'https://your-resource.openai.azure.com/'
                          }
                          {...field}
                        />
                      </FormControl>
                      <FormDescription>
                        The base URL for the API endpoint
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}

              {/* Advanced Settings */}
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
