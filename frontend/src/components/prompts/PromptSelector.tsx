import { useEffect, useState, useMemo } from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Input,
  Label,
  Badge,
  Textarea,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Spinner,
} from '@/components/ui';
import { usePrompts, usePrompt } from '@/api/hooks';
import { FileText, Variable, Eye, Pencil } from 'lucide-react';

interface PromptSelectorProps {
  selectedPromptId: number | null;
  promptVariables: Record<string, string>;
  systemPromptOverride: string;
  usePromptLibrary: boolean;
  onChange: (config: {
    prompt_id: number | null;
    prompt_variables: Record<string, string>;
    system_prompt: string;
    use_prompt_library: boolean;
  }) => void;
}

export function PromptSelector({
  selectedPromptId,
  promptVariables,
  systemPromptOverride,
  usePromptLibrary,
  onChange,
}: PromptSelectorProps) {
  const [variableValues, setVariableValues] = useState<Record<string, string>>(promptVariables);

  // Load all prompts for dropdown
  const { data: promptsData, isLoading: isLoadingPrompts } = usePrompts({ pageSize: 100 });

  // Load selected prompt details
  const { data: selectedPrompt, isLoading: isLoadingPrompt } = usePrompt(
    selectedPromptId ?? undefined
  );

  // Extract variables from the selected prompt's template
  const detectedVariables = useMemo(() => {
    if (!selectedPrompt?.current_version?.template) return [];
    const matches = selectedPrompt.current_version.template.match(/\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g) || [];
    return [...new Set(matches.map((m) => m.slice(1, -1)))];
  }, [selectedPrompt?.current_version?.template]);

  // Sync variable values with prop changes
  useEffect(() => {
    setVariableValues(promptVariables);
  }, [promptVariables]);

  // Render the prompt preview with variable substitution
  const renderedPreview = useMemo(() => {
    if (!selectedPrompt?.current_version?.template) return '';
    let result = selectedPrompt.current_version.template;
    for (const [key, value] of Object.entries(variableValues)) {
      result = result.replace(new RegExp(`\\{${key}\\}`, 'g'), value || `{${key}}`);
    }
    return result;
  }, [selectedPrompt?.current_version?.template, variableValues]);

  const handlePromptChange = (promptId: string) => {
    const id = promptId === 'none' ? null : parseInt(promptId);
    onChange({
      prompt_id: id,
      prompt_variables: id ? variableValues : {},
      system_prompt: systemPromptOverride,
      use_prompt_library: usePromptLibrary,
    });
  };

  const handleVariableChange = (varName: string, value: string) => {
    const newVariables = { ...variableValues, [varName]: value };
    setVariableValues(newVariables);
    onChange({
      prompt_id: selectedPromptId,
      prompt_variables: newVariables,
      system_prompt: systemPromptOverride,
      use_prompt_library: usePromptLibrary,
    });
  };

  const handleSystemPromptChange = (value: string) => {
    onChange({
      prompt_id: selectedPromptId,
      prompt_variables: variableValues,
      system_prompt: value,
      use_prompt_library: usePromptLibrary,
    });
  };

  const handleModeChange = (useLibrary: boolean) => {
    onChange({
      prompt_id: useLibrary ? selectedPromptId : null,
      prompt_variables: useLibrary ? variableValues : {},
      system_prompt: systemPromptOverride,
      use_prompt_library: useLibrary,
    });
  };

  const prompts = promptsData?.prompts || [];

  return (
    <div className="space-y-4">
      {/* Mode Toggle */}
      <Tabs
        value={usePromptLibrary ? 'library' : 'custom'}
        onValueChange={(v) => handleModeChange(v === 'library')}
        className="w-full"
      >
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="library" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Prompt Library
          </TabsTrigger>
          <TabsTrigger value="custom" className="flex items-center gap-2">
            <Pencil className="h-4 w-4" />
            Custom Prompt
          </TabsTrigger>
        </TabsList>

        <TabsContent value="library" className="space-y-4 mt-4">
          {/* Prompt Selector Dropdown */}
          <div className="space-y-2">
            <Label>Select Prompt</Label>
            {isLoadingPrompts ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Spinner className="h-4 w-4" />
                Loading prompts...
              </div>
            ) : (
              <Select
                value={selectedPromptId?.toString() || 'none'}
                onValueChange={handlePromptChange}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a prompt from library" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No prompt selected</SelectItem>
                  {prompts.map((prompt) => (
                    <SelectItem key={prompt.id} value={prompt.id.toString()}>
                      <div className="flex items-center gap-2">
                        <span>{prompt.name}</span>
                        <Badge variant="outline" className="text-xs">
                          {prompt.use_case}
                        </Badge>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          {/* Selected Prompt Details */}
          {selectedPromptId && (
            <>
              {isLoadingPrompt ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Spinner className="h-4 w-4" />
                  Loading prompt details...
                </div>
              ) : selectedPrompt ? (
                <div className="space-y-4">
                  {/* Prompt Info */}
                  <div className="rounded-md border p-3 bg-muted/30">
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="font-medium">{selectedPrompt.name}</h4>
                        {selectedPrompt.description && (
                          <p className="text-sm text-muted-foreground mt-1">
                            {selectedPrompt.description}
                          </p>
                        )}
                      </div>
                      <Badge variant="secondary">
                        v{selectedPrompt.current_version?.version_number || 1}
                      </Badge>
                    </div>
                  </div>

                  {/* Variable Inputs */}
                  {detectedVariables.length > 0 && (
                    <div className="space-y-3">
                      <div className="flex items-center gap-2">
                        <Variable className="h-4 w-4" />
                        <Label>Template Variables</Label>
                      </div>
                      <div className="grid gap-3">
                        {detectedVariables.map((varName) => (
                          <div key={varName} className="space-y-1">
                            <Label htmlFor={`var-${varName}`} className="text-sm">
                              {varName}
                            </Label>
                            <Input
                              id={`var-${varName}`}
                              placeholder={`Enter value for {${varName}}`}
                              value={variableValues[varName] || ''}
                              onChange={(e) => handleVariableChange(varName, e.target.value)}
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Preview */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Eye className="h-4 w-4" />
                      <Label>Preview</Label>
                    </div>
                    <div className="rounded-md border p-3 bg-muted/50 max-h-[200px] overflow-y-auto">
                      <pre className="text-sm whitespace-pre-wrap font-mono">
                        {renderedPreview}
                      </pre>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-sm text-muted-foreground">
                  Prompt not found
                </div>
              )}
            </>
          )}

          {!selectedPromptId && (
            <p className="text-sm text-muted-foreground">
              Select a prompt from your library to use as the system prompt for this agent.
            </p>
          )}
        </TabsContent>

        <TabsContent value="custom" className="space-y-4 mt-4">
          {/* Custom System Prompt */}
          <div className="space-y-2">
            <Label>System Prompt</Label>
            <Textarea
              placeholder="You are a helpful assistant..."
              className="min-h-[200px] font-mono text-sm"
              value={systemPromptOverride}
              onChange={(e) => handleSystemPromptChange(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Enter a custom system prompt that defines the agent's behavior and personality.
            </p>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
