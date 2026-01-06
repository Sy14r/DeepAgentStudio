import { useState, useEffect, useMemo } from 'react';
import {
  Button,
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Badge,
  Alert,
  AlertDescription,
} from '@/components/ui';
import {
  ChevronDown,
  ChevronUp,
  Settings2,
  AlertTriangle,
  Info,
  Sparkles,
} from 'lucide-react';
import {
  LLM_PROVIDER_CONFIG,
  getConfigValidationWarnings,
  requiresMaxCompletionTokens,
  getProviderModels,
  getModelParameterConfig,
  type ProviderConfig,
  type CustomModelConfig,
} from '@/config/llmProviders';
import { LLMProvider } from '@/api/types';

interface LLMConfigValues {
  provider?: string;
  provider_id?: number;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  top_k?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
}

interface ModelParameterHelperProps {
  providers: LLMProvider[];
  currentConfig: LLMConfigValues;
  onApply: (updates: LLMConfigValues) => void;
  defaultExpanded?: boolean;
}

export function ModelParameterHelper({
  providers,
  currentConfig,
  onApply,
  defaultExpanded = true,
}: ModelParameterHelperProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Local state for form values
  const [selectedProviderId, setSelectedProviderId] = useState<number | null>(
    currentConfig.provider_id ?? null
  );
  const [model, setModel] = useState(currentConfig.model || '');
  const [temperature, setTemperature] = useState(currentConfig.temperature ?? 0.7);
  const [maxTokens, setMaxTokens] = useState(currentConfig.max_tokens ?? 4096);
  const [topP, setTopP] = useState(currentConfig.top_p ?? 1);
  const [topK, setTopK] = useState(currentConfig.top_k ?? 40);
  const [frequencyPenalty, setFrequencyPenalty] = useState(currentConfig.frequency_penalty ?? 0);
  const [presencePenalty, setPresencePenalty] = useState(currentConfig.presence_penalty ?? 0);

  // Sync local state with currentConfig when it changes externally
  useEffect(() => {
    if (currentConfig.provider_id !== undefined) {
      setSelectedProviderId(currentConfig.provider_id);
    }
    if (currentConfig.model !== undefined) {
      setModel(currentConfig.model);
    }
    if (currentConfig.temperature !== undefined) {
      setTemperature(currentConfig.temperature);
    }
    if (currentConfig.max_tokens !== undefined) {
      setMaxTokens(currentConfig.max_tokens);
    }
  }, [currentConfig.provider_id, currentConfig.model, currentConfig.temperature, currentConfig.max_tokens]);

  // Get selected provider info
  const selectedProvider = useMemo(() => {
    if (selectedProviderId === null) return null;
    return providers.find((p) => p.id === selectedProviderId) || null;
  }, [providers, selectedProviderId]);

  const providerType = selectedProvider?.provider_type || 'openai';
  const providerConfig: ProviderConfig | undefined = LLM_PROVIDER_CONFIG[providerType];

  // Get custom models from provider config
  const customModels = useMemo(() => {
    return (selectedProvider?.config?.custom_models as CustomModelConfig[] | undefined) || [];
  }, [selectedProvider]);

  // Get merged model list (defaults + custom)
  const availableModels = useMemo(() => {
    return getProviderModels(providerType, customModels);
  }, [providerType, customModels]);

  // Get parameter config with custom model overrides
  const effectiveParamConfig = useMemo(() => {
    return getModelParameterConfig(providerType, model, customModels) || providerConfig?.parameters;
  }, [providerType, model, customModels, providerConfig]);

  // Get validation warnings
  const warnings = useMemo(() => {
    return getConfigValidationWarnings(providerType, {
      model,
      temperature,
      max_tokens: maxTokens,
    });
  }, [providerType, model, temperature, maxTokens]);

  // Check if model uses max_completion_tokens
  const usesCompletionTokens = requiresMaxCompletionTokens(providerType, model);

  const handleApply = () => {
    const updates: LLMConfigValues = {
      provider: providerType,
      provider_id: selectedProviderId ?? undefined,
      model,
      temperature,
      max_tokens: maxTokens,
    };

    // Include advanced params if they differ from defaults
    if (showAdvanced) {
      if (topP !== 1) updates.top_p = topP;
      if (effectiveParamConfig?.top_k && topK !== (effectiveParamConfig.top_k.default ?? 40)) {
        updates.top_k = topK;
      }
      if (effectiveParamConfig?.frequency_penalty && frequencyPenalty !== 0) {
        updates.frequency_penalty = frequencyPenalty;
      }
      if (effectiveParamConfig?.presence_penalty && presencePenalty !== 0) {
        updates.presence_penalty = presencePenalty;
      }
    }

    onApply(updates);
  };

  const handleProviderChange = (providerId: string) => {
    const id = parseInt(providerId);
    setSelectedProviderId(id);

    const provider = providers.find((p) => p.id === id);
    if (provider) {
      const providerCustomModels = (provider.config?.custom_models as CustomModelConfig[] | undefined) || [];
      const models = getProviderModels(provider.provider_type, providerCustomModels);
      const config = LLM_PROVIDER_CONFIG[provider.provider_type];

      if (models.length > 0) {
        setModel(models[0].id);
      }
      if (config) {
        setTemperature(config.parameters.temperature.default ?? 0.7);
        setMaxTokens(config.parameters.max_tokens.default ?? 4096);
      }
    }
  };

  const handleModelChange = (modelId: string) => {
    setModel(modelId);
  };

  if (!isExpanded) {
    return (
      <div className="border rounded-lg bg-muted/30">
        <button
          onClick={() => setIsExpanded(true)}
          className="w-full flex items-center justify-between px-4 py-2 text-sm font-medium hover:bg-muted/50 transition-colors"
        >
          <div className="flex items-center gap-2">
            <Settings2 className="h-4 w-4" />
            Model Settings
          </div>
          <ChevronDown className="h-4 w-4" />
        </button>
      </div>
    );
  }

  return (
    <div className="border rounded-lg overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(false)}
        className="w-full flex items-center justify-between px-4 py-2 bg-muted/30 text-sm font-medium hover:bg-muted/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Settings2 className="h-4 w-4" />
          Model Settings
        </div>
        <ChevronUp className="h-4 w-4" />
      </button>

      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Provider Selection */}
        <div className="space-y-2">
          <Label className="text-xs">Provider</Label>
          <Select
            value={selectedProviderId?.toString() || ''}
            onValueChange={handleProviderChange}
          >
            <SelectTrigger className="h-8 text-sm">
              <SelectValue placeholder="Select provider" />
            </SelectTrigger>
            <SelectContent>
              {providers.map((provider) => (
                <SelectItem key={provider.id} value={provider.id.toString()}>
                  {provider.name} ({provider.provider_type})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Model Selection */}
        <div className="space-y-2">
          <Label className="text-xs">
            Model
            {customModels.length > 0 && (
              <Badge variant="secondary" className="ml-2 text-[10px] h-4">
                {customModels.length} custom
              </Badge>
            )}
          </Label>
          {availableModels.length > 0 ? (
            <Select value={model} onValueChange={handleModelChange}>
              <SelectTrigger className="h-8 text-sm">
                <SelectValue placeholder="Select model" />
              </SelectTrigger>
              <SelectContent>
                {availableModels.map((m) => (
                  <SelectItem key={m.id} value={m.id}>
                    <div className="flex items-center gap-2">
                      {m.name}
                      {m.usesMaxCompletionTokens && (
                        <Badge variant="outline" className="text-[10px] h-4">
                          new API
                        </Badge>
                      )}
                      {customModels.some((cm) => cm.id === m.id) && (
                        <Badge variant="secondary" className="text-[10px] h-4">
                          custom
                        </Badge>
                      )}
                    </div>
                  </SelectItem>
                ))}
                <SelectItem value="__custom__">
                  <span className="text-muted-foreground">Custom model...</span>
                </SelectItem>
              </SelectContent>
            </Select>
          ) : (
            <Input
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="Enter model name"
              className="h-8 text-sm"
            />
          )}
          {model === '__custom__' && (
            <Input
              value=""
              onChange={(e) => setModel(e.target.value)}
              placeholder="Enter custom model ID"
              className="h-8 text-sm mt-2"
            />
          )}
        </div>

        {/* Temperature */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label className="text-xs">Temperature</Label>
            <span className="text-xs text-muted-foreground">
              {temperature.toFixed(1)}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="range"
              min={effectiveParamConfig?.temperature.min ?? 0}
              max={effectiveParamConfig?.temperature.max ?? 2}
              step={effectiveParamConfig?.temperature.step ?? 0.1}
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="flex-1 h-2 rounded-lg appearance-none cursor-pointer bg-muted"
            />
          </div>
          {effectiveParamConfig?.temperature.warning && (
            <p className="text-[10px] text-amber-600 dark:text-amber-400">
              {effectiveParamConfig.temperature.warning}
            </p>
          )}
        </div>

        {/* Max Tokens */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label className="text-xs">
              Max Tokens
              {usesCompletionTokens && (
                <Badge variant="secondary" className="ml-2 text-[10px] h-4">
                  max_completion_tokens
                </Badge>
              )}
            </Label>
          </div>
          <Input
            type="number"
            value={maxTokens}
            onChange={(e) => setMaxTokens(parseInt(e.target.value) || 4096)}
            min={effectiveParamConfig?.max_tokens.min ?? 1}
            max={effectiveParamConfig?.max_tokens.max ?? 128000}
            className="h-8 text-sm"
          />
          <p className="text-[10px] text-muted-foreground">
            Range: {effectiveParamConfig?.max_tokens.min ?? 1} -{' '}
            {(effectiveParamConfig?.max_tokens.max ?? 128000).toLocaleString()}
          </p>
        </div>

        {/* Advanced Parameters Toggle */}
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <Sparkles className="h-3 w-3" />
          {showAdvanced ? 'Hide' : 'Show'} Advanced Parameters
          {showAdvanced ? (
            <ChevronUp className="h-3 w-3" />
          ) : (
            <ChevronDown className="h-3 w-3" />
          )}
        </button>

        {/* Advanced Parameters */}
        {showAdvanced && (
          <div className="space-y-3 pt-2 border-t">
            {/* Top P */}
            {effectiveParamConfig?.top_p && (
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <Label className="text-xs">Top P</Label>
                  <span className="text-xs text-muted-foreground">{topP.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min={effectiveParamConfig.top_p.min}
                  max={effectiveParamConfig.top_p.max}
                  step={effectiveParamConfig.top_p.step ?? 0.05}
                  value={topP}
                  onChange={(e) => setTopP(parseFloat(e.target.value))}
                  className="w-full h-2 rounded-lg appearance-none cursor-pointer bg-muted"
                />
              </div>
            )}

            {/* Top K (Anthropic, Google, Ollama) */}
            {effectiveParamConfig?.top_k && (
              <div className="space-y-1">
                <Label className="text-xs">Top K</Label>
                <Input
                  type="number"
                  value={topK}
                  onChange={(e) => setTopK(parseInt(e.target.value) || 40)}
                  min={effectiveParamConfig.top_k.min}
                  max={effectiveParamConfig.top_k.max}
                  className="h-8 text-sm"
                />
              </div>
            )}

            {/* Frequency Penalty (OpenAI, Azure) */}
            {effectiveParamConfig?.frequency_penalty && (
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <Label className="text-xs">Frequency Penalty</Label>
                  <span className="text-xs text-muted-foreground">
                    {frequencyPenalty.toFixed(1)}
                  </span>
                </div>
                <input
                  type="range"
                  min={effectiveParamConfig.frequency_penalty.min}
                  max={effectiveParamConfig.frequency_penalty.max}
                  step={effectiveParamConfig.frequency_penalty.step ?? 0.1}
                  value={frequencyPenalty}
                  onChange={(e) => setFrequencyPenalty(parseFloat(e.target.value))}
                  className="w-full h-2 rounded-lg appearance-none cursor-pointer bg-muted"
                />
              </div>
            )}

            {/* Presence Penalty (OpenAI, Azure) */}
            {effectiveParamConfig?.presence_penalty && (
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <Label className="text-xs">Presence Penalty</Label>
                  <span className="text-xs text-muted-foreground">
                    {presencePenalty.toFixed(1)}
                  </span>
                </div>
                <input
                  type="range"
                  min={effectiveParamConfig.presence_penalty.min}
                  max={effectiveParamConfig.presence_penalty.max}
                  step={effectiveParamConfig.presence_penalty.step ?? 0.1}
                  value={presencePenalty}
                  onChange={(e) => setPresencePenalty(parseFloat(e.target.value))}
                  className="w-full h-2 rounded-lg appearance-none cursor-pointer bg-muted"
                />
              </div>
            )}
          </div>
        )}

        {/* Validation Warnings */}
        {warnings.length > 0 && (
          <div className="space-y-2">
            {warnings.map((warning, index) => (
              <Alert
                key={index}
                variant={warning.startsWith('Note:') ? 'default' : 'default'}
                className="py-2"
              >
                {warning.startsWith('Note:') ? (
                  <Info className="h-3 w-3" />
                ) : (
                  <AlertTriangle className="h-3 w-3" />
                )}
                <AlertDescription className="text-xs ml-2">
                  {warning}
                </AlertDescription>
              </Alert>
            ))}
          </div>
        )}

        {/* Provider Notes */}
        {providerConfig?.notes && providerConfig.notes.length > 0 && (
          <div className="text-[10px] text-muted-foreground space-y-1 pt-2 border-t">
            {providerConfig.notes.map((note, index) => (
              <p key={index} className="flex items-start gap-1">
                <Info className="h-3 w-3 shrink-0 mt-0.5" />
                {note}
              </p>
            ))}
          </div>
        )}

        {/* Apply Button */}
        <Button onClick={handleApply} className="w-full" size="sm">
          Apply to Config
        </Button>
      </div>
    </div>
  );
}
