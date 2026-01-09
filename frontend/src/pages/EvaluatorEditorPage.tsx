import { useEffect, useState } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
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
  Label,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Breadcrumb,
} from '@/components/ui';
import {
  Save,
  X,
  FlaskConical,
  AlertCircle,
  Copy,
  Info,
  Play,
  CheckCircle,
  ClipboardList,
} from 'lucide-react';
import {
  useEvaluator,
  useCreateEvaluator,
  useUpdateEvaluator,
  useCloneEvaluator,
  useTestEvaluator,
  getErrorMessage,
} from '@/api/hooks';
import { useUIStore } from '@/stores/uiStore';
import { EvaluatorType, EvaluatorCategory } from '@/api/types';

const EVALUATOR_CATEGORIES: { value: EvaluatorCategory; label: string }[] = [
  { value: 'output', label: 'Output' },
  { value: 'run_metadata', label: 'Run Metadata' },
];

const OUTPUT_EVALUATOR_TYPES: { value: EvaluatorType; label: string; description: string }[] = [
  { value: 'exact_match', label: 'Exact Match', description: 'Output exactly matches expected' },
  { value: 'contains', label: 'Contains', description: 'Output contains expected string' },
  { value: 'regex_match', label: 'Regex Match', description: 'Output matches regex pattern' },
  { value: 'json_match', label: 'JSON Match', description: 'JSON structure comparison' },
  { value: 'semantic_similarity', label: 'Semantic Similarity', description: 'Embedding-based similarity' },
  { value: 'llm_judge', label: 'LLM Judge', description: 'LLM-based evaluation' },
  { value: 'custom_code', label: 'Custom Code', description: 'Custom Python evaluation code' },
];

const RUN_METADATA_EVALUATOR_TYPES: { value: EvaluatorType; label: string; description: string }[] = [
  { value: 'token_efficiency', label: 'Token Efficiency', description: 'Evaluate token usage' },
  { value: 'latency_threshold', label: 'Latency Threshold', description: 'Check response time' },
  { value: 'cost_threshold', label: 'Cost Threshold', description: 'Check execution cost' },
  { value: 'chain_length', label: 'Chain Length', description: 'Evaluate steps taken' },
  { value: 'tool_call_success_rate', label: 'Tool Success Rate', description: 'Tool call success %' },
  { value: 'tool_selection', label: 'Tool Selection', description: 'Validate tool choices' },
  { value: 'error_rate', label: 'Error Rate', description: 'Evaluate error frequency' },
  { value: 'span_count', label: 'Span Count', description: 'Evaluate trace spans' },
  { value: 'custom_metadata', label: 'Custom Metadata', description: 'Custom metadata evaluation' },
];

const DEFAULT_CONFIGS: Record<string, Record<string, unknown>> = {
  exact_match: { case_sensitive: true, strip_whitespace: true },
  contains: { case_sensitive: false },
  regex_match: { flags: ['IGNORECASE'] },
  json_match: { ignore_order: true, subset_match: false },
  semantic_similarity: { model: 'text-embedding-3-small', threshold: 0.85 },
  llm_judge: {
    model: 'gpt-4o-mini',
    criteria: 'correctness',
    prompt_template: `You are evaluating an AI assistant's response.

Input: {input}
Expected Output: {expected_output}
Actual Output: {actual_output}

Evaluate if the actual output is correct and complete.

Respond with a JSON object:
{
  "score": <0.0-1.0>,
  "passed": <true/false>,
  "reasoning": "<brief explanation>"
}`,
  },
  custom_code: {
    code: `def evaluate(input_data, expected_output, actual_output, run_metadata):
    """
    Custom evaluation function.

    Args:
        input_data: The input given to the agent
        expected_output: The expected output
        actual_output: The agent's actual output
        run_metadata: Metadata from the run (tokens, latency, etc.)

    Returns:
        dict with keys: score (0-1), passed (bool), feedback (str)
    """
    # Your evaluation logic here
    passed = actual_output == expected_output
    return {
        "score": 1.0 if passed else 0.0,
        "passed": passed,
        "feedback": "Match!" if passed else "Output does not match expected"
    }
`,
  },
  token_efficiency: { max_input_tokens: 5000, max_output_tokens: 2000, max_total_tokens: 7000 },
  latency_threshold: { max_ms: 30000, warning_ms: 15000 },
  cost_threshold: { max_cost_usd: 0.1, warning_cost_usd: 0.05 },
  chain_length: { max_steps: 10, warning_steps: 5 },
  tool_call_success_rate: { min_success_rate: 0.9 },
  tool_selection: { mode: 'required', required_tools: [], forbidden_tools: [] },
  error_rate: { max_errors: 2, max_retries: 3 },
  span_count: { max_llm_spans: 10, max_tool_spans: 20, max_total_spans: 50 },
  custom_metadata: { expression: 'run_metadata.get("custom_field") == expected_value' },
};

export function EvaluatorEditorPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { theme } = useUIStore();

  const isEditing = id !== undefined && id !== 'new';
  const evaluatorId = isEditing ? parseInt(id) : null;
  const cloneId = searchParams.get('clone');

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState<EvaluatorCategory>('output');
  const [type, setType] = useState<EvaluatorType>('exact_match');
  const [config, setConfig] = useState('{}');

  // Editor state
  const [error, setError] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Test state
  const [testInput, setTestInput] = useState('What is 2+2?');
  const [testExpected, setTestExpected] = useState('4');
  const [testActual, setTestActual] = useState('4');
  const [testResult, setTestResult] = useState<{
    score: number;
    passed: boolean;
    feedback?: string;
  } | null>(null);
  const [testError, setTestError] = useState<string | null>(null);

  // Data hooks
  const { data: evaluator, isLoading: isLoadingEvaluator } = useEvaluator(evaluatorId ?? undefined);
  const { data: evaluatorToClone, isLoading: isLoadingClone } = useEvaluator(
    cloneId ? parseInt(cloneId) : undefined
  );

  const createEvaluator = useCreateEvaluator();
  const updateEvaluator = useUpdateEvaluator(evaluatorId ?? 0);
  const cloneEvaluator = useCloneEvaluator();
  const testEvaluator = useTestEvaluator(evaluatorId ?? 0);

  // Check if viewing a built-in evaluator (read-only)
  const isBuiltin = isEditing && evaluator?.is_builtin;

  // Get evaluator types based on category
  const evaluatorTypes = category === 'output' ? OUTPUT_EVALUATOR_TYPES : RUN_METADATA_EVALUATOR_TYPES;

  // Determine Monaco theme
  const getMonacoTheme = () => {
    if (theme === 'system') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'deepagent-dark'
        : 'deepagent-light';
    }
    return theme === 'dark' ? 'deepagent-dark' : 'deepagent-light';
  };

  // Initialize with evaluator data
  useEffect(() => {
    if (isEditing && evaluator) {
      setName(evaluator.name);
      setDescription(evaluator.description || '');
      setCategory(evaluator.category);
      setType(evaluator.type);
      setConfig(JSON.stringify(evaluator.config || {}, null, 2));
      setHasUnsavedChanges(false);
    } else if (!isEditing && evaluatorToClone) {
      setName(`${evaluatorToClone.name}_copy`);
      setDescription(evaluatorToClone.description || '');
      setCategory(evaluatorToClone.category);
      setType(evaluatorToClone.type);
      setConfig(JSON.stringify(evaluatorToClone.config || {}, null, 2));
      setHasUnsavedChanges(true);
    } else if (!isEditing && !cloneId) {
      setName('');
      setDescription('');
      setCategory('output');
      setType('exact_match');
      setConfig(JSON.stringify(DEFAULT_CONFIGS.exact_match, null, 2));
      setHasUnsavedChanges(false);
    }
  }, [isEditing, evaluator, evaluatorToClone, cloneId]);

  // Update default config when type changes
  useEffect(() => {
    if (!isEditing && !cloneId && DEFAULT_CONFIGS[type]) {
      setConfig(JSON.stringify(DEFAULT_CONFIGS[type], null, 2));
    }
  }, [type, isEditing, cloneId]);

  // Track unsaved changes
  useEffect(() => {
    if (!isLoadingEvaluator && (name || description)) {
      setHasUnsavedChanges(true);
    }
  }, [name, description, category, type, config]);

  const handleEditorMount: OnMount = (_editor, monaco) => {
    monaco.editor.defineTheme('deepagent-dark', {
      base: 'vs-dark',
      inherit: true,
      rules: [],
      colors: {
        'editor.background': '#0f0f17',
        'editor.foreground': '#e4e4e7',
      },
    });
    monaco.editor.defineTheme('deepagent-light', {
      base: 'vs',
      inherit: true,
      rules: [],
      colors: {
        'editor.background': '#fafafa',
        'editor.foreground': '#1f2937',
      },
    });
    monaco.editor.setTheme(getMonacoTheme());
  };

  const handleSave = async () => {
    if (!name.trim()) {
      setError('Evaluator name is required');
      return;
    }

    let parsedConfig: Record<string, unknown>;
    try {
      parsedConfig = JSON.parse(config);
    } catch {
      setError('Config must be valid JSON');
      return;
    }

    setError(null);

    try {
      const payload = {
        name: name.trim(),
        type,
        category,
        description: description.trim() || undefined,
        config: parsedConfig,
      };

      if (isEditing && evaluatorId) {
        await updateEvaluator.mutateAsync({
          name: payload.name,
          description: payload.description,
          config: payload.config,
        });
      } else {
        const created = await createEvaluator.mutateAsync(payload);
        navigate(`/evaluations/evaluators/${created.id}`, { replace: true });
      }
      setHasUnsavedChanges(false);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const handleCancel = () => {
    navigate('/evaluations');
  };

  const handleClone = async () => {
    if (evaluator) {
      try {
        const cloned = await cloneEvaluator.mutateAsync({
          id: evaluator.id,
          name: `${evaluator.name}_copy`,
        });
        navigate(`/evaluations/evaluators/${cloned.id}`);
      } catch (err) {
        setError(getErrorMessage(err));
      }
    }
  };

  const handleTest = async () => {
    if (!evaluatorId) {
      setError('Save the evaluator first before testing');
      return;
    }

    setTestResult(null);
    setTestError(null);

    try {
      const result = await testEvaluator.mutateAsync({
        input: testInput,
        expected_output: testExpected,
        actual_output: testActual,
      });
      setTestResult({
        score: result.score,
        passed: result.passed,
        feedback: result.message || undefined,
      });
    } catch (err) {
      setTestError(getErrorMessage(err));
    }
  };

  const isPending = createEvaluator.isPending || updateEvaluator.isPending;
  const isLoading = (isLoadingEvaluator && isEditing) || (isLoadingClone && !!cloneId);

  const breadcrumbItems = [
    { label: 'Evaluations', href: '/evaluations?tab=evaluators', icon: ClipboardList },
    { label: 'Evaluators', href: '/evaluations?tab=evaluators' },
    { label: name || (isEditing ? 'Loading...' : 'New Evaluator'), icon: FlaskConical },
  ];

  if (isLoading) {
    return (
      <div className="container mx-auto py-6 px-4 max-w-7xl flex items-center justify-center min-h-[400px]">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 px-4 max-w-7xl space-y-4">
      {/* Breadcrumb */}
      <Breadcrumb items={breadcrumbItems} />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FlaskConical className="h-6 w-6 text-primary" />
          <div>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              {name || 'New Evaluator'}
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
                ? 'View built-in evaluator (read-only)'
                : isEditing
                  ? 'Edit evaluator configuration'
                  : cloneId
                    ? 'Create new evaluator from clone'
                    : 'Create a new custom evaluator'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleCancel}>
            <X className="mr-2 h-4 w-4" />
            {isBuiltin ? 'Close' : 'Cancel'}
          </Button>
          {isBuiltin ? (
            <Button onClick={handleClone} disabled={cloneEvaluator.isPending}>
              {cloneEvaluator.isPending ? (
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
            This is a built-in evaluator and cannot be modified. Use "Clone to Edit" to create an editable copy.
          </AlertDescription>
        </Alert>
      )}

      {/* Error alerts */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Main content - split view */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left side - Config Editor (2/3 width) */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          {/* Evaluator Settings */}
          <div className="border rounded-lg p-4 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Name</Label>
                <Input
                  placeholder="my_evaluator"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  disabled={isBuiltin}
                />
              </div>
              <div className="space-y-2">
                <Label>Category</Label>
                <Select
                  value={category}
                  onValueChange={(v) => {
                    setCategory(v as EvaluatorCategory);
                    // Reset type when category changes
                    const types = v === 'output' ? OUTPUT_EVALUATOR_TYPES : RUN_METADATA_EVALUATOR_TYPES;
                    setType(types[0].value);
                  }}
                  disabled={isBuiltin || isEditing}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {EVALUATOR_CATEGORIES.map((cat) => (
                      <SelectItem key={cat.value} value={cat.value}>
                        {cat.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Type</Label>
                <Select
                  value={type}
                  onValueChange={(v) => setType(v as EvaluatorType)}
                  disabled={isBuiltin || isEditing}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {evaluatorTypes.map((t) => (
                      <SelectItem key={t.value} value={t.value}>
                        <div>
                          <div className="font-medium">{t.label}</div>
                          <div className="text-xs text-muted-foreground">{t.description}</div>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Input
                  placeholder="What this evaluator checks..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  disabled={isBuiltin}
                />
              </div>
            </div>
          </div>

          {/* Config Editor */}
          <div className="flex flex-col border rounded-lg overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/30">
              <div className="text-sm font-medium">Configuration (JSON)</div>
              <Badge variant="secondary" className="text-xs">
                {type}
              </Badge>
            </div>
            <div className="h-[400px]">
              <Editor
                height="100%"
                defaultLanguage="json"
                value={config}
                onChange={(value) => !isBuiltin && setConfig(value || '{}')}
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
                  readOnly: isBuiltin,
                }}
              />
            </div>
          </div>
        </div>

        {/* Right side - Test Panel (1/3 width) */}
        <div className="flex flex-col border rounded-lg overflow-hidden h-fit">
          <div className="flex items-center gap-2 px-4 py-2 border-b bg-muted/30">
            <Play className="h-4 w-4" />
            <span className="text-sm font-medium">Test Evaluator</span>
          </div>

          <div className="p-4">
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Test Input</Label>
                <Textarea
                  placeholder="Enter test input..."
                  value={testInput}
                  onChange={(e) => setTestInput(e.target.value)}
                  className="resize-none h-20 font-mono text-sm"
                />
              </div>

              <div className="space-y-2">
                <Label>Expected Output</Label>
                <Textarea
                  placeholder="Enter expected output..."
                  value={testExpected}
                  onChange={(e) => setTestExpected(e.target.value)}
                  className="resize-none h-20 font-mono text-sm"
                />
              </div>

              <div className="space-y-2">
                <Label>Actual Output</Label>
                <Textarea
                  placeholder="Enter actual output to evaluate..."
                  value={testActual}
                  onChange={(e) => setTestActual(e.target.value)}
                  className="resize-none h-20 font-mono text-sm"
                />
              </div>

              <Button
                onClick={handleTest}
                disabled={testEvaluator.isPending || !evaluatorId}
                className="w-full"
                variant="secondary"
              >
                {testEvaluator.isPending ? (
                  <Spinner className="mr-2 h-4 w-4" />
                ) : (
                  <Play className="mr-2 h-4 w-4" />
                )}
                Run Test
              </Button>

              {!evaluatorId && (
                <p className="text-xs text-muted-foreground text-center">
                  Save the evaluator first to test it
                </p>
              )}

              {testResult && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      {testResult.passed ? (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-red-600" />
                      )}
                      {testResult.passed ? 'Passed' : 'Failed'}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Score:</span>
                      <span className="font-mono">{(testResult.score * 100).toFixed(1)}%</span>
                    </div>
                    {testResult.feedback && (
                      <div className="text-sm">
                        <span className="text-muted-foreground">Feedback:</span>
                        <p className="mt-1 text-xs bg-muted p-2 rounded">{testResult.feedback}</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {testError && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription className="text-xs">{testError}</AlertDescription>
                </Alert>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
