import { useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Play,
  Plus,
  MoreVertical,
  Pencil,
  Trash2,
  Eye,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  Database,
  FlaskConical,
  Settings,
  ClipboardList,
  TrendingUp,
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Spinner } from '@/components/ui/spinner';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { DeleteConfirmDialog, Breadcrumb } from '@/components/ui';
import {
  useEvaluation,
  useEvaluationRuns,
  useCreateEvaluationRun,
  useExecuteEvaluationRun,
  useCancelEvaluationRun,
  useDeleteEvaluationRun,
  useAgents,
  getErrorMessage,
} from '@/api/hooks';
import type { EvaluationRun, EvaluationStatus } from '@/api/types';

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function getStatusIcon(status: EvaluationStatus) {
  switch (status) {
    case 'completed':
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case 'failed':
    case 'error':
      return <XCircle className="h-4 w-4 text-red-500" />;
    case 'running':
    case 'evaluating':
      return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
    case 'pending':
      return <Clock className="h-4 w-4 text-yellow-500" />;
    case 'cancelled':
      return <XCircle className="h-4 w-4 text-gray-500" />;
    default:
      return <Clock className="h-4 w-4 text-gray-500" />;
  }
}

function getStatusBadgeVariant(status: EvaluationStatus): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status) {
    case 'completed':
      return 'default';
    case 'failed':
    case 'error':
      return 'destructive';
    case 'running':
    case 'evaluating':
    case 'pending':
      return 'secondary';
    default:
      return 'outline';
  }
}

interface ChartDataPoint {
  name: string;
  passRate: number;
  avgScore: number;
  date: string;
  runId: number;
  agentName: string;
}

function PerformanceChart({ runs }: { runs: EvaluationRun[] }) {
  const chartData = useMemo(() => {
    // Filter to completed runs and sort by date
    const completedRuns = runs
      .filter((r) => r.status === 'completed' && r.completed_at)
      .sort((a, b) => new Date(a.completed_at!).getTime() - new Date(b.completed_at!).getTime());

    return completedRuns.map((run, index): ChartDataPoint => {
      const passRate = run.total_examples > 0
        ? (run.passed_examples / run.total_examples) * 100
        : 0;

      const avgScore = run.metrics && typeof run.metrics === 'object' && 'avg_score' in run.metrics
        ? (run.metrics.avg_score as number) * 100
        : passRate;

      return {
        name: run.name || `Run #${index + 1}`,
        passRate: Math.round(passRate * 10) / 10,
        avgScore: Math.round(avgScore * 10) / 10,
        date: new Date(run.completed_at!).toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
        }),
        runId: run.id,
        agentName: run.agent_name || 'Unknown',
      };
    });
  }, [runs]);

  if (chartData.length === 0) {
    return null;
  }

  // Calculate trend
  const trend = chartData.length >= 2
    ? chartData[chartData.length - 1].passRate - chartData[0].passRate
    : 0;

  // Calculate average
  const avgPassRate = chartData.reduce((sum, d) => sum + d.passRate, 0) / chartData.length;

  return (
    <Card className="mb-8">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Performance Over Time
          </CardTitle>
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-1">
              <span className="text-muted-foreground">Avg:</span>
              <span className="font-medium">{avgPassRate.toFixed(1)}%</span>
            </div>
            {chartData.length >= 2 && (
              <div className="flex items-center gap-1">
                <span className="text-muted-foreground">Trend:</span>
                <span className={`font-medium ${trend >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {trend >= 0 ? '+' : ''}{trend.toFixed(1)}%
                </span>
              </div>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 12 }}
                tickLine={false}
                axisLine={false}
                className="text-muted-foreground"
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fontSize: 12 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(value) => `${value}%`}
                className="text-muted-foreground"
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload || !payload.length) return null;
                  const data = payload[0].payload as ChartDataPoint;
                  return (
                    <div className="bg-popover border rounded-lg shadow-lg p-3 text-sm">
                      <p className="font-medium">{data.name}</p>
                      <p className="text-muted-foreground text-xs mb-2">{data.agentName}</p>
                      <div className="space-y-1">
                        <p>
                          <span className="text-muted-foreground">Pass Rate: </span>
                          <span className="font-medium">{data.passRate}%</span>
                        </p>
                        <p>
                          <span className="text-muted-foreground">Avg Score: </span>
                          <span className="font-medium">{data.avgScore}%</span>
                        </p>
                        <p className="text-xs text-muted-foreground">{data.date}</p>
                      </div>
                    </div>
                  );
                }}
              />
              <ReferenceLine
                y={avgPassRate}
                stroke="hsl(var(--muted-foreground))"
                strokeDasharray="5 5"
                strokeOpacity={0.5}
              />
              <Line
                type="monotone"
                dataKey="passRate"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                dot={{ fill: 'hsl(var(--primary))', strokeWidth: 2, r: 4 }}
                activeDot={{ r: 6, strokeWidth: 0 }}
                name="Pass Rate"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        {chartData.length === 1 && (
          <p className="text-xs text-muted-foreground text-center mt-2">
            Run more evaluations to see performance trends
          </p>
        )}
      </CardContent>
    </Card>
  );
}

export default function EvaluationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const evaluationId = id ? parseInt(id) : undefined;

  // State
  const [showCreateRunDialog, setShowCreateRunDialog] = useState(false);
  const [newRunAgentId, setNewRunAgentId] = useState<number | null>(null);
  const [newRunName, setNewRunName] = useState('');
  const [runToDelete, setRunToDelete] = useState<EvaluationRun | null>(null);

  // Queries
  const {
    data: evaluation,
    isLoading: evaluationLoading,
    error: evaluationError,
  } = useEvaluation(evaluationId);

  const {
    data: runsData,
    isLoading: runsLoading,
  } = useEvaluationRuns({
    evaluationId: evaluationId || 0,
    page: 1,
    pageSize: 100,
    // Enable polling when any run is active (the hook handles this internally)
    pollingEnabled: true,
  });

  const { data: agentsData } = useAgents({ page: 1, pageSize: 100 });

  // Mutations
  const createRun = useCreateEvaluationRun(evaluationId || 0);
  const executeRun = useExecuteEvaluationRun(evaluationId || 0);
  const cancelRun = useCancelEvaluationRun(evaluationId || 0);
  const deleteRun = useDeleteEvaluationRun(evaluationId || 0);

  const handleOpenCreateRunDialog = () => {
    setNewRunAgentId(null);
    setNewRunName('');
    setShowCreateRunDialog(true);
  };

  const handleCloseCreateRunDialog = () => {
    setShowCreateRunDialog(false);
  };

  const handleCreateRun = async () => {
    if (!newRunAgentId) return;

    try {
      const run = await createRun.mutateAsync({
        agent_id: newRunAgentId,
        name: newRunName.trim() || undefined,
      });
      handleCloseCreateRunDialog();
      navigate(`/evaluations/${evaluationId}/runs/${run.id}`);
    } catch {
      // Error handled by mutation
    }
  };

  if (evaluationLoading) {
    return (
      <div className="container mx-auto py-6 px-4 max-w-7xl">
        <div className="flex justify-center py-12">
          <Spinner size="lg" />
        </div>
      </div>
    );
  }

  if (evaluationError || !evaluation) {
    return (
      <div className="container mx-auto py-6 px-4 max-w-7xl">
        <Alert variant="destructive">
          <AlertDescription>
            {evaluationError ? getErrorMessage(evaluationError) : 'Evaluation not found'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 px-4 max-w-7xl">
      {/* Breadcrumb */}
      <Breadcrumb
        className="mb-4"
        items={[
          { label: 'Evaluations', href: '/evaluations?tab=evaluations', icon: ClipboardList },
          { label: evaluation.name },
        ]}
      />

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/evaluations?tab=evaluations')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold">{evaluation.name}</h1>
            {evaluation.description && (
              <p className="text-muted-foreground mt-1">{evaluation.description}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => navigate(`/evaluations/${evaluationId}/edit`)}>
            <Pencil className="h-4 w-4 mr-2" />
            Edit
          </Button>
          <Button onClick={handleOpenCreateRunDialog}>
            <Plus className="h-4 w-4 mr-2" />
            New Run
          </Button>
        </div>
      </div>

      {/* Evaluation Config Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Database className="h-4 w-4" />
              Dataset
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold">{evaluation.dataset?.name || 'Unknown'}</p>
            {evaluation.dataset && (
              <p className="text-sm text-muted-foreground">
                {evaluation.dataset.example_count} examples
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <FlaskConical className="h-4 w-4" />
              Evaluators
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold">{evaluation.evaluator_count} evaluators</p>
            <div className="flex flex-wrap gap-1 mt-1">
              {evaluation.evaluators?.slice(0, 3).map((e) => (
                <Badge key={e.id} variant="outline" className="text-xs">
                  {e.name}
                </Badge>
              ))}
              {evaluation.evaluators && evaluation.evaluators.length > 3 && (
                <Badge variant="outline" className="text-xs">
                  +{evaluation.evaluators.length - 3} more
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Settings className="h-4 w-4" />
              Config
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1 text-sm">
              <p>Concurrency: {evaluation.config?.concurrency || 3}</p>
              <p>Timeout: {((evaluation.config?.timeout_per_example_ms || 60000) / 1000)}s per example</p>
              {evaluation.config?.sample_size && (
                <p>Sample: {evaluation.config.sample_size} examples</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Performance Chart - only show if there are completed runs */}
      {runsData && runsData.runs.filter(r => r.status === 'completed').length > 0 && (
        <PerformanceChart runs={runsData.runs} />
      )}

      {/* Runs Section */}
      <div className="mb-4">
        <h2 className="text-xl font-semibold mb-4">Runs ({runsData?.total || 0})</h2>
      </div>

      {runsLoading ? (
        <div className="flex justify-center py-12">
          <Spinner size="lg" />
        </div>
      ) : runsData?.runs.length === 0 ? (
        <Card className="py-12">
          <div className="text-center">
            <Play className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No runs yet</h3>
            <p className="text-muted-foreground mb-4">
              Create your first run to test an agent against this evaluation.
            </p>
            <Button onClick={handleOpenCreateRunDialog}>
              <Plus className="h-4 w-4 mr-2" />
              Create Run
            </Button>
          </div>
        </Card>
      ) : (
        <div className="space-y-2">
          {runsData?.runs.map((run) => {
            const passRate = run.total_examples > 0 && run.passed_examples != null
              ? ((run.passed_examples / run.total_examples) * 100).toFixed(1)
              : '0.0';

            return (
              <div
                key={run.id}
                className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors cursor-pointer"
                onClick={() => navigate(`/evaluations/${evaluationId}/runs/${run.id}`)}
              >
                <div className="flex items-center gap-4 flex-1 min-w-0">
                  {getStatusIcon(run.status)}
                  <div className="min-w-0 flex-1">
                    <h3 className="font-medium truncate">
                      {run.name || `Run #${run.id}`}
                    </h3>
                    <p className="text-sm text-muted-foreground truncate">
                      Agent: {run.agent_name || 'Unknown'}
                    </p>
                  </div>
                  <div className="flex items-center gap-4 text-sm">
                    <Badge variant={getStatusBadgeVariant(run.status)}>{run.status}</Badge>
                    <span className="text-muted-foreground">
                      {run.completed_examples}/{run.total_examples}
                    </span>
                    {run.status === 'completed' && (
                      <span className={`font-medium ${
                        parseFloat(passRate) >= 80 ? 'text-green-600' :
                        parseFloat(passRate) >= 50 ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {passRate}%
                      </span>
                    )}
                    <span className="text-muted-foreground text-xs">
                      {run.completed_at ? formatDate(run.completed_at) : formatDate(run.created_at)}
                    </span>
                  </div>
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                    <Button variant="ghost" size="icon" className="h-8 w-8 ml-2">
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/evaluations/${evaluationId}/runs/${run.id}`);
                    }}>
                      <Eye className="h-4 w-4 mr-2" />
                      View Results
                    </DropdownMenuItem>
                    {run.status === 'pending' && (
                      <DropdownMenuItem
                        onClick={(e) => {
                          e.stopPropagation();
                          executeRun.mutate(run.id);
                        }}
                        disabled={executeRun.isPending}
                      >
                        <Play className="h-4 w-4 mr-2" />
                        {executeRun.isPending ? 'Starting...' : 'Execute'}
                      </DropdownMenuItem>
                    )}
                    {(run.status === 'running' || run.status === 'evaluating') && (
                      <DropdownMenuItem
                        onClick={(e) => {
                          e.stopPropagation();
                          cancelRun.mutate(run.id);
                        }}
                        disabled={cancelRun.isPending}
                      >
                        <XCircle className="h-4 w-4 mr-2" />
                        {cancelRun.isPending ? 'Cancelling...' : 'Cancel'}
                      </DropdownMenuItem>
                    )}
                    {run.status !== 'running' && run.status !== 'evaluating' && (
                      <DropdownMenuItem
                        onClick={(e) => {
                          e.stopPropagation();
                          setRunToDelete(run);
                        }}
                        className="text-destructive"
                      >
                        <Trash2 className="h-4 w-4 mr-2" />
                        Delete
                      </DropdownMenuItem>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            );
          })}
        </div>
      )}

      {/* Delete Run Dialog */}
      <DeleteConfirmDialog
        open={!!runToDelete}
        onOpenChange={(open: boolean) => !open && setRunToDelete(null)}
        itemName={runToDelete?.name || `Run #${runToDelete?.id}`}
        itemType="evaluation run"
        onConfirm={async () => {
          if (runToDelete) {
            await deleteRun.mutateAsync(runToDelete.id);
            setRunToDelete(null);
          }
        }}
        isLoading={deleteRun.isPending}
      />

      {/* Create Run Dialog */}
      <Dialog open={showCreateRunDialog} onOpenChange={(open) => !open && handleCloseCreateRunDialog()}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Run</DialogTitle>
            <DialogDescription>
              Select an agent to run against this evaluation's dataset.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Run Name (Optional) */}
            <div className="space-y-2">
              <Label htmlFor="run-name">Run Name (Optional)</Label>
              <Input
                id="run-name"
                placeholder="e.g., v2.0 test"
                value={newRunName}
                onChange={(e) => setNewRunName(e.target.value)}
              />
            </div>

            {/* Agent Selection */}
            <div className="space-y-2">
              <Label>Agent *</Label>
              <Select
                value={newRunAgentId?.toString() || ''}
                onValueChange={(v) => setNewRunAgentId(parseInt(v))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select an agent" />
                </SelectTrigger>
                <SelectContent>
                  {agentsData?.agents.map((agent) => (
                    <SelectItem key={agent.id} value={agent.id.toString()}>
                      {agent.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {agentsData?.agents.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  No agents available.{' '}
                  <Button variant="link" className="p-0 h-auto" onClick={() => navigate('/agents/new')}>
                    Create one first.
                  </Button>
                </p>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={handleCloseCreateRunDialog}>
              Cancel
            </Button>
            <Button
              onClick={handleCreateRun}
              disabled={!newRunAgentId || createRun.isPending}
            >
              {createRun.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create & View'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
