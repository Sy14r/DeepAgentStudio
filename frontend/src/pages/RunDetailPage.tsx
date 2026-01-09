import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Button,
  Badge,
  Spinner,
  Alert,
  AlertDescription,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Breadcrumb,
} from '@/components/ui';
import {
  ArrowLeft,
  Play,
  Square,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  BarChart3,
  ListChecks,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  ClipboardList,
  PlayCircle,
  Circle,
  Grid3X3,
  Minus,
  FlaskConical,
  ExternalLink,
} from 'lucide-react';
import {
  useEvaluationRun,
  useEvaluationResults,
  useExecuteEvaluationRun,
  useCancelEvaluationRun,
  useEvaluationRunPolling,
  useDatasetExamples,
  getErrorMessage,
} from '@/api/hooks';
import { EvaluationStatus } from '@/api/types';

const STATUS_CONFIG: Record<
  EvaluationStatus,
  { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline'; icon: typeof Clock }
> = {
  pending: { label: 'Pending', variant: 'secondary', icon: Clock },
  running: { label: 'Running', variant: 'default', icon: RefreshCw },
  evaluating: { label: 'Evaluating', variant: 'default', icon: FlaskConical },
  completed: { label: 'Completed', variant: 'outline', icon: CheckCircle },
  failed: { label: 'Failed', variant: 'destructive', icon: XCircle },
  cancelled: { label: 'Cancelled', variant: 'secondary', icon: Square },
  error: { label: 'Error', variant: 'destructive', icon: AlertCircle },
};

export function RunDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const runId = id ? parseInt(id) : null;

  // Results pagination
  const [resultsPage, setResultsPage] = useState(1);
  const [resultsFilter, setResultsFilter] = useState<'all' | 'passed' | 'failed'>('all');

  // Error state
  const [error, setError] = useState<string | null>(null);

  // Data hooks
  const { data: run, isLoading: isLoadingRun, refetch: refetchRun } = useEvaluationRun(runId ?? undefined);
  const { data: resultsData, isLoading: isLoadingResults } = useEvaluationResults({
    runId: runId ?? 0,
    page: resultsPage,
    pageSize: 20,
    passed: resultsFilter === 'all' ? undefined : resultsFilter === 'passed',
  });

  // Fetch all results with scores for the matrix view (only when run exists)
  const { data: matrixResultsData, isLoading: isLoadingMatrixResults } = useEvaluationResults({
    runId: runId ?? 0,
    page: 1,
    pageSize: 200, // Backend max is 200
    includeScores: true,
  });

  // Fetch dataset examples for the matrix view
  const { data: datasetExamplesData, isLoading: isLoadingExamples } = useDatasetExamples({
    datasetId: run?.dataset_id ?? 0,
    page: 1,
    pageSize: 200, // Backend max is 200
  });

  // Use polling for running/evaluating evaluations
  useEvaluationRunPolling(runId ?? 0, run?.status === 'running' || run?.status === 'evaluating');

  const executeRun = useExecuteEvaluationRun();
  const cancelRun = useCancelEvaluationRun();

  const handleExecute = async () => {
    if (!runId) return;
    setError(null);
    try {
      await executeRun.mutateAsync(runId);
      refetchRun();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const handleCancel = async () => {
    if (!runId) return;
    setError(null);
    try {
      await cancelRun.mutateAsync(runId);
      refetchRun();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const handleBack = () => {
    navigate('/evaluations');
  };

  const results = resultsData?.results || [];
  const totalResults = resultsData?.total || 0;
  const totalPages = Math.ceil(totalResults / 20);

  if (isLoadingRun) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  if (!run) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
        <h2 className="text-lg font-semibold">Run not found</h2>
        <Button variant="outline" onClick={handleBack} className="mt-4">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Evaluations
        </Button>
      </div>
    );
  }

  const statusConfig = STATUS_CONFIG[run.status] || STATUS_CONFIG.pending;
  const StatusIcon = statusConfig.icon;
  const progress = run.total_examples > 0 ? (run.completed_examples / run.total_examples) * 100 : 0;
  const passRate = typeof run.metrics?.pass_rate === 'number' ? run.metrics.pass_rate : 0;
  const avgScore = typeof run.metrics?.avg_score === 'number' ? run.metrics.avg_score : 0;

  const breadcrumbItems = [
    { label: 'Evaluations', href: '/evaluations?tab=runs', icon: ClipboardList },
    { label: 'Runs', href: '/evaluations?tab=runs' },
    { label: run.name || `Run #${run.id}`, icon: PlayCircle },
  ];

  return (
    <div className="container mx-auto py-6 px-4 max-w-7xl space-y-6">
      {/* Breadcrumb */}
      <Breadcrumb items={breadcrumbItems} />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              {run.name}
              <Badge variant={statusConfig.variant} className="gap-1">
                <StatusIcon className={`h-3 w-3 ${run.status === 'running' ? 'animate-spin' : ''}`} />
                {statusConfig.label}
              </Badge>
            </h1>
            <p className="text-sm text-muted-foreground">
              {run.dataset_name} • {run.agent_name || 'No agent'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {(run.status === 'pending' || run.status === 'failed') && (
            <Button onClick={handleExecute} disabled={executeRun.isPending}>
              {executeRun.isPending ? (
                <Spinner className="mr-2 h-4 w-4" />
              ) : (
                <Play className="mr-2 h-4 w-4" />
              )}
              {run.status === 'failed' ? 'Retry' : 'Start'}
            </Button>
          )}
          {run.status === 'running' && (
            <Button variant="destructive" onClick={handleCancel} disabled={cancelRun.isPending}>
              {cancelRun.isPending ? (
                <Spinner className="mr-2 h-4 w-4" />
              ) : (
                <Square className="mr-2 h-4 w-4" />
              )}
              Cancel
            </Button>
          )}
        </div>
      </div>

      {/* Error alerts */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Progress bar for running/evaluating evaluations */}
      {(run.status === 'running' || run.status === 'evaluating') && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span>Progress</span>
            <span className="text-muted-foreground">
              {run.completed_examples} / {run.total_examples} examples
            </span>
          </div>
          <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Main content */}
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview" className="gap-2">
            <BarChart3 className="h-4 w-4" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="matrix" className="gap-2">
            <Grid3X3 className="h-4 w-4" />
            Test Matrix
          </TabsTrigger>
          <TabsTrigger value="results" className="gap-2">
            <ListChecks className="h-4 w-4" />
            Results ({totalResults})
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="mt-6 space-y-6">
          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Progress Card */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Progress
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{progress.toFixed(0)}%</div>
                <p className="text-xs text-muted-foreground">
                  {run.completed_examples} of {run.total_examples} examples
                </p>
              </CardContent>
            </Card>

            {/* Pass Rate Card */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Pass Rate
                </CardTitle>
              </CardHeader>
              <CardContent>
                {run.status === 'running' || run.status === 'pending' ? (
                  <>
                    <div className="text-2xl font-bold flex items-center gap-2 text-muted-foreground">
                      <RefreshCw className="h-5 w-5 animate-spin" />
                      {run.status === 'pending' ? 'Pending' : 'Running...'}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Waiting for results
                    </p>
                  </>
                ) : (
                  <>
                    <div className="text-2xl font-bold flex items-center gap-2">
                      {(passRate * 100).toFixed(1)}%
                      {passRate >= 0.8 ? (
                        <CheckCircle className="h-5 w-5 text-green-600" />
                      ) : passRate >= 0.5 ? (
                        <AlertCircle className="h-5 w-5 text-yellow-600" />
                      ) : (
                        <XCircle className="h-5 w-5 text-red-600" />
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {run.passed_examples || 0} passed
                    </p>
                  </>
                )}
              </CardContent>
            </Card>

            {/* Average Score Card */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Average Score
                </CardTitle>
              </CardHeader>
              <CardContent>
                {run.status === 'running' || run.status === 'pending' ? (
                  <>
                    <div className="text-2xl font-bold flex items-center gap-2 text-muted-foreground">
                      <RefreshCw className="h-5 w-5 animate-spin" />
                      {run.status === 'pending' ? 'Pending' : 'Running...'}
                    </div>
                    <p className="text-xs text-muted-foreground">Waiting for results</p>
                  </>
                ) : (
                  <>
                    <div className="text-2xl font-bold">{(avgScore * 100).toFixed(1)}%</div>
                    <p className="text-xs text-muted-foreground">Across all evaluators</p>
                  </>
                )}
              </CardContent>
            </Card>

            {/* Duration Card */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Duration
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {run.started_at && run.completed_at
                    ? `${Math.round(
                        (new Date(run.completed_at).getTime() -
                          new Date(run.started_at).getTime()) /
                          1000
                      )}s`
                    : run.started_at
                      ? 'Running...'
                      : '-'}
                </div>
                <p className="text-xs text-muted-foreground">
                  {run.started_at
                    ? `Started ${new Date(run.started_at).toLocaleString()}`
                    : 'Not started'}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Metrics breakdown */}
          {run.metrics && Object.keys(run.metrics).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Metrics Breakdown</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {Object.entries(run.metrics)
                    .filter(([key]) => !['evaluator_scores', 'tag_breakdown', 'run_metadata_aggregates', 'score_distribution'].includes(key))
                    .map(([key, value]) => (
                    <div key={key} className="space-y-1">
                      <div className="text-sm text-muted-foreground capitalize">
                        {key.replace(/_/g, ' ')}
                      </div>
                      <div className="text-lg font-semibold">
                        {typeof value === 'number'
                          ? value < 1 && key.includes('rate')
                            ? `${(value * 100).toFixed(1)}%`
                            : value.toFixed(2)
                          : typeof value === 'object'
                            ? JSON.stringify(value)
                            : String(value)}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Run configuration */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Configuration</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">Dataset:</span>
                  <div className="font-medium">{run.dataset_name}</div>
                  <div className="text-xs text-muted-foreground">{run.total_examples} examples</div>
                </div>
                <div>
                  <span className="text-muted-foreground">Agent:</span>
                  <div className="font-medium">{run.agent_name || 'None'}</div>
                </div>
                <div>
                  <span className="text-muted-foreground">Evaluators:</span>
                  <div className="font-medium">{run.evaluators?.length || 0}</div>
                  {run.evaluators && run.evaluators.length > 0 && (
                    <div className="text-xs text-muted-foreground truncate" title={run.evaluators.map(e => e.name).join(', ')}>
                      {run.evaluators.map(e => e.name).join(', ')}
                    </div>
                  )}
                </div>
                <div>
                  <span className="text-muted-foreground">Created:</span>
                  <div className="font-medium">
                    {new Date(run.created_at).toLocaleDateString()}
                  </div>
                </div>
                <div>
                  <span className="text-muted-foreground">Total Tests:</span>
                  <div className="font-medium">{run.total_examples * (run.evaluators?.length || 0)}</div>
                  <div className="text-xs text-muted-foreground">{run.total_examples} examples × {run.evaluators?.length || 0} evaluators</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Test Matrix Tab */}
        <TabsContent value="matrix" className="mt-6 space-y-4">
          {isLoadingExamples || isLoadingMatrixResults ? (
            <div className="flex items-center justify-center py-12">
              <Spinner className="h-8 w-8" />
            </div>
          ) : (
            <>
              {/* Matrix explanation */}
              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  Each row represents a test example, and each column represents an evaluator.
                  {run.status === 'pending' && ' Start the evaluation to see results.'}
                </p>
              </div>

              {/* Matrix table */}
              <Card>
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <table className="w-full border-collapse">
                      <thead>
                        <tr className="border-b bg-muted/50">
                          <th className="text-left p-3 font-medium text-sm sticky left-0 bg-muted/50 min-w-[200px]">
                            Example
                          </th>
                          <th className="text-left p-3 font-medium text-sm min-w-[120px]">
                            Input Preview
                          </th>
                          <th className="text-left p-3 font-medium text-sm min-w-[120px]">
                            Expected
                          </th>
                          <th className="text-left p-3 font-medium text-sm min-w-[150px]">
                            Actual Output
                          </th>
                          {run.evaluators?.map((evaluator) => (
                            <th
                              key={evaluator.id}
                              className="text-center p-3 font-medium text-sm min-w-[100px]"
                              title={evaluator.description || evaluator.name}
                            >
                              <div className="truncate max-w-[100px]">{evaluator.name}</div>
                              <div className="text-xs text-muted-foreground font-normal">
                                {evaluator.type.replace(/_/g, ' ')}
                              </div>
                            </th>
                          ))}
                          <th className="text-center p-3 font-medium text-sm min-w-[80px]">
                            Overall
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {(datasetExamplesData?.examples || []).map((example) => {
                          // Find the result for this example
                          const result = matrixResultsData?.results?.find(
                            (r) => r.example_id === example.id
                          );
                          const scores = result?.scores || [];

                          return (
                            <tr key={example.id} className="border-b hover:bg-muted/30">
                              <td className="p-3 text-sm sticky left-0 bg-background">
                                <div className="font-medium">
                                  {example.name || `Example #${example.id}`}
                                </div>
                              </td>
                              <td className="p-3 text-sm">
                                <div className="truncate max-w-[150px] text-muted-foreground" title={
                                  typeof example.input === 'string'
                                    ? example.input
                                    : JSON.stringify(example.input)
                                }>
                                  {typeof example.input === 'string'
                                    ? example.input.slice(0, 50)
                                    : JSON.stringify(example.input).slice(0, 50)}
                                  {(typeof example.input === 'string' ? example.input : JSON.stringify(example.input)).length > 50 && '...'}
                                </div>
                              </td>
                              <td className="p-3 text-sm">
                                <div className="truncate max-w-[150px] text-muted-foreground" title={
                                  typeof example.expected_output === 'string'
                                    ? example.expected_output
                                    : JSON.stringify(example.expected_output)
                                }>
                                  {typeof example.expected_output === 'string'
                                    ? example.expected_output.slice(0, 50)
                                    : JSON.stringify(example.expected_output).slice(0, 50)}
                                  {(typeof example.expected_output === 'string' ? example.expected_output : JSON.stringify(example.expected_output)).length > 50 && '...'}
                                </div>
                              </td>
                              <td className="p-3 text-sm">
                                {result ? (
                                  result.status === 'pending' || result.status === 'running' ? (
                                    <div className="flex items-center gap-1 text-muted-foreground">
                                      <RefreshCw className="h-3 w-3 animate-spin" />
                                      <span className="text-xs">Running...</span>
                                    </div>
                                  ) : (
                                    <div className="flex flex-col gap-1">
                                      <div
                                        className="truncate max-w-[150px] text-muted-foreground"
                                        title={
                                          typeof result.agent_output === 'string'
                                            ? result.agent_output
                                            : JSON.stringify(result.agent_output)
                                        }
                                      >
                                        {result.agent_output != null ? (
                                          typeof result.agent_output === 'string'
                                            ? result.agent_output.slice(0, 40)
                                            : JSON.stringify(result.agent_output).slice(0, 40)
                                        ) : (
                                          <span className="text-muted-foreground/50 italic">No output</span>
                                        )}
                                        {result.agent_output != null &&
                                          (typeof result.agent_output === 'string' ? result.agent_output : JSON.stringify(result.agent_output)).length > 40 && '...'}
                                      </div>
                                      {(result.run_metadata as Record<string, unknown>)?.session_id && (
                                        <a
                                          href={`/sessions/${(result.run_metadata as Record<string, unknown>).session_id}`}
                                          className="text-xs text-blue-500 hover:text-blue-700 flex items-center gap-1"
                                          title="View agent execution session"
                                          onClick={(e) => {
                                            e.preventDefault();
                                            navigate(`/sessions/${(result.run_metadata as Record<string, unknown>).session_id}`);
                                          }}
                                        >
                                          <ExternalLink className="h-3 w-3" />
                                          View Session
                                        </a>
                                      )}
                                    </div>
                                  )
                                ) : (
                                  <div className="flex items-center">
                                    <Minus className="h-4 w-4 text-muted-foreground" />
                                  </div>
                                )}
                              </td>
                              {run.evaluators?.map((evaluator) => {
                                const score = scores.find((s) => s.evaluator_id === evaluator.id);

                                if (!result) {
                                  // No result yet (run not started or example not processed)
                                  return (
                                    <td key={evaluator.id} className="p-3 text-center">
                                      <div className="flex items-center justify-center">
                                        <Minus className="h-4 w-4 text-muted-foreground" />
                                      </div>
                                    </td>
                                  );
                                }

                                if (result.status === 'pending' || result.status === 'running') {
                                  return (
                                    <td key={evaluator.id} className="p-3 text-center">
                                      <div className="flex items-center justify-center">
                                        <RefreshCw className="h-4 w-4 text-blue-500 animate-spin" />
                                      </div>
                                    </td>
                                  );
                                }

                                if (!score) {
                                  return (
                                    <td key={evaluator.id} className="p-3 text-center">
                                      <div className="flex items-center justify-center">
                                        <Circle className="h-4 w-4 text-muted-foreground" />
                                      </div>
                                    </td>
                                  );
                                }

                                return (
                                  <td key={evaluator.id} className="p-3 text-center">
                                    <div className="flex flex-col items-center gap-1">
                                      {score.passed === true ? (
                                        <CheckCircle className="h-4 w-4 text-green-600" />
                                      ) : score.passed === false ? (
                                        <XCircle className="h-4 w-4 text-red-600" />
                                      ) : (
                                        <Circle className="h-4 w-4 text-muted-foreground" />
                                      )}
                                      {score.score != null && (
                                        <span className="text-xs text-muted-foreground">
                                          {(score.score * 100).toFixed(0)}%
                                        </span>
                                      )}
                                      {score.session_id && (
                                        <a
                                          href={`/sessions/${score.session_id}`}
                                          className="text-xs text-blue-500 hover:text-blue-700 flex items-center gap-1"
                                          title="View evaluator session"
                                          onClick={(e) => {
                                            e.preventDefault();
                                            navigate(`/sessions/${score.session_id}`);
                                          }}
                                        >
                                          <ExternalLink className="h-3 w-3" />
                                          Session
                                        </a>
                                      )}
                                    </div>
                                  </td>
                                );
                              })}
                              <td className="p-3 text-center">
                                {!result ? (
                                  <div className="flex items-center justify-center">
                                    <Minus className="h-4 w-4 text-muted-foreground" />
                                  </div>
                                ) : result.status === 'pending' || result.status === 'running' ? (
                                  <div className="flex items-center justify-center">
                                    <RefreshCw className="h-4 w-4 text-blue-500 animate-spin" />
                                  </div>
                                ) : (
                                  <div className="flex flex-col items-center gap-1">
                                    {result.passed === true ? (
                                      <CheckCircle className="h-5 w-5 text-green-600" />
                                    ) : result.passed === false ? (
                                      <XCircle className="h-5 w-5 text-red-600" />
                                    ) : (
                                      <Circle className="h-5 w-5 text-muted-foreground" />
                                    )}
                                    {result.aggregate_score != null && (
                                      <span className="text-xs font-medium">
                                        {(result.aggregate_score * 100).toFixed(0)}%
                                      </span>
                                    )}
                                  </div>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>

              {/* Legend */}
              <div className="flex items-center gap-6 text-sm text-muted-foreground flex-wrap">
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  <span>Passed</span>
                </div>
                <div className="flex items-center gap-2">
                  <XCircle className="h-4 w-4 text-red-600" />
                  <span>Failed</span>
                </div>
                <div className="flex items-center gap-2">
                  <RefreshCw className="h-4 w-4 text-blue-500" />
                  <span>Running</span>
                </div>
                <div className="flex items-center gap-2">
                  <Minus className="h-4 w-4 text-muted-foreground" />
                  <span>Not Started</span>
                </div>
                <div className="flex items-center gap-2">
                  <Circle className="h-4 w-4 text-muted-foreground" />
                  <span>No Score</span>
                </div>
                <div className="flex items-center gap-2">
                  <ExternalLink className="h-4 w-4 text-blue-500" />
                  <span>View Session (Agent or Evaluator)</span>
                </div>
              </div>
            </>
          )}
        </TabsContent>

        {/* Results Tab */}
        <TabsContent value="results" className="mt-6 space-y-4">
          {/* Results toolbar */}
          <div className="flex items-center justify-between gap-4">
            <Select
              value={resultsFilter}
              onValueChange={(v) => {
                setResultsFilter(v as 'all' | 'passed' | 'failed');
                setResultsPage(1);
              }}
            >
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Results</SelectItem>
                <SelectItem value="passed">Passed Only</SelectItem>
                <SelectItem value="failed">Failed Only</SelectItem>
              </SelectContent>
            </Select>

            {totalResults > 0 && (
              <span className="text-sm text-muted-foreground">
                Showing {results.length} of {totalResults} results
              </span>
            )}
          </div>

          {/* Results list */}
          {isLoadingResults ? (
            <div className="flex items-center justify-center py-12">
              <Spinner className="h-8 w-8" />
            </div>
          ) : results.length === 0 ? (
            <Card className="py-12">
              <div className="flex flex-col items-center justify-center text-center">
                <ListChecks className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold">No results yet</h3>
                <p className="text-muted-foreground">
                  {run.status === 'pending'
                    ? 'Start the evaluation to see results'
                    : 'No results match the current filter'}
                </p>
              </div>
            </Card>
          ) : (
            <div className="space-y-4">
              {results.map((result) => {
                const isPassed = result.passed;
                const isResultPending = result.status === 'pending' || result.status === 'running';
                // Render appropriate icon based on passed state and result status
                const PassIcon = isResultPending
                  ? () => <RefreshCw className="h-5 w-5 text-blue-500 shrink-0 animate-spin" />
                  : isPassed === true
                    ? () => <CheckCircle className="h-5 w-5 text-green-600 shrink-0" />
                    : isPassed === false
                      ? () => <XCircle className="h-5 w-5 text-red-600 shrink-0" />
                      : () => <Circle className="h-5 w-5 text-muted-foreground shrink-0" />;
                return (
                  <Card key={result.id}>
                    <CardContent className="p-6">
                      <div className="flex items-center gap-3 mb-4">
                        <PassIcon />
                        <span className="font-semibold text-lg">
                          {result.example_name || `Example #${result.example_id}`}
                        </span>
                        {isResultPending && (
                          <Badge variant="outline" className="text-blue-500 border-blue-500">
                            {result.status === 'pending' ? 'Pending' : 'Running'}
                          </Badge>
                        )}
                        {!isResultPending && result.latency_ms && (
                          <Badge variant="outline">
                            {result.latency_ms}ms
                          </Badge>
                        )}
                        <Badge variant={isPassed === true ? 'default' : 'secondary'}>
                          Score: {isResultPending ? 'Pending' : result.aggregate_score != null ? `${(result.aggregate_score * 100).toFixed(0)}%` : 'N/A'}
                        </Badge>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div>
                          <div className="text-sm font-medium text-muted-foreground mb-2">Input</div>
                          <pre className="bg-muted p-3 rounded-md text-sm overflow-x-auto whitespace-pre-wrap break-words min-h-[60px]">
                            {result.example_input != null
                              ? typeof result.example_input === 'string'
                                ? result.example_input
                                : JSON.stringify(result.example_input, null, 2)
                              : '-'}
                          </pre>
                        </div>
                        <div>
                          <div className="text-sm font-medium text-muted-foreground mb-2">Expected Output</div>
                          <pre className="bg-muted p-3 rounded-md text-sm overflow-x-auto whitespace-pre-wrap break-words min-h-[60px]">
                            {result.example_expected_output != null
                              ? typeof result.example_expected_output === 'string'
                                ? result.example_expected_output
                                : JSON.stringify(result.example_expected_output, null, 2)
                              : '-'}
                          </pre>
                        </div>
                        <div>
                          <div className="text-sm font-medium text-muted-foreground mb-2">Actual Output</div>
                          <pre className="bg-muted p-3 rounded-md text-sm overflow-x-auto whitespace-pre-wrap break-words min-h-[60px]">
                            {result.agent_output != null
                              ? typeof result.agent_output === 'string'
                                ? result.agent_output
                                : JSON.stringify(result.agent_output, null, 2)
                              : '-'}
                          </pre>
                        </div>
                      </div>

                      {result.error_message && (
                        <Alert variant="destructive" className="mt-4">
                          <AlertCircle className="h-4 w-4" />
                          <AlertDescription>
                            {result.error_message}
                          </AlertDescription>
                        </Alert>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-4">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setResultsPage((p) => Math.max(1, p - 1))}
                disabled={resultsPage === 1}
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                Previous
              </Button>
              <span className="text-sm text-muted-foreground px-4">
                Page {resultsPage} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setResultsPage((p) => Math.min(totalPages, p + 1))}
                disabled={resultsPage === totalPages}
              >
                Next
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
