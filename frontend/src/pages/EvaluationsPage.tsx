import { useState, useEffect } from 'react';
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import {
  Plus,
  Database,
  FlaskConical,
  Play,
  MoreVertical,
  Pencil,
  Trash2,
  Copy,
  Eye,
  FileText,
  Lock,
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  LayoutGrid,
  List,
  Search,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { DeleteConfirmDialog } from '@/components/ui';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import {
  useDatasets,
  useDeleteDataset,
  useEvaluators,
  useDeleteEvaluator,
  useCloneEvaluator,
  useEvaluationRuns,
  useCreateEvaluationRun,
  useDeleteEvaluationRun,
  useExecuteEvaluationRun,
  useCancelEvaluationRun,
  useAgents,
  getErrorMessage,
} from '@/api/hooks';
import type {
  EvaluationDataset,
  Evaluator,
  EvaluationRun,
  EvaluationStatus,
  EvaluatorCategory,
} from '@/api/types';

const EVALUATIONS_VIEW_MODE_KEY = 'evaluations-view-mode';

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
    case 'pending':
      return 'secondary';
    default:
      return 'outline';
  }
}

// ============================================================================
// Dataset Components
// ============================================================================

interface DatasetCardProps {
  dataset: EvaluationDataset;
  onEdit: () => void;
  onDelete: () => void;
}

function DatasetCard({ dataset, onEdit, onDelete }: DatasetCardProps) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <Database className="h-5 w-5 text-muted-foreground" />
            <CardTitle className="text-lg">{dataset.name}</CardTitle>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={onEdit}>
                <Pencil className="h-4 w-4 mr-2" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onDelete} className="text-destructive">
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <CardDescription className="line-clamp-2">
          {dataset.description || 'No description'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-4">
            <span className="text-muted-foreground">
              <FileText className="h-4 w-4 inline mr-1" />
              {dataset.example_count} examples
            </span>
            <Badge variant="outline">{dataset.schema_type}</Badge>
          </div>
          <span className="text-muted-foreground text-xs">
            {formatDate(dataset.created_at)}
          </span>
        </div>
        {dataset.tags && dataset.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {dataset.tags.slice(0, 3).map((tag) => (
              <Badge key={tag} variant="secondary" className="text-xs">
                {tag}
              </Badge>
            ))}
            {dataset.tags.length > 3 && (
              <Badge variant="secondary" className="text-xs">
                +{dataset.tags.length - 3}
              </Badge>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function DatasetListItem({ dataset, onEdit, onDelete }: DatasetCardProps) {
  return (
    <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors">
      <div className="flex items-center gap-4 flex-1 min-w-0">
        <Database className="h-5 w-5 text-muted-foreground flex-shrink-0" />
        <div className="min-w-0 flex-1">
          <h3 className="font-medium truncate">{dataset.name}</h3>
          <p className="text-sm text-muted-foreground truncate">
            {dataset.description || 'No description'}
          </p>
        </div>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span>{dataset.example_count} examples</span>
          <Badge variant="outline">{dataset.schema_type}</Badge>
          <span className="text-xs">{formatDate(dataset.created_at)}</span>
        </div>
      </div>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" className="h-8 w-8 ml-2">
            <MoreVertical className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={onEdit}>
            <Pencil className="h-4 w-4 mr-2" />
            Edit
          </DropdownMenuItem>
          <DropdownMenuItem onClick={onDelete} className="text-destructive">
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

// ============================================================================
// Evaluator Components
// ============================================================================

interface EvaluatorCardProps {
  evaluator: Evaluator;
  onEdit: () => void;
  onDelete: () => void;
  onClone: () => void;
}

function EvaluatorCard({ evaluator, onEdit, onDelete, onClone }: EvaluatorCardProps) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <FlaskConical className="h-5 w-5 text-muted-foreground" />
            <CardTitle className="text-lg">{evaluator.name}</CardTitle>
            {evaluator.is_builtin && (
              <Badge variant="secondary" className="gap-1">
                <Lock className="h-3 w-3" />
                Built-in
              </Badge>
            )}
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {evaluator.is_builtin ? (
                <>
                  <DropdownMenuItem onClick={onEdit}>
                    <Eye className="h-4 w-4 mr-2" />
                    View
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={onClone}>
                    <Copy className="h-4 w-4 mr-2" />
                    Clone
                  </DropdownMenuItem>
                </>
              ) : (
                <>
                  <DropdownMenuItem onClick={onEdit}>
                    <Pencil className="h-4 w-4 mr-2" />
                    Edit
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={onClone}>
                    <Copy className="h-4 w-4 mr-2" />
                    Clone
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={onDelete} className="text-destructive">
                    <Trash2 className="h-4 w-4 mr-2" />
                    Delete
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <CardDescription className="line-clamp-2">
          {evaluator.description || 'No description'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-2">
          <Badge variant={evaluator.category === 'output' ? 'default' : 'secondary'}>
            {evaluator.category === 'output' ? 'Output' : 'Run Metadata'}
          </Badge>
          <Badge variant="outline">{evaluator.type.replace(/_/g, ' ')}</Badge>
        </div>
      </CardContent>
    </Card>
  );
}

function EvaluatorListItem({ evaluator, onEdit, onDelete, onClone }: EvaluatorCardProps) {
  return (
    <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors">
      <div className="flex items-center gap-4 flex-1 min-w-0">
        <FlaskConical className="h-5 w-5 text-muted-foreground flex-shrink-0" />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="font-medium truncate">{evaluator.name}</h3>
            {evaluator.is_builtin && (
              <Badge variant="secondary" className="gap-1 text-xs">
                <Lock className="h-3 w-3" />
                Built-in
              </Badge>
            )}
          </div>
          <p className="text-sm text-muted-foreground truncate">
            {evaluator.description || 'No description'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={evaluator.category === 'output' ? 'default' : 'secondary'}>
            {evaluator.category === 'output' ? 'Output' : 'Run Metadata'}
          </Badge>
          <Badge variant="outline">{evaluator.type.replace(/_/g, ' ')}</Badge>
        </div>
      </div>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" className="h-8 w-8 ml-2">
            <MoreVertical className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {evaluator.is_builtin ? (
            <>
              <DropdownMenuItem onClick={onEdit}>
                <Eye className="h-4 w-4 mr-2" />
                View
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onClone}>
                <Copy className="h-4 w-4 mr-2" />
                Clone
              </DropdownMenuItem>
            </>
          ) : (
            <>
              <DropdownMenuItem onClick={onEdit}>
                <Pencil className="h-4 w-4 mr-2" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onClone}>
                <Copy className="h-4 w-4 mr-2" />
                Clone
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onDelete} className="text-destructive">
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </DropdownMenuItem>
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

// ============================================================================
// Run Components
// ============================================================================

interface RunCardProps {
  run: EvaluationRun;
  onView: () => void;
  onExecute: () => void;
  onCancel: () => void;
  onDelete: () => void;
  isExecuting: boolean;
  isCancelling: boolean;
}

function RunCard({ run, onView, onExecute, onCancel, onDelete, isExecuting, isCancelling }: RunCardProps) {
  const passRate = run.total_examples > 0 && run.passed_examples != null
    ? ((run.passed_examples / run.total_examples) * 100).toFixed(1)
    : '0.0';

  return (
    <Card className="hover:shadow-md transition-shadow cursor-pointer" onClick={onView}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            {getStatusIcon(run.status)}
            <CardTitle className="text-lg">{run.name}</CardTitle>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onView(); }}>
                <Eye className="h-4 w-4 mr-2" />
                View Results
              </DropdownMenuItem>
              {run.status === 'pending' && (
                <DropdownMenuItem
                  onClick={(e) => { e.stopPropagation(); onExecute(); }}
                  disabled={isExecuting}
                >
                  <Play className="h-4 w-4 mr-2" />
                  {isExecuting ? 'Starting...' : 'Execute'}
                </DropdownMenuItem>
              )}
              {run.status === 'running' && (
                <DropdownMenuItem
                  onClick={(e) => { e.stopPropagation(); onCancel(); }}
                  disabled={isCancelling}
                >
                  <XCircle className="h-4 w-4 mr-2" />
                  {isCancelling ? 'Cancelling...' : 'Cancel'}
                </DropdownMenuItem>
              )}
              {run.status !== 'running' && (
                <DropdownMenuItem
                  onClick={(e) => { e.stopPropagation(); onDelete(); }}
                  className="text-destructive"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <CardDescription>
          Dataset: {run.dataset_name} | Agent: {run.agent_name || 'None'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-4">
            <Badge variant={getStatusBadgeVariant(run.status)}>{run.status}</Badge>
            <span className="text-muted-foreground">
              {run.completed_examples}/{run.total_examples} examples
            </span>
            {run.status === 'completed' && (
              <span className={`font-medium ${parseFloat(passRate) >= 80 ? 'text-green-600' : parseFloat(passRate) >= 50 ? 'text-yellow-600' : 'text-red-600'}`}>
                {passRate}% pass rate
              </span>
            )}
          </div>
          <span className="text-muted-foreground text-xs">
            {run.completed_at ? formatDate(run.completed_at) : formatDate(run.created_at)}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

function RunListItem({ run, onView, onExecute, onCancel, onDelete, isExecuting, isCancelling }: RunCardProps) {
  const passRate = run.total_examples > 0 && run.passed_examples != null
    ? ((run.passed_examples / run.total_examples) * 100).toFixed(1)
    : '0.0';

  return (
    <div
      className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors cursor-pointer"
      onClick={onView}
    >
      <div className="flex items-center gap-4 flex-1 min-w-0">
        {getStatusIcon(run.status)}
        <div className="min-w-0 flex-1">
          <h3 className="font-medium truncate">{run.name}</h3>
          <p className="text-sm text-muted-foreground truncate">
            Dataset: {run.dataset_name} | Agent: {run.agent_name || 'None'}
          </p>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <Badge variant={getStatusBadgeVariant(run.status)}>{run.status}</Badge>
          <span className="text-muted-foreground">
            {run.completed_examples}/{run.total_examples}
          </span>
          {run.status === 'completed' && (
            <span className={`font-medium ${parseFloat(passRate) >= 80 ? 'text-green-600' : parseFloat(passRate) >= 50 ? 'text-yellow-600' : 'text-red-600'}`}>
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
          <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onView(); }}>
            <Eye className="h-4 w-4 mr-2" />
            View Results
          </DropdownMenuItem>
          {run.status === 'pending' && (
            <DropdownMenuItem
              onClick={(e) => { e.stopPropagation(); onExecute(); }}
              disabled={isExecuting}
            >
              <Play className="h-4 w-4 mr-2" />
              {isExecuting ? 'Starting...' : 'Execute'}
            </DropdownMenuItem>
          )}
          {run.status === 'running' && (
            <DropdownMenuItem
              onClick={(e) => { e.stopPropagation(); onCancel(); }}
              disabled={isCancelling}
            >
              <XCircle className="h-4 w-4 mr-2" />
              {isCancelling ? 'Cancelling...' : 'Cancel'}
            </DropdownMenuItem>
          )}
          {run.status !== 'running' && (
            <DropdownMenuItem
              onClick={(e) => { e.stopPropagation(); onDelete(); }}
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
}

// ============================================================================
// Main Page Component
// ============================================================================

export default function EvaluationsPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();

  // Read initial tab from URL query parameter
  const getInitialTab = (): 'datasets' | 'evaluators' | 'runs' => {
    const tabParam = searchParams.get('tab');
    if (tabParam === 'evaluators' || tabParam === 'runs' || tabParam === 'datasets') {
      return tabParam;
    }
    return 'datasets';
  };

  const [activeTab, setActiveTab] = useState<'datasets' | 'evaluators' | 'runs'>(getInitialTab);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>(() => {
    const saved = localStorage.getItem(EVALUATIONS_VIEW_MODE_KEY);
    return saved === 'list' ? 'list' : 'grid';
  });

  // Create Run dialog state
  const [showCreateRunDialog, setShowCreateRunDialog] = useState(false);
  const [newRunName, setNewRunName] = useState('');
  const [newRunDatasetId, setNewRunDatasetId] = useState<number | null>(null);
  const [newRunAgentId, setNewRunAgentId] = useState<number | null>(null);
  const [newRunEvaluatorIds, setNewRunEvaluatorIds] = useState<number[]>([]);

  // Sync tab with URL query parameter
  useEffect(() => {
    const tabParam = searchParams.get('tab');
    if (tabParam === 'evaluators' || tabParam === 'runs' || tabParam === 'datasets') {
      if (tabParam !== activeTab) {
        setActiveTab(tabParam);
      }
    }
  }, [searchParams]);

  // Update URL when tab changes
  const handleTabChange = (tab: 'datasets' | 'evaluators' | 'runs') => {
    setActiveTab(tab);
    if (tab === 'datasets') {
      // Remove tab param for default tab
      searchParams.delete('tab');
    } else {
      searchParams.set('tab', tab);
    }
    setSearchParams(searchParams, { replace: true });
  };

  // Open dialog when navigating to /evaluations/runs/new
  useEffect(() => {
    if (location.pathname === '/evaluations/runs/new') {
      handleTabChange('runs');
      setShowCreateRunDialog(true);
    }
  }, [location.pathname]);

  // Datasets state
  const [datasetPage, setDatasetPage] = useState(1);
  const [datasetSearch, setDatasetSearch] = useState('');
  const [datasetToDelete, setDatasetToDelete] = useState<EvaluationDataset | null>(null);

  // Evaluators state
  const [evaluatorPage, setEvaluatorPage] = useState(1);
  const [evaluatorCategory, setEvaluatorCategory] = useState<EvaluatorCategory | 'all'>('all');
  const [evaluatorToDelete, setEvaluatorToDelete] = useState<Evaluator | null>(null);

  // Runs state
  const [runPage, setRunPage] = useState(1);
  const [runStatus, setRunStatus] = useState<EvaluationStatus | 'all'>('all');
  const [runToDelete, setRunToDelete] = useState<EvaluationRun | null>(null);

  // Queries
  const {
    data: datasetsData,
    isLoading: datasetsLoading,
    error: datasetsError,
  } = useDatasets({ page: datasetPage, search: datasetSearch || undefined });

  const {
    data: evaluatorsData,
    isLoading: evaluatorsLoading,
    error: evaluatorsError,
  } = useEvaluators({
    page: evaluatorPage,
    category: evaluatorCategory === 'all' ? undefined : evaluatorCategory,
  });

  const {
    data: runsData,
    isLoading: runsLoading,
    error: runsError,
  } = useEvaluationRuns({
    page: runPage,
    status: runStatus === 'all' ? undefined : runStatus,
  });

  // Agents for creating runs
  const { data: agentsData } = useAgents({ page: 1, pageSize: 100 });

  // All datasets for creating runs (separate from paginated list)
  const { data: allDatasetsData } = useDatasets({ page: 1, pageSize: 100 });

  // All evaluators for creating runs (separate from paginated list)
  const { data: allEvaluatorsData } = useEvaluators({ page: 1, pageSize: 100 });

  // Mutations
  const deleteDataset = useDeleteDataset();
  const deleteEvaluator = useDeleteEvaluator();
  const cloneEvaluator = useCloneEvaluator();
  const createRun = useCreateEvaluationRun();
  const executeRun = useExecuteEvaluationRun();
  const cancelRun = useCancelEvaluationRun();
  const deleteRun = useDeleteEvaluationRun();

  const handleViewModeChange = (mode: 'grid' | 'list') => {
    setViewMode(mode);
    localStorage.setItem(EVALUATIONS_VIEW_MODE_KEY, mode);
  };

  const handleCloneEvaluator = async (evaluator: Evaluator) => {
    try {
      const cloned = await cloneEvaluator.mutateAsync({ id: evaluator.id });
      navigate(`/evaluations/evaluators/${cloned.id}`);
    } catch {
      // Error handled by mutation
    }
  };

  const handleOpenCreateRunDialog = () => {
    setNewRunName('');
    setNewRunDatasetId(null);
    setNewRunAgentId(null);
    setNewRunEvaluatorIds([]);
    setShowCreateRunDialog(true);
  };

  const handleCloseCreateRunDialog = () => {
    setShowCreateRunDialog(false);
    // Navigate back to /evaluations if we came from /evaluations/runs/new
    if (location.pathname === '/evaluations/runs/new') {
      navigate('/evaluations');
    }
  };

  const handleCreateRun = async () => {
    if (!newRunName.trim() || !newRunDatasetId || !newRunAgentId || newRunEvaluatorIds.length === 0) {
      return;
    }

    try {
      const run = await createRun.mutateAsync({
        name: newRunName.trim(),
        dataset_id: newRunDatasetId,
        agent_id: newRunAgentId,
        evaluator_ids: newRunEvaluatorIds,
      });
      handleCloseCreateRunDialog();
      navigate(`/evaluations/runs/${run.id}`);
    } catch {
      // Error handled by mutation
    }
  };

  const toggleEvaluatorSelection = (id: number) => {
    setNewRunEvaluatorIds((prev) =>
      prev.includes(id) ? prev.filter((eid) => eid !== id) : [...prev, id]
    );
  };

  return (
    <div className="container mx-auto py-6 px-4 max-w-7xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">Evaluations</h1>
          <p className="text-muted-foreground">
            Test and evaluate your agents with datasets and evaluators
          </p>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={(v) => handleTabChange(v as typeof activeTab)}>
        <div className="flex items-center justify-between mb-4">
          <TabsList>
            <TabsTrigger value="datasets" className="gap-2">
              <Database className="h-4 w-4" />
              Datasets
              {datasetsData && (
                <Badge variant="secondary" className="ml-1">
                  {datasetsData.total}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="evaluators" className="gap-2">
              <FlaskConical className="h-4 w-4" />
              Evaluators
              {evaluatorsData && (
                <Badge variant="secondary" className="ml-1">
                  {evaluatorsData.total}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="runs" className="gap-2">
              <Play className="h-4 w-4" />
              Runs
              {runsData && (
                <Badge variant="secondary" className="ml-1">
                  {runsData.total}
                </Badge>
              )}
            </TabsTrigger>
          </TabsList>

          <div className="flex items-center gap-2">
            <div className="flex items-center border rounded-md">
              <Button
                variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
                size="icon"
                className="h-8 w-8 rounded-r-none"
                onClick={() => handleViewModeChange('grid')}
              >
                <LayoutGrid className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === 'list' ? 'secondary' : 'ghost'}
                size="icon"
                className="h-8 w-8 rounded-l-none"
                onClick={() => handleViewModeChange('list')}
              >
                <List className="h-4 w-4" />
              </Button>
            </div>
            {activeTab === 'datasets' && (
              <Button onClick={() => navigate('/evaluations/datasets/new')}>
                <Plus className="h-4 w-4 mr-2" />
                New Dataset
              </Button>
            )}
            {activeTab === 'evaluators' && (
              <Button onClick={() => navigate('/evaluations/evaluators/new')}>
                <Plus className="h-4 w-4 mr-2" />
                New Evaluator
              </Button>
            )}
            {activeTab === 'runs' && (
              <Button onClick={handleOpenCreateRunDialog}>
                <Plus className="h-4 w-4 mr-2" />
                New Run
              </Button>
            )}
          </div>
        </div>

        {/* Datasets Tab */}
        <TabsContent value="datasets">
          <div className="mb-4">
            <div className="relative max-w-md">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search datasets..."
                value={datasetSearch}
                onChange={(e) => setDatasetSearch(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>

          {datasetsLoading ? (
            <div className="flex justify-center py-12">
              <Spinner size="lg" />
            </div>
          ) : datasetsError ? (
            <Alert variant="destructive">
              <AlertDescription>{getErrorMessage(datasetsError)}</AlertDescription>
            </Alert>
          ) : datasetsData?.datasets.length === 0 ? (
            <Card className="py-12">
              <div className="text-center">
                <Database className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium mb-2">No datasets yet</h3>
                <p className="text-muted-foreground mb-4">
                  Create your first dataset to start evaluating your agents.
                </p>
                <Button onClick={() => navigate('/evaluations/datasets/new')}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Dataset
                </Button>
              </div>
            </Card>
          ) : viewMode === 'grid' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {datasetsData?.datasets.map((dataset) => (
                <DatasetCard
                  key={dataset.id}
                  dataset={dataset}
                  onEdit={() => navigate(`/evaluations/datasets/${dataset.id}`)}
                  onDelete={() => setDatasetToDelete(dataset)}
                />
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {datasetsData?.datasets.map((dataset) => (
                <DatasetListItem
                  key={dataset.id}
                  dataset={dataset}
                  onEdit={() => navigate(`/evaluations/datasets/${dataset.id}`)}
                  onDelete={() => setDatasetToDelete(dataset)}
                />
              ))}
            </div>
          )}

          {datasetsData && datasetsData.total > 50 && (
            <div className="flex items-center justify-center gap-4 mt-4">
              <Button
                variant="outline"
                size="sm"
                disabled={datasetPage === 1}
                onClick={() => setDatasetPage((p) => p - 1)}
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {datasetPage} of {Math.ceil(datasetsData.total / 50)}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={datasetPage >= Math.ceil(datasetsData.total / 50)}
                onClick={() => setDatasetPage((p) => p + 1)}
              >
                Next
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          )}
        </TabsContent>

        {/* Evaluators Tab */}
        <TabsContent value="evaluators">
          <div className="mb-4">
            <Select
              value={evaluatorCategory}
              onValueChange={(v) => setEvaluatorCategory(v as typeof evaluatorCategory)}
            >
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Filter by category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                <SelectItem value="output">Output Evaluators</SelectItem>
                <SelectItem value="run_metadata">Run Metadata Evaluators</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {evaluatorsLoading ? (
            <div className="flex justify-center py-12">
              <Spinner size="lg" />
            </div>
          ) : evaluatorsError ? (
            <Alert variant="destructive">
              <AlertDescription>{getErrorMessage(evaluatorsError)}</AlertDescription>
            </Alert>
          ) : evaluatorsData?.evaluators.length === 0 ? (
            <Card className="py-12">
              <div className="text-center">
                <FlaskConical className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium mb-2">No evaluators yet</h3>
                <p className="text-muted-foreground mb-4">
                  Create custom evaluators to test your agents.
                </p>
                <Button onClick={() => navigate('/evaluations/evaluators/new')}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Evaluator
                </Button>
              </div>
            </Card>
          ) : viewMode === 'grid' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {evaluatorsData?.evaluators.map((evaluator) => (
                <EvaluatorCard
                  key={evaluator.id}
                  evaluator={evaluator}
                  onEdit={() => navigate(`/evaluations/evaluators/${evaluator.id}`)}
                  onDelete={() => setEvaluatorToDelete(evaluator)}
                  onClone={() => handleCloneEvaluator(evaluator)}
                />
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {evaluatorsData?.evaluators.map((evaluator) => (
                <EvaluatorListItem
                  key={evaluator.id}
                  evaluator={evaluator}
                  onEdit={() => navigate(`/evaluations/evaluators/${evaluator.id}`)}
                  onDelete={() => setEvaluatorToDelete(evaluator)}
                  onClone={() => handleCloneEvaluator(evaluator)}
                />
              ))}
            </div>
          )}

          {evaluatorsData && evaluatorsData.total > 50 && (
            <div className="flex items-center justify-center gap-4 mt-4">
              <Button
                variant="outline"
                size="sm"
                disabled={evaluatorPage === 1}
                onClick={() => setEvaluatorPage((p) => p - 1)}
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {evaluatorPage} of {Math.ceil(evaluatorsData.total / 50)}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={evaluatorPage >= Math.ceil(evaluatorsData.total / 50)}
                onClick={() => setEvaluatorPage((p) => p + 1)}
              >
                Next
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          )}
        </TabsContent>

        {/* Runs Tab */}
        <TabsContent value="runs">
          <div className="mb-4">
            <Select
              value={runStatus}
              onValueChange={(v) => setRunStatus(v as typeof runStatus)}
            >
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="running">Running</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
                <SelectItem value="cancelled">Cancelled</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {runsLoading ? (
            <div className="flex justify-center py-12">
              <Spinner size="lg" />
            </div>
          ) : runsError ? (
            <Alert variant="destructive">
              <AlertDescription>{getErrorMessage(runsError)}</AlertDescription>
            </Alert>
          ) : runsData?.runs.length === 0 ? (
            <Card className="py-12">
              <div className="text-center">
                <Play className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium mb-2">No evaluation runs yet</h3>
                <p className="text-muted-foreground mb-4">
                  Create your first evaluation run to test your agents.
                </p>
                <Button onClick={handleOpenCreateRunDialog}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Run
                </Button>
              </div>
            </Card>
          ) : viewMode === 'grid' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {runsData?.runs.map((run) => (
                <RunCard
                  key={run.id}
                  run={run}
                  onView={() => navigate(`/evaluations/runs/${run.id}`)}
                  onExecute={() => executeRun.mutate(run.id)}
                  onCancel={() => cancelRun.mutate(run.id)}
                  onDelete={() => setRunToDelete(run)}
                  isExecuting={executeRun.isPending}
                  isCancelling={cancelRun.isPending}
                />
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {runsData?.runs.map((run) => (
                <RunListItem
                  key={run.id}
                  run={run}
                  onView={() => navigate(`/evaluations/runs/${run.id}`)}
                  onExecute={() => executeRun.mutate(run.id)}
                  onCancel={() => cancelRun.mutate(run.id)}
                  onDelete={() => setRunToDelete(run)}
                  isExecuting={executeRun.isPending}
                  isCancelling={cancelRun.isPending}
                />
              ))}
            </div>
          )}

          {runsData && runsData.total > 50 && (
            <div className="flex items-center justify-center gap-4 mt-4">
              <Button
                variant="outline"
                size="sm"
                disabled={runPage === 1}
                onClick={() => setRunPage((p) => p - 1)}
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {runPage} of {Math.ceil(runsData.total / 50)}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={runPage >= Math.ceil(runsData.total / 50)}
                onClick={() => setRunPage((p) => p + 1)}
              >
                Next
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Delete Dialogs */}
      <DeleteConfirmDialog
        open={!!datasetToDelete}
        onOpenChange={(open: boolean) => !open && setDatasetToDelete(null)}
        itemName={datasetToDelete?.name || 'dataset'}
        itemType="dataset"
        onConfirm={async () => {
          if (datasetToDelete) {
            await deleteDataset.mutateAsync(datasetToDelete.id);
            setDatasetToDelete(null);
          }
        }}
        isLoading={deleteDataset.isPending}
      />

      <DeleteConfirmDialog
        open={!!evaluatorToDelete}
        onOpenChange={(open: boolean) => !open && setEvaluatorToDelete(null)}
        itemName={evaluatorToDelete?.name || 'evaluator'}
        itemType="evaluator"
        onConfirm={async () => {
          if (evaluatorToDelete) {
            await deleteEvaluator.mutateAsync(evaluatorToDelete.id);
            setEvaluatorToDelete(null);
          }
        }}
        isLoading={deleteEvaluator.isPending}
      />

      <DeleteConfirmDialog
        open={!!runToDelete}
        onOpenChange={(open: boolean) => !open && setRunToDelete(null)}
        itemName={runToDelete?.name || 'run'}
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
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Create Evaluation Run</DialogTitle>
            <DialogDescription>
              Configure a new evaluation run to test your agent against a dataset.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Run Name */}
            <div className="space-y-2">
              <Label htmlFor="run-name">Run Name *</Label>
              <Input
                id="run-name"
                placeholder="e.g., Math Test Run 1"
                value={newRunName}
                onChange={(e) => setNewRunName(e.target.value)}
              />
            </div>

            {/* Dataset Selection */}
            <div className="space-y-2">
              <Label>Dataset *</Label>
              <Select
                value={newRunDatasetId?.toString() || ''}
                onValueChange={(v) => setNewRunDatasetId(parseInt(v))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a dataset" />
                </SelectTrigger>
                <SelectContent>
                  {allDatasetsData?.datasets.map((dataset) => (
                    <SelectItem key={dataset.id} value={dataset.id.toString()}>
                      {dataset.name} ({dataset.example_count} examples)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {allDatasetsData?.datasets.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  No datasets available.{' '}
                  <Button variant="link" className="p-0 h-auto" onClick={() => navigate('/evaluations/datasets/new')}>
                    Create one first.
                  </Button>
                </p>
              )}
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

            {/* Evaluators Selection */}
            <div className="space-y-2">
              <Label>Evaluators * ({newRunEvaluatorIds.length} selected)</Label>
              <div className="border rounded-md p-4 max-h-64 overflow-y-auto space-y-2">
                {allEvaluatorsData?.evaluators.map((evaluator) => (
                  <div
                    key={evaluator.id}
                    className="flex items-center space-x-2 py-1 hover:bg-muted/50 rounded px-2 cursor-pointer"
                    onClick={() => toggleEvaluatorSelection(evaluator.id)}
                  >
                    <Checkbox
                      id={`evaluator-${evaluator.id}`}
                      checked={newRunEvaluatorIds.includes(evaluator.id)}
                      onClick={(e) => e.stopPropagation()}
                      onCheckedChange={() => toggleEvaluatorSelection(evaluator.id)}
                    />
                    <div className="flex-1 min-w-0">
                      <label
                        htmlFor={`evaluator-${evaluator.id}`}
                        className="text-sm font-medium cursor-pointer"
                      >
                        {evaluator.name}
                        {evaluator.is_builtin && (
                          <Badge variant="secondary" className="ml-2 text-xs">Built-in</Badge>
                        )}
                      </label>
                      <p className="text-xs text-muted-foreground truncate">
                        {evaluator.description}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
              {allEvaluatorsData?.evaluators.length === 0 && (
                <p className="text-sm text-muted-foreground">No evaluators available.</p>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={handleCloseCreateRunDialog}>
              Cancel
            </Button>
            <Button
              onClick={handleCreateRun}
              disabled={
                !newRunName.trim() ||
                !newRunDatasetId ||
                !newRunAgentId ||
                newRunEvaluatorIds.length === 0 ||
                createRun.isPending
              }
            >
              {createRun.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Run'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
