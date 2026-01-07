import { useEffect, useState, useRef } from 'react';
import Editor, { OnMount } from '@monaco-editor/react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  Button,
  Spinner,
  Alert,
  AlertDescription,
} from '@/components/ui';
import {
  useAgent,
  useCreateAgent,
  useUpdateAgent,
  useLLMProviders,
  useTools,
  useAgentTypes,
  getErrorMessage,
} from '@/api/hooks';
import { useUIStore } from '@/stores/uiStore';
import { AgentCreateRequest } from '@/api/types';

interface AgentCodeEditorProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  agentId: number | null;
}

// Default agent configuration template (agent_type_id will be set dynamically)
const DEFAULT_AGENT_CONFIG: AgentCreateRequest = {
  name: 'My Agent',
  description: 'A helpful AI agent',
  agent_type_id: 0, // Will be set to first available agent type
  tags: [],
  config: {
    llm_config: {
      provider: 'openai',
      provider_id: 0,
      model: 'gpt-4',
      temperature: 0.7,
      max_tokens: 4096,
    },
    tool_ids: [],
    prompt_id: null,
    system_prompt: 'You are a helpful AI assistant.',
  },
};

// JSON schema for agent configuration (for Monaco intellisense)
const AGENT_SCHEMA = {
  type: 'object',
  required: ['name', 'agent_type_id', 'config'],
  properties: {
    name: {
      type: 'string',
      description: 'The name of the agent',
      minLength: 1,
      maxLength: 100,
    },
    description: {
      type: 'string',
      description: 'A description of what this agent does',
      maxLength: 2000,
    },
    agent_type_id: {
      type: 'number',
      description: 'ID of the agent type configuration to use',
    },
    tags: {
      type: 'array',
      items: { type: 'string' },
      description: 'Tags for categorizing the agent',
    },
    config: {
      type: 'object',
      required: ['llm_config'],
      properties: {
        llm_config: {
          type: 'object',
          required: ['provider', 'provider_id', 'model'],
          properties: {
            provider: {
              type: 'string',
              enum: ['openai', 'anthropic', 'google', 'azure_openai', 'ollama', 'llamacpp'],
              description: 'LLM provider type',
            },
            provider_id: {
              type: 'number',
              description: 'ID of the configured LLM provider',
            },
            model: {
              type: 'string',
              description: 'Model name (e.g., gpt-4, gpt-4-turbo, claude-3-opus)',
            },
            temperature: {
              type: 'number',
              minimum: 0,
              maximum: 2,
              description: 'Sampling temperature (0-2, lower = more deterministic)',
            },
            max_tokens: {
              type: 'number',
              minimum: 1,
              maximum: 100000,
              description: 'Maximum tokens in response',
            },
          },
        },
        tool_ids: {
          type: 'array',
          items: { type: 'number' },
          description: 'IDs of tools available to this agent',
        },
        prompt_id: {
          type: ['number', 'null'],
          description: 'ID of a prompt template to use',
        },
        system_prompt: {
          type: ['string', 'null'],
          description: 'System prompt instructions for the agent',
        },
        timeout_seconds: {
          type: 'number',
          description: 'Execution timeout in seconds',
        },
      },
    },
  },
};

export function AgentCodeEditor({ open, onClose, onSuccess, agentId }: AgentCodeEditorProps) {
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const editorRef = useRef<any>(null);

  const { theme } = useUIStore();
  const isEditing = agentId !== null;

  const { data: agent, isLoading: isLoadingAgent } = useAgent(agentId ?? undefined);
  const { data: providersData } = useLLMProviders({ pageSize: 100 });
  const { data: toolsData } = useTools({ pageSize: 100 });
  const { data: agentTypesData } = useAgentTypes({ isActive: true });

  const createAgent = useCreateAgent();
  const updateAgent = useUpdateAgent(agentId ?? 0);

  // Determine Monaco theme based on app theme
  const getMonacoTheme = () => {
    if (theme === 'system') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'deepagent-dark' : 'deepagent-light';
    }
    return theme === 'dark' ? 'deepagent-dark' : 'deepagent-light';
  };

  // Initialize editor with agent data or default template
  useEffect(() => {
    if (!open) return;

    if (isEditing && agent) {
      // Convert existing agent to editable format
      const agentConfig: AgentCreateRequest = {
        name: agent.name,
        description: agent.description || undefined,
        agent_type_id: agent.agent_type_id,
        tags: agent.tags || [],
        config: agent.current_version?.config || DEFAULT_AGENT_CONFIG.config,
      };
      setCode(JSON.stringify(agentConfig, null, 2));
    } else if (!isEditing && agentTypesData) {
      // Use default template for new agents
      const defaultConfig = { ...DEFAULT_AGENT_CONFIG };

      // Set agent_type_id to first available agent type
      const defaultAgentType = agentTypesData.agent_types.find(
        at => at.execution_strategy === 'react' && at.is_builtin
      ) || agentTypesData.agent_types[0];
      if (defaultAgentType) {
        defaultConfig.agent_type_id = defaultAgentType.id;
      }

      // Set provider_id to first available provider
      if (providersData?.providers?.length) {
        const firstProvider = providersData.providers[0];
        defaultConfig.config.llm_config.provider_id = firstProvider.id;
        defaultConfig.config.llm_config.provider = firstProvider.provider_type;
      }

      setCode(JSON.stringify(defaultConfig, null, 2));
    }
  }, [open, isEditing, agent, providersData, agentTypesData]);

  // Reset state when dialog closes
  useEffect(() => {
    if (!open) {
      setCode('');
      setError(null);
      setValidationError(null);
    }
  }, [open]);

  // Validate JSON on code change
  useEffect(() => {
    if (!code) {
      setValidationError(null);
      return;
    }

    try {
      const parsed = JSON.parse(code);

      // Basic validation
      if (!parsed.name || typeof parsed.name !== 'string') {
        setValidationError('name is required and must be a string');
        return;
      }

      if (typeof parsed.agent_type_id !== 'number' || parsed.agent_type_id <= 0) {
        setValidationError('agent_type_id is required and must be a positive number');
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
        'editor.background': '#1a1a2e',
        'editor.foreground': '#e4e4e7',
        'editor.lineHighlightBackground': '#27273a',
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
        'editor.background': '#ffffff',
        'editor.foreground': '#1f2937',
        'editor.lineHighlightBackground': '#f3f4f6',
        'editor.selectionBackground': '#add6ff',
        'editorCursor.foreground': '#2563eb',
        'editorLineNumber.foreground': '#9ca3af',
        'editorLineNumber.activeForeground': '#1f2937',
        'editor.inactiveSelectionBackground': '#e5ebf1',
      },
    });

    // Set the initial theme
    monaco.editor.setTheme(getMonacoTheme());

    // Configure JSON language settings with schema
    monaco.languages.json.jsonDefaults.setDiagnosticsOptions({
      validate: true,
      schemas: [
        {
          uri: 'http://deepagentstudio/agent-schema.json',
          fileMatch: ['*'],
          schema: AGENT_SCHEMA,
        },
      ],
    });
  };

  const handleSubmit = async () => {
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);

    try {
      const agentData: AgentCreateRequest = JSON.parse(code);

      if (isEditing) {
        await updateAgent.mutateAsync({
          name: agentData.name,
          description: agentData.description,
          agent_type_id: agentData.agent_type_id,
          tags: agentData.tags,
          config: agentData.config,
        });
      } else {
        await createAgent.mutateAsync(agentData);
      }
      onSuccess();
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

  const isPending = createAgent.isPending || updateAgent.isPending;

  // Build helpful comment header
  const getHelpComment = () => {
    const providers = providersData?.providers || [];
    const tools = toolsData?.tools || [];
    const agentTypes = agentTypesData?.agent_types || [];

    let help = '// Available Agent Types:\n';
    if (agentTypes.length === 0) {
      help += '//   (No agent types available)\n';
    } else {
      agentTypes.forEach(at => {
        const typeLabel = at.is_builtin ? 'Built-in' : (at.strategy_type === 'custom_code' ? 'Custom' : 'User');
        help += `//   - agent_type_id: ${at.id} (${at.name} - ${typeLabel})\n`;
      });
    }

    help += '//\n// Available LLM Providers:\n';
    if (providers.length === 0) {
      help += '//   (No providers configured - add one in Settings)\n';
    } else {
      providers.forEach(p => {
        help += `//   - provider_id: ${p.id} (${p.name} - ${p.provider_type})\n`;
      });
    }

    help += '//\n// Available Tools:\n';
    if (tools.length === 0) {
      help += '//   (No tools available)\n';
    } else {
      tools.forEach(t => {
        help += `//   - tool_id: ${t.id} (${t.name})\n`;
      });
    }

    help += '// --------------------------------------------------------\n\n';

    return help;
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-4xl h-[85vh] flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle>{isEditing ? 'Edit Agent' : 'Create Agent'}</DialogTitle>
        </DialogHeader>

        {isLoadingAgent && isEditing ? (
          <div className="flex justify-center py-8 flex-1">
            <Spinner className="h-8 w-8" />
          </div>
        ) : (
          <div className="flex flex-col flex-1 overflow-hidden gap-4">
            {/* Help text */}
            <div className="text-sm text-muted-foreground bg-muted/50 p-3 rounded-md font-mono whitespace-pre overflow-x-auto">
              {getHelpComment()}
            </div>

            {/* Validation status */}
            {validationError && (
              <Alert variant="destructive">
                <AlertDescription className="font-mono text-sm">
                  {validationError}
                </AlertDescription>
              </Alert>
            )}

            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Monaco Editor */}
            <div className="flex-1 border rounded-md overflow-hidden min-h-0">
              <Editor
                height="100%"
                defaultLanguage="json"
                value={code}
                onChange={(value) => setCode(value || '')}
                onMount={handleEditorMount}
                theme={getMonacoTheme()}
                options={{
                  minimap: { enabled: false },
                  fontSize: 14,
                  fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
                  lineNumbers: 'on',
                  scrollBeyondLastLine: false,
                  wordWrap: 'on',
                  automaticLayout: true,
                  tabSize: 2,
                  formatOnPaste: true,
                  formatOnType: true,
                  suggestOnTriggerCharacters: true,
                  quickSuggestions: true,
                  folding: true,
                  bracketPairColorization: { enabled: true },
                  guides: {
                    bracketPairs: true,
                    indentation: true,
                  },
                }}
              />
            </div>

            {/* Action buttons */}
            <div className="flex justify-between items-center pt-2 border-t flex-shrink-0">
              <Button type="button" variant="outline" size="sm" onClick={handleFormatCode}>
                Format JSON
              </Button>
              <div className="flex gap-2">
                <Button type="button" variant="outline" onClick={onClose}>
                  Cancel
                </Button>
                <Button
                  onClick={handleSubmit}
                  disabled={isPending || !!validationError}
                >
                  {isPending ? (
                    <Spinner className="h-4 w-4" />
                  ) : isEditing ? (
                    'Save Changes'
                  ) : (
                    'Create Agent'
                  )}
                </Button>
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
