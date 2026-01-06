/**
 * LLM Provider Configuration
 *
 * Defines model-specific parameters and constraints for different LLM providers.
 * Used by the UI to show appropriate fields and validation warnings.
 */

export interface ModelInfo {
  id: string;
  name: string;
  usesMaxCompletionTokens?: boolean;
  maxContextTokens?: number;
  notes?: string;
}

export interface ParameterConfig {
  min: number;
  max: number;
  default: number | null;
  step?: number;
  required?: boolean;
  optional?: boolean;
  warning?: string;
  description?: string;
}

export interface ProviderConfig {
  name: string;
  models: ModelInfo[];
  parameters: {
    temperature: ParameterConfig;
    max_tokens: ParameterConfig;
    top_p?: ParameterConfig;
    top_k?: ParameterConfig;
    frequency_penalty?: ParameterConfig;
    presence_penalty?: ParameterConfig;
  };
  notes?: string[];
}

export const LLM_PROVIDER_CONFIG: Record<string, ProviderConfig> = {
  openai: {
    name: 'OpenAI',
    models: [
      { id: 'gpt-4o', name: 'GPT-4o', usesMaxCompletionTokens: true, maxContextTokens: 128000 },
      { id: 'gpt-4o-mini', name: 'GPT-4o Mini', usesMaxCompletionTokens: true, maxContextTokens: 128000 },
      { id: 'gpt-4-turbo', name: 'GPT-4 Turbo', usesMaxCompletionTokens: true, maxContextTokens: 128000 },
      { id: 'gpt-4-turbo-preview', name: 'GPT-4 Turbo Preview', usesMaxCompletionTokens: true, maxContextTokens: 128000 },
      { id: 'gpt-4', name: 'GPT-4', usesMaxCompletionTokens: false, maxContextTokens: 8192 },
      { id: 'gpt-4-32k', name: 'GPT-4 32K', usesMaxCompletionTokens: false, maxContextTokens: 32768 },
      { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', usesMaxCompletionTokens: false, maxContextTokens: 16385 },
      { id: 'o1', name: 'o1', usesMaxCompletionTokens: true, maxContextTokens: 200000, notes: 'Reasoning model' },
      { id: 'o1-mini', name: 'o1 Mini', usesMaxCompletionTokens: true, maxContextTokens: 128000, notes: 'Reasoning model' },
      { id: 'o1-preview', name: 'o1 Preview', usesMaxCompletionTokens: true, maxContextTokens: 128000, notes: 'Reasoning model' },
      { id: 'o3-mini', name: 'o3 Mini', usesMaxCompletionTokens: true, maxContextTokens: 200000, notes: 'Reasoning model' },
    ],
    parameters: {
      temperature: {
        min: 0,
        max: 2,
        default: 0.7,
        step: 0.1,
        description: 'Controls randomness. Lower = more focused, higher = more creative.',
      },
      max_tokens: {
        min: 1,
        max: 128000,
        default: 4096,
        step: 1,
        description: 'Maximum tokens to generate in the response.',
      },
      top_p: {
        min: 0,
        max: 1,
        default: 1,
        step: 0.05,
        optional: true,
        description: 'Nucleus sampling threshold. Alternative to temperature.',
      },
      frequency_penalty: {
        min: -2,
        max: 2,
        default: 0,
        step: 0.1,
        optional: true,
        description: 'Reduce repetition of token sequences.',
      },
      presence_penalty: {
        min: -2,
        max: 2,
        default: 0,
        step: 0.1,
        optional: true,
        description: 'Encourage talking about new topics.',
      },
    },
    notes: [
      'Newer models (gpt-4o, gpt-4-turbo, o1, o3) use max_completion_tokens instead of max_tokens',
      'The backend handles this conversion automatically',
    ],
  },

  anthropic: {
    name: 'Anthropic',
    models: [
      { id: 'claude-sonnet-4-20250514', name: 'Claude Sonnet 4', maxContextTokens: 200000 },
      { id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet', maxContextTokens: 200000 },
      { id: 'claude-3-5-haiku-20241022', name: 'Claude 3.5 Haiku', maxContextTokens: 200000 },
      { id: 'claude-3-opus-20240229', name: 'Claude 3 Opus', maxContextTokens: 200000 },
      { id: 'claude-3-sonnet-20240229', name: 'Claude 3 Sonnet', maxContextTokens: 200000 },
      { id: 'claude-3-haiku-20240307', name: 'Claude 3 Haiku', maxContextTokens: 200000 },
    ],
    parameters: {
      temperature: {
        min: 0,
        max: 1,
        default: 0.7,
        step: 0.1,
        warning: 'Anthropic maximum is 1.0. Values above will be clamped.',
        description: 'Controls randomness. Anthropic supports 0.0 to 1.0 only.',
      },
      max_tokens: {
        min: 1,
        max: 200000,
        default: 4096,
        step: 1,
        required: true,
        description: 'Maximum tokens to generate. Required for Anthropic API.',
      },
      top_p: {
        min: 0,
        max: 1,
        default: 1,
        step: 0.05,
        optional: true,
        description: 'Nucleus sampling threshold.',
      },
      top_k: {
        min: 1,
        max: 500,
        default: null,
        step: 1,
        optional: true,
        description: 'Only sample from top K tokens.',
      },
    },
    notes: [
      'Temperature is clamped to 1.0 maximum (Anthropic API limit)',
      'max_tokens is required for all Anthropic API calls',
    ],
  },

  google: {
    name: 'Google',
    models: [
      { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash', maxContextTokens: 1000000 },
      { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro', maxContextTokens: 2000000 },
      { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash', maxContextTokens: 1000000 },
      { id: 'gemini-pro', name: 'Gemini Pro', maxContextTokens: 32000 },
    ],
    parameters: {
      temperature: {
        min: 0,
        max: 2,
        default: 0.7,
        step: 0.1,
        description: 'Controls randomness in generation.',
      },
      max_tokens: {
        min: 1,
        max: 8192,
        default: 4096,
        step: 1,
        description: 'Maximum output tokens.',
      },
      top_p: {
        min: 0,
        max: 1,
        default: 1,
        step: 0.05,
        optional: true,
        description: 'Nucleus sampling threshold.',
      },
      top_k: {
        min: 1,
        max: 100,
        default: null,
        step: 1,
        optional: true,
        description: 'Top-k sampling.',
      },
    },
    notes: ['Google Gemini support coming soon'],
  },

  azure_openai: {
    name: 'Azure OpenAI',
    models: [
      { id: 'gpt-4o', name: 'GPT-4o (Deployment)', usesMaxCompletionTokens: true },
      { id: 'gpt-4', name: 'GPT-4 (Deployment)', usesMaxCompletionTokens: false },
      { id: 'gpt-35-turbo', name: 'GPT-3.5 Turbo (Deployment)', usesMaxCompletionTokens: false },
    ],
    parameters: {
      temperature: {
        min: 0,
        max: 2,
        default: 0.7,
        step: 0.1,
        description: 'Controls randomness.',
      },
      max_tokens: {
        min: 1,
        max: 128000,
        default: 4096,
        step: 1,
        description: 'Maximum tokens to generate.',
      },
      top_p: {
        min: 0,
        max: 1,
        default: 1,
        step: 0.05,
        optional: true,
        description: 'Nucleus sampling.',
      },
      frequency_penalty: {
        min: -2,
        max: 2,
        default: 0,
        step: 0.1,
        optional: true,
        description: 'Reduce repetition.',
      },
      presence_penalty: {
        min: -2,
        max: 2,
        default: 0,
        step: 0.1,
        optional: true,
        description: 'Encourage new topics.',
      },
    },
    notes: [
      'Azure OpenAI uses deployment names instead of model IDs',
      'Azure OpenAI support coming soon',
    ],
  },

  ollama: {
    name: 'Ollama (Local)',
    models: [
      { id: 'llama3.2', name: 'Llama 3.2' },
      { id: 'llama3.1', name: 'Llama 3.1' },
      { id: 'llama3', name: 'Llama 3' },
      { id: 'llama2', name: 'Llama 2' },
      { id: 'mistral', name: 'Mistral' },
      { id: 'mixtral', name: 'Mixtral' },
      { id: 'codellama', name: 'Code Llama' },
      { id: 'phi3', name: 'Phi-3' },
      { id: 'gemma2', name: 'Gemma 2' },
      { id: 'qwen2.5', name: 'Qwen 2.5' },
    ],
    parameters: {
      temperature: {
        min: 0,
        max: 2,
        default: 0.7,
        step: 0.1,
        description: 'Controls randomness.',
      },
      max_tokens: {
        min: 1,
        max: 32000,
        default: 4096,
        step: 1,
        description: 'Maximum tokens (num_predict in Ollama).',
      },
      top_p: {
        min: 0,
        max: 1,
        default: 1,
        step: 0.05,
        optional: true,
        description: 'Nucleus sampling.',
      },
      top_k: {
        min: 1,
        max: 100,
        default: 40,
        step: 1,
        optional: true,
        description: 'Top-k sampling.',
      },
    },
    notes: [
      'Ollama runs models locally',
      'Model availability depends on what you have pulled',
      'Ollama support coming soon',
    ],
  },

  llamacpp: {
    name: 'LlamaCpp (Local)',
    models: [
      { id: 'custom', name: 'Custom Model', notes: 'Specify model path in base URL config' },
    ],
    parameters: {
      temperature: {
        min: 0,
        max: 2,
        default: 0.7,
        step: 0.1,
        description: 'Controls randomness.',
      },
      max_tokens: {
        min: 1,
        max: 32000,
        default: 4096,
        step: 1,
        description: 'Maximum tokens to generate.',
      },
      top_p: {
        min: 0,
        max: 1,
        default: 1,
        step: 0.05,
        optional: true,
        description: 'Nucleus sampling.',
      },
      top_k: {
        min: 1,
        max: 100,
        default: 40,
        step: 1,
        optional: true,
        description: 'Top-k sampling.',
      },
    },
    notes: [
      'LlamaCpp runs GGUF models locally',
      'LlamaCpp support coming soon',
    ],
  },
};

/**
 * Check if a model requires max_completion_tokens instead of max_tokens
 */
export function requiresMaxCompletionTokens(provider: string, model: string): boolean {
  if (provider !== 'openai') return false;

  const modelLower = model.toLowerCase();

  // o1 and o3 series
  if (modelLower.startsWith('o1') || modelLower.startsWith('o3')) {
    return true;
  }

  // gpt-4o variants
  if (modelLower.includes('gpt-4o')) {
    return true;
  }

  // gpt-4-turbo variants
  if (modelLower.includes('gpt-4-turbo')) {
    return true;
  }

  return false;
}

/**
 * Get validation warnings for a given configuration
 */
export function getConfigValidationWarnings(
  provider: string,
  config: { model?: string; temperature?: number; max_tokens?: number }
): string[] {
  const warnings: string[] = [];
  const providerConfig = LLM_PROVIDER_CONFIG[provider];

  if (!providerConfig) {
    warnings.push(`Unknown provider: ${provider}`);
    return warnings;
  }

  // Temperature warnings
  if (config.temperature !== undefined) {
    if (provider === 'anthropic' && config.temperature > 1) {
      warnings.push(`Temperature ${config.temperature} exceeds Anthropic's maximum of 1.0. It will be clamped to 1.0.`);
    }
  }

  // Max tokens info for newer OpenAI models
  if (config.model && requiresMaxCompletionTokens(provider, config.model)) {
    warnings.push(`Note: ${config.model} uses max_completion_tokens. The backend handles this conversion automatically.`);
  }

  // Model validation
  if (config.model) {
    const knownModels = providerConfig.models.map(m => m.id.toLowerCase());
    const modelLower = config.model.toLowerCase();
    const isKnown = knownModels.some(m => modelLower.includes(m) || m.includes(modelLower));

    if (!isKnown) {
      warnings.push(`Model "${config.model}" is not in the known models list. It may still work if valid.`);
    }
  }

  return warnings;
}

/**
 * Get the default configuration for a provider
 */
export function getDefaultConfig(provider: string): {
  model: string;
  temperature: number;
  max_tokens: number;
} {
  const providerConfig = LLM_PROVIDER_CONFIG[provider];

  if (!providerConfig) {
    return {
      model: 'gpt-4',
      temperature: 0.7,
      max_tokens: 4096,
    };
  }

  return {
    model: providerConfig.models[0]?.id || 'gpt-4',
    temperature: providerConfig.parameters.temperature.default ?? 0.7,
    max_tokens: providerConfig.parameters.max_tokens.default ?? 4096,
  };
}

/**
 * Custom model configuration interface matching types.ts
 */
export interface CustomModelConfig {
  id: string;
  name: string;
  usesMaxCompletionTokens?: boolean;
  maxContextTokens?: number;
  parameters?: {
    temperature?: { min: number; max: number; default: number };
    max_tokens?: { min: number; max: number; default: number };
    top_p?: { min: number; max: number; default: number };
    top_k?: { min: number; max: number; default: number };
    frequency_penalty?: { min: number; max: number; default: number };
    presence_penalty?: { min: number; max: number; default: number };
  };
  notes?: string;
}

/**
 * Merge provider's custom models with default models.
 * Custom models with the same ID override defaults; new IDs are appended.
 */
export function getProviderModels(
  providerType: string,
  customModels?: CustomModelConfig[]
): ModelInfo[] {
  const defaults = LLM_PROVIDER_CONFIG[providerType]?.models || [];

  if (!customModels?.length) {
    return defaults;
  }

  // Create a map of default models
  const merged = [...defaults];

  for (const custom of customModels) {
    const existingIdx = merged.findIndex((m) => m.id === custom.id);
    if (existingIdx >= 0) {
      // Override existing model with custom config
      merged[existingIdx] = {
        ...merged[existingIdx],
        ...custom,
      };
    } else {
      // Add new custom model
      merged.push({
        id: custom.id,
        name: custom.name,
        usesMaxCompletionTokens: custom.usesMaxCompletionTokens,
        maxContextTokens: custom.maxContextTokens,
        notes: custom.notes,
      });
    }
  }

  return merged;
}

/**
 * Get parameter config for a specific model, merging custom overrides
 */
export function getModelParameterConfig(
  providerType: string,
  modelId: string,
  customModels?: CustomModelConfig[]
): ProviderConfig['parameters'] | null {
  const providerConfig = LLM_PROVIDER_CONFIG[providerType];
  if (!providerConfig) return null;

  // Start with default provider parameters
  const params = { ...providerConfig.parameters };

  // Check for custom model parameter overrides
  const customModel = customModels?.find((m) => m.id === modelId);
  if (customModel?.parameters) {
    // Merge custom parameter constraints
    const customParams = customModel.parameters;
    if (customParams.temperature) {
      params.temperature = {
        ...params.temperature,
        min: customParams.temperature.min,
        max: customParams.temperature.max,
        default: customParams.temperature.default,
      };
    }
    if (customParams.max_tokens) {
      params.max_tokens = {
        ...params.max_tokens,
        min: customParams.max_tokens.min,
        max: customParams.max_tokens.max,
        default: customParams.max_tokens.default,
      };
    }
    if (customParams.top_p) {
      params.top_p = {
        ...params.top_p,
        min: customParams.top_p.min,
        max: customParams.top_p.max,
        default: customParams.top_p.default,
      };
    }
    if (customParams.top_k) {
      params.top_k = {
        ...(params.top_k || { min: 1, max: 100, default: null, optional: true }),
        min: customParams.top_k.min,
        max: customParams.top_k.max,
        default: customParams.top_k.default,
      };
    }
    if (customParams.frequency_penalty) {
      params.frequency_penalty = {
        ...(params.frequency_penalty || { min: -2, max: 2, default: 0, optional: true }),
        min: customParams.frequency_penalty.min,
        max: customParams.frequency_penalty.max,
        default: customParams.frequency_penalty.default,
      };
    }
    if (customParams.presence_penalty) {
      params.presence_penalty = {
        ...(params.presence_penalty || { min: -2, max: 2, default: 0, optional: true }),
        min: customParams.presence_penalty.min,
        max: customParams.presence_penalty.max,
        default: customParams.presence_penalty.default,
      };
    }
  }

  return params;
}
