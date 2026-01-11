import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Button,
  Input,
  Textarea,
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
  Breadcrumb,
  Checkbox,
} from '@/components/ui';
import {
  Save,
  X,
  Database,
  AlertCircle,
  FlaskConical,
  Settings,
  ClipboardList,
} from 'lucide-react';
import {
  useEvaluation,
  useCreateEvaluation,
  useUpdateEvaluation,
  useDatasets,
  useEvaluators,
  getErrorMessage,
} from '@/api/hooks';
import type { EvaluationConfig } from '@/api/types';

export function EvaluationEditorPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const isEditing = id !== undefined && id !== 'new';
  const evaluationId = isEditing ? parseInt(id) : null;

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [datasetId, setDatasetId] = useState<number | null>(null);
  const [evaluatorIds, setEvaluatorIds] = useState<number[]>([]);
  const [config, setConfig] = useState<EvaluationConfig>({
    concurrency: 3,
    timeout_per_example_ms: 60000,
  });

  // Editor state
  const [error, setError] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Data hooks
  const { data: evaluation, isLoading: isLoadingEvaluation } = useEvaluation(
    evaluationId ?? undefined
  );
  const { data: datasetsData } = useDatasets({ page: 1, pageSize: 100 });
  const { data: evaluatorsData } = useEvaluators({ page: 1, pageSize: 100 });

  const createEvaluation = useCreateEvaluation();
  const updateEvaluation = useUpdateEvaluation(evaluationId ?? 0);

  // Initialize with evaluation data
  useEffect(() => {
    if (isEditing && evaluation) {
      setName(evaluation.name);
      setDescription(evaluation.description || '');
      setDatasetId(evaluation.dataset_id);
      setEvaluatorIds(evaluation.evaluators?.map((e) => e.id) || []);
      setConfig(evaluation.config || { concurrency: 3, timeout_per_example_ms: 60000 });
      setHasUnsavedChanges(false);
    } else if (!isEditing) {
      setName('');
      setDescription('');
      setDatasetId(null);
      setEvaluatorIds([]);
      setConfig({ concurrency: 3, timeout_per_example_ms: 60000 });
      setHasUnsavedChanges(false);
    }
  }, [isEditing, evaluation]);

  // Track unsaved changes
  useEffect(() => {
    if (!isLoadingEvaluation && name) {
      setHasUnsavedChanges(true);
    }
  }, [name, description, datasetId, evaluatorIds, config, isLoadingEvaluation]);

  const handleSave = async () => {
    setError(null);

    if (!name.trim()) {
      setError('Name is required');
      return;
    }

    if (!isEditing && !datasetId) {
      setError('Dataset is required');
      return;
    }

    if (evaluatorIds.length === 0) {
      setError('At least one evaluator is required');
      return;
    }

    try {
      if (isEditing) {
        await updateEvaluation.mutateAsync({
          name: name.trim(),
          description: description.trim() || undefined,
          evaluator_ids: evaluatorIds,
          config,
        });
        setHasUnsavedChanges(false);
        navigate(`/evaluations/${evaluationId}`);
      } else {
        const created = await createEvaluation.mutateAsync({
          name: name.trim(),
          description: description.trim() || undefined,
          dataset_id: datasetId!,
          evaluator_ids: evaluatorIds,
          config,
        });
        setHasUnsavedChanges(false);
        navigate(`/evaluations/${created.id}`);
      }
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const handleCancel = () => {
    if (isEditing) {
      navigate(`/evaluations/${evaluationId}`);
    } else {
      navigate('/evaluations?tab=evaluations');
    }
  };

  const toggleEvaluator = (evaluatorId: number) => {
    setEvaluatorIds((prev) =>
      prev.includes(evaluatorId)
        ? prev.filter((id) => id !== evaluatorId)
        : [...prev, evaluatorId]
    );
  };

  if (isLoadingEvaluation && isEditing) {
    return (
      <div className="container mx-auto py-6 px-4 max-w-4xl">
        <div className="flex justify-center py-12">
          <Spinner size="lg" />
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 px-4 max-w-4xl">
      {/* Breadcrumb */}
      <Breadcrumb
        className="mb-4"
        items={[
          { label: 'Evaluations', href: '/evaluations?tab=evaluations', icon: ClipboardList },
          ...(isEditing && evaluation
            ? [
                { label: evaluation.name, href: `/evaluations/${evaluationId}` },
                { label: 'Edit' },
              ]
            : [{ label: 'New Evaluation' }]),
        ]}
      />

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">
            {isEditing ? 'Edit Evaluation' : 'New Evaluation'}
          </h1>
          <p className="text-muted-foreground mt-1">
            {isEditing
              ? 'Update evaluation configuration'
              : 'Create a reusable evaluation configuration'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleCancel}>
            <X className="h-4 w-4 mr-2" />
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={
              createEvaluation.isPending ||
              updateEvaluation.isPending ||
              !hasUnsavedChanges
            }
          >
            <Save className="h-4 w-4 mr-2" />
            {createEvaluation.isPending || updateEvaluation.isPending
              ? 'Saving...'
              : 'Save'}
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="space-y-6">
        {/* Basic Info */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Basic Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name *</Label>
              <Input
                id="name"
                placeholder="e.g., Math Problem Evaluation"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Describe what this evaluation tests..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
              />
            </div>
          </CardContent>
        </Card>

        {/* Dataset Selection */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Database className="h-5 w-5" />
              Dataset
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isEditing ? (
              <div className="p-4 bg-muted/50 rounded-lg">
                <p className="font-medium">{evaluation?.dataset?.name || 'Unknown'}</p>
                <p className="text-sm text-muted-foreground">
                  {evaluation?.dataset?.example_count || 0} examples
                </p>
                <p className="text-xs text-muted-foreground mt-2">
                  Dataset cannot be changed after creation.
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                <Label>Select Dataset *</Label>
                <Select
                  value={datasetId?.toString() || ''}
                  onValueChange={(v) => setDatasetId(parseInt(v))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Choose a dataset" />
                  </SelectTrigger>
                  <SelectContent>
                    {datasetsData?.datasets.map((dataset) => (
                      <SelectItem key={dataset.id} value={dataset.id.toString()}>
                        {dataset.name} ({dataset.example_count} examples)
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {datasetsData?.datasets.length === 0 && (
                  <p className="text-sm text-muted-foreground">
                    No datasets available.{' '}
                    <Button
                      variant="link"
                      className="p-0 h-auto"
                      onClick={() => navigate('/evaluations/datasets/new')}
                    >
                      Create one first.
                    </Button>
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Evaluators Selection */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <FlaskConical className="h-5 w-5" />
              Evaluators ({evaluatorIds.length} selected)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Label>Select Evaluators *</Label>
              <p className="text-sm text-muted-foreground mb-3">
                Choose one or more evaluators to score agent responses.
              </p>
              {evaluatorsData?.evaluators.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No evaluators available.{' '}
                  <Button
                    variant="link"
                    className="p-0 h-auto"
                    onClick={() => navigate('/evaluations/evaluators/new')}
                  >
                    Create one first.
                  </Button>
                </p>
              ) : (
                <div className="grid gap-2 max-h-64 overflow-y-auto border rounded-lg p-2">
                  {evaluatorsData?.evaluators.map((evaluator) => (
                    <div
                      key={evaluator.id}
                      className="flex items-center space-x-3 p-2 hover:bg-muted/50 rounded cursor-pointer"
                      onClick={() => toggleEvaluator(evaluator.id)}
                    >
                      <Checkbox
                        checked={evaluatorIds.includes(evaluator.id)}
                        onCheckedChange={() => toggleEvaluator(evaluator.id)}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm">{evaluator.name}</p>
                        <p className="text-xs text-muted-foreground truncate">
                          {evaluator.type} • {evaluator.description || 'No description'}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Config */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Configuration
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="concurrency">Concurrency</Label>
                <Input
                  id="concurrency"
                  type="number"
                  min={1}
                  max={10}
                  value={config.concurrency || 3}
                  onChange={(e) =>
                    setConfig({ ...config, concurrency: parseInt(e.target.value) || 3 })
                  }
                />
                <p className="text-xs text-muted-foreground">
                  Number of examples to process in parallel
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="timeout">Timeout (seconds)</Label>
                <Input
                  id="timeout"
                  type="number"
                  min={10}
                  max={600}
                  value={(config.timeout_per_example_ms || 60000) / 1000}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      timeout_per_example_ms: (parseInt(e.target.value) || 60) * 1000,
                    })
                  }
                />
                <p className="text-xs text-muted-foreground">
                  Max time per example in seconds
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="sample_size">Sample Size (optional)</Label>
              <Input
                id="sample_size"
                type="number"
                min={1}
                placeholder="All examples"
                value={config.sample_size || ''}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    sample_size: e.target.value ? parseInt(e.target.value) : undefined,
                  })
                }
              />
              <p className="text-xs text-muted-foreground">
                Limit to a random sample of examples (leave empty for all)
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
