import { useState } from 'react';
import {
  Button,
  Input,
  Label,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  Badge,
  Checkbox,
} from '@/components/ui';
import {
  Plus,
  Pencil,
  Trash2,
  ChevronDown,
  ChevronUp,
  Cpu,
} from 'lucide-react';
import { CustomModelConfig } from '@/api/types';

interface CustomModelsEditorProps {
  models: CustomModelConfig[];
  onChange: (models: CustomModelConfig[]) => void;
}

interface ModelFormState {
  id: string;
  name: string;
  usesMaxCompletionTokens: boolean;
  maxContextTokens: string;
  notes: string;
  parameters: {
    temperature: { enabled: boolean; min: string; max: string; default: string };
    max_tokens: { enabled: boolean; min: string; max: string; default: string };
    top_p: { enabled: boolean; min: string; max: string; default: string };
    top_k: { enabled: boolean; min: string; max: string; default: string };
    frequency_penalty: { enabled: boolean; min: string; max: string; default: string };
    presence_penalty: { enabled: boolean; min: string; max: string; default: string };
  };
}

const defaultFormState: ModelFormState = {
  id: '',
  name: '',
  usesMaxCompletionTokens: false,
  maxContextTokens: '',
  notes: '',
  parameters: {
    temperature: { enabled: false, min: '0', max: '2', default: '0.7' },
    max_tokens: { enabled: false, min: '1', max: '128000', default: '4096' },
    top_p: { enabled: false, min: '0', max: '1', default: '1' },
    top_k: { enabled: false, min: '1', max: '100', default: '40' },
    frequency_penalty: { enabled: false, min: '-2', max: '2', default: '0' },
    presence_penalty: { enabled: false, min: '-2', max: '2', default: '0' },
  },
};

function modelToFormState(model: CustomModelConfig): ModelFormState {
  return {
    id: model.id,
    name: model.name,
    usesMaxCompletionTokens: model.usesMaxCompletionTokens ?? false,
    maxContextTokens: model.maxContextTokens?.toString() ?? '',
    notes: model.notes ?? '',
    parameters: {
      temperature: model.parameters?.temperature
        ? { enabled: true, min: model.parameters.temperature.min.toString(), max: model.parameters.temperature.max.toString(), default: model.parameters.temperature.default.toString() }
        : { enabled: false, min: '0', max: '2', default: '0.7' },
      max_tokens: model.parameters?.max_tokens
        ? { enabled: true, min: model.parameters.max_tokens.min.toString(), max: model.parameters.max_tokens.max.toString(), default: model.parameters.max_tokens.default.toString() }
        : { enabled: false, min: '1', max: '128000', default: '4096' },
      top_p: model.parameters?.top_p
        ? { enabled: true, min: model.parameters.top_p.min.toString(), max: model.parameters.top_p.max.toString(), default: model.parameters.top_p.default.toString() }
        : { enabled: false, min: '0', max: '1', default: '1' },
      top_k: model.parameters?.top_k
        ? { enabled: true, min: model.parameters.top_k.min.toString(), max: model.parameters.top_k.max.toString(), default: model.parameters.top_k.default.toString() }
        : { enabled: false, min: '1', max: '100', default: '40' },
      frequency_penalty: model.parameters?.frequency_penalty
        ? { enabled: true, min: model.parameters.frequency_penalty.min.toString(), max: model.parameters.frequency_penalty.max.toString(), default: model.parameters.frequency_penalty.default.toString() }
        : { enabled: false, min: '-2', max: '2', default: '0' },
      presence_penalty: model.parameters?.presence_penalty
        ? { enabled: true, min: model.parameters.presence_penalty.min.toString(), max: model.parameters.presence_penalty.max.toString(), default: model.parameters.presence_penalty.default.toString() }
        : { enabled: false, min: '-2', max: '2', default: '0' },
    },
  };
}

function formStateToModel(state: ModelFormState): CustomModelConfig {
  const model: CustomModelConfig = {
    id: state.id,
    name: state.name,
  };

  if (state.usesMaxCompletionTokens) {
    model.usesMaxCompletionTokens = true;
  }

  if (state.maxContextTokens) {
    model.maxContextTokens = parseInt(state.maxContextTokens);
  }

  if (state.notes) {
    model.notes = state.notes;
  }

  // Build parameters object
  const parameters: CustomModelConfig['parameters'] = {};

  const paramKeys = ['temperature', 'max_tokens', 'top_p', 'top_k', 'frequency_penalty', 'presence_penalty'] as const;

  for (const key of paramKeys) {
    const param = state.parameters[key];
    if (param.enabled) {
      parameters[key] = {
        min: parseFloat(param.min),
        max: parseFloat(param.max),
        default: parseFloat(param.default),
      };
    }
  }

  if (Object.keys(parameters).length > 0) {
    model.parameters = parameters;
  }

  return model;
}

export function CustomModelsEditor({ models, onChange }: CustomModelsEditorProps) {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [formState, setFormState] = useState<ModelFormState>(defaultFormState);
  const [showParameters, setShowParameters] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const handleAdd = () => {
    setEditingIndex(null);
    setFormState(defaultFormState);
    setShowParameters(false);
    setFormError(null);
    setIsDialogOpen(true);
  };

  const handleEdit = (index: number) => {
    setEditingIndex(index);
    setFormState(modelToFormState(models[index]));
    setShowParameters(models[index].parameters !== undefined);
    setFormError(null);
    setIsDialogOpen(true);
  };

  const handleDelete = (index: number) => {
    const newModels = [...models];
    newModels.splice(index, 1);
    onChange(newModels);
  };

  const handleSave = () => {
    // Validation
    if (!formState.id.trim()) {
      setFormError('Model ID is required');
      return;
    }
    if (!formState.name.trim()) {
      setFormError('Display name is required');
      return;
    }

    // Check for duplicate IDs (except when editing the same model)
    const isDuplicate = models.some((m, i) =>
      m.id === formState.id && i !== editingIndex
    );
    if (isDuplicate) {
      setFormError('A model with this ID already exists');
      return;
    }

    const model = formStateToModel(formState);

    if (editingIndex !== null) {
      const newModels = [...models];
      newModels[editingIndex] = model;
      onChange(newModels);
    } else {
      onChange([...models, model]);
    }

    setIsDialogOpen(false);
  };

  const updateParam = (
    paramName: keyof ModelFormState['parameters'],
    field: 'enabled' | 'min' | 'max' | 'default',
    value: string | boolean
  ) => {
    setFormState((prev) => ({
      ...prev,
      parameters: {
        ...prev.parameters,
        [paramName]: {
          ...prev.parameters[paramName],
          [field]: value,
        },
      },
    }));
  };

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Label className="text-sm font-medium">Custom Models</Label>
        <Button type="button" variant="outline" size="sm" onClick={handleAdd}>
          <Plus className="h-3 w-3 mr-1" />
          Add Model
        </Button>
      </div>

      {/* Models List */}
      {models.length === 0 ? (
        <div className="text-sm text-muted-foreground py-4 text-center border rounded-md border-dashed">
          No custom models defined. Click "Add Model" to add one.
        </div>
      ) : (
        <div className="space-y-2">
          {models.map((model, index) => (
            <div
              key={model.id}
              className="flex items-center justify-between p-3 border rounded-md bg-muted/30"
            >
              <div className="flex items-center gap-3">
                <Cpu className="h-4 w-4 text-muted-foreground" />
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">{model.name}</span>
                    <code className="text-xs bg-muted px-1 py-0.5 rounded">
                      {model.id}
                    </code>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    {model.usesMaxCompletionTokens && (
                      <Badge variant="secondary" className="text-[10px] h-4">
                        max_completion_tokens
                      </Badge>
                    )}
                    {model.maxContextTokens && (
                      <span className="text-[10px] text-muted-foreground">
                        {model.maxContextTokens.toLocaleString()} ctx
                      </span>
                    )}
                    {model.parameters && (
                      <span className="text-[10px] text-muted-foreground">
                        custom params
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => handleEdit(index)}
                >
                  <Pencil className="h-3 w-3" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => handleDelete(index)}
                  className="text-destructive hover:text-destructive"
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add/Edit Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingIndex !== null ? 'Edit Custom Model' : 'Add Custom Model'}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {formError && (
              <div className="text-sm text-destructive bg-destructive/10 p-2 rounded">
                {formError}
              </div>
            )}

            {/* Model ID */}
            <div className="space-y-2">
              <Label htmlFor="model-id">Model ID *</Label>
              <Input
                id="model-id"
                value={formState.id}
                onChange={(e) => setFormState((prev) => ({ ...prev, id: e.target.value }))}
                placeholder="gpt-5-mini"
              />
              <p className="text-xs text-muted-foreground">
                The exact model name to send to the API
              </p>
            </div>

            {/* Display Name */}
            <div className="space-y-2">
              <Label htmlFor="model-name">Display Name *</Label>
              <Input
                id="model-name"
                value={formState.name}
                onChange={(e) => setFormState((prev) => ({ ...prev, name: e.target.value }))}
                placeholder="GPT-5 Mini"
              />
            </div>

            {/* Uses max_completion_tokens */}
            <div className="flex items-center gap-2">
              <Checkbox
                id="uses-completion-tokens"
                checked={formState.usesMaxCompletionTokens}
                onCheckedChange={(checked) =>
                  setFormState((prev) => ({
                    ...prev,
                    usesMaxCompletionTokens: checked === true,
                  }))
                }
              />
              <Label htmlFor="uses-completion-tokens" className="text-sm font-normal cursor-pointer">
                Uses max_completion_tokens (instead of max_tokens)
              </Label>
            </div>

            {/* Max Context Tokens */}
            <div className="space-y-2">
              <Label htmlFor="max-context">Max Context Tokens</Label>
              <Input
                id="max-context"
                type="number"
                value={formState.maxContextTokens}
                onChange={(e) =>
                  setFormState((prev) => ({ ...prev, maxContextTokens: e.target.value }))
                }
                placeholder="128000"
              />
            </div>

            {/* Parameter Constraints Toggle */}
            <button
              type="button"
              onClick={() => setShowParameters(!showParameters)}
              className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors w-full"
            >
              {showParameters ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
              Parameter Constraints
            </button>

            {/* Parameter Constraints */}
            {showParameters && (
              <div className="space-y-3 border-t pt-3">
                {(['temperature', 'max_tokens', 'top_p', 'top_k', 'frequency_penalty', 'presence_penalty'] as const).map(
                  (paramName) => (
                    <ParameterConstraintRow
                      key={paramName}
                      name={paramName}
                      label={paramName.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                      value={formState.parameters[paramName]}
                      onChange={(field, value) => updateParam(paramName, field, value)}
                    />
                  )
                )}
              </div>
            )}

            {/* Notes */}
            <div className="space-y-2">
              <Label htmlFor="model-notes">Notes</Label>
              <Input
                id="model-notes"
                value={formState.notes}
                onChange={(e) => setFormState((prev) => ({ ...prev, notes: e.target.value }))}
                placeholder="Optional notes about this model"
              />
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>
              Cancel
            </Button>
            <Button type="button" onClick={handleSave}>
              {editingIndex !== null ? 'Save Changes' : 'Add Model'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

interface ParameterConstraintRowProps {
  name: string;
  label: string;
  value: { enabled: boolean; min: string; max: string; default: string };
  onChange: (field: 'enabled' | 'min' | 'max' | 'default', value: string | boolean) => void;
}

function ParameterConstraintRow({ name, label, value, onChange }: ParameterConstraintRowProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Checkbox
          id={`param-${name}`}
          checked={value.enabled}
          onCheckedChange={(checked) => onChange('enabled', checked === true)}
        />
        <Label htmlFor={`param-${name}`} className="text-sm font-normal cursor-pointer">
          {label}
        </Label>
      </div>
      {value.enabled && (
        <div className="grid grid-cols-3 gap-2 ml-6">
          <div>
            <Label className="text-xs text-muted-foreground">Min</Label>
            <Input
              type="number"
              value={value.min}
              onChange={(e) => onChange('min', e.target.value)}
              className="h-7 text-xs"
              step="any"
            />
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">Max</Label>
            <Input
              type="number"
              value={value.max}
              onChange={(e) => onChange('max', e.target.value)}
              className="h-7 text-xs"
              step="any"
            />
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">Default</Label>
            <Input
              type="number"
              value={value.default}
              onChange={(e) => onChange('default', e.target.value)}
              className="h-7 text-xs"
              step="any"
            />
          </div>
        </div>
      )}
    </div>
  );
}
