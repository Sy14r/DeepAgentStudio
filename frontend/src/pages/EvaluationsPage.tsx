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
  useEvaluations,
  useCreateEvaluation,
  useDeleteEvaluation,
  getErrorMessage,
} from '@/api/hooks';
import type {
  EvaluationDataset,
  Evaluator,
  Evaluation,
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
// Evaluation Components (Reusable Config)
// ============================================================================

interface EvaluationCardProps {
  evaluation: Evaluation;
  onView: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

function EvaluationCard({ evaluation, onView, onEdit, onDelete }: EvaluationCardProps) {
  return (
    <Card className="hover:shadow-md transition-shadow cursor-pointer" onClick={onView}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <Play className="h-5 w-5 text-muted-foreground" />
            <CardTitle className="text-lg">{evaluation.name}</CardTitle>
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
                View & Run
              </DropdownMenuItem>
              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onEdit(); }}>
                <Pencil className="h-4 w-4 mr-2" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={(e) => { e.stopPropagation(); onDelete(); }}
                className="text-destructive"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <CardDescription className="line-clamp-2">
          {evaluation.description || 'No description'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-4">
            <span className="text-muted-foreground">
              <Database className="h-4 w-4 inline mr-1" />
              {evaluation.dataset_name || 'Unknown dataset'}
            </span>
            <span className="text-muted-foreground">
              <FlaskConical className="h-4 w-4 inline mr-1" />
              {evaluation.evaluator_count} evaluators
            </span>
          </div>
          <Badge variant="secondary">{evaluation.run_count} runs</Badge>
        </div>
        <div className="text-xs text-muted-foreground mt-2">
          {formatDate(evaluation.created_at)}
        </div>
      </CardContent>
    </Card>
  );
}

function EvaluationListItem({ evaluation, onView, onEdit, onDelete }: EvaluationCardProps) {
  return (
    <div
      className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors cursor-pointer"
      onClick={onView}
    >
      <div className="flex items-center gap-4 flex-1 min-w-0">
        <Play className="h-5 w-5 text-muted-foreground flex-shrink-0" />
        <div className="min-w-0 flex-1">
          <h3 className="font-medium truncate">{evaluation.name}</h3>
          <p className="text-sm text-muted-foreground truncate">
            {evaluation.description || 'No description'}
          </p>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-muted-foreground">
            {evaluation.dataset_name || 'Unknown'}
          </span>
          <span className="text-muted-foreground">
            {evaluation.evaluator_count} evaluators
          </span>
          <Badge variant="secondary">{evaluation.run_count} runs</Badge>
          <span className="text-muted-foreground text-xs">
            {formatDate(evaluation.created_at)}
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
            View & Run
          </DropdownMenuItem>
          <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onEdit(); }}>
            <Pencil className="h-4 w-4 mr-2" />
            Edit
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
            className="text-destructive"
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </DropdownMenuItem>
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
  const getInitialTab = (): 'datasets' | 'evaluators' | 'evaluations' => {
    const tabParam = searchParams.get('tab');
    if (tabParam === 'evaluators' || tabParam === 'evaluations' || tabParam === 'datasets') {
      return tabParam;
    }
    return 'datasets';
  };

  const [activeTab, setActiveTab] = useState<'datasets' | 'evaluators' | 'evaluations'>(getInitialTab);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>(() => {
    const saved = localStorage.getItem(EVALUATIONS_VIEW_MODE_KEY);
    return saved === 'list' ? 'list' : 'grid';
  });

  // Create Evaluation dialog state
  const [showCreateEvaluationDialog, setShowCreateEvaluationDialog] = useState(false);
  const [newEvaluationName, setNewEvaluationName] = useState('');
  const [newEvaluationDescription, setNewEvaluationDescription] = useState('');
  const [newEvaluationDatasetId, setNewEvaluationDatasetId] = useState<number | null>(null);
  const [newEvaluationEvaluatorIds, setNewEvaluationEvaluatorIds] = useState<number[]>([]);

  // Sync tab with URL query parameter
  useEffect(() => {
    const tabParam = searchParams.get('tab');
    if (tabParam === 'evaluators' || tabParam === 'evaluations' || tabParam === 'datasets') {
      if (tabParam !== activeTab) {
        setActiveTab(tabParam);
      }
    }
  }, [searchParams]);

  // Update URL when tab changes
  const handleTabChange = (tab: 'datasets' | 'evaluators' | 'evaluations') => {
    setActiveTab(tab);
    if (tab === 'datasets') {
      // Remove tab param for default tab
      searchParams.delete('tab');
    } else {
      searchParams.set('tab', tab);
    }
    setSearchParams(searchParams, { replace: true });
  };

  // Open dialog when navigating to /evaluations/new
  useEffect(() => {
    if (location.pathname === '/evaluations/new') {
      handleTabChange('evaluations');
      setShowCreateEvaluationDialog(true);
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

  // Evaluations state
  const [evaluationPage, setEvaluationPage] = useState(1);
  const [evaluationSearch, setEvaluationSearch] = useState('');
  const [evaluationToDelete, setEvaluationToDelete] = useState<Evaluation | null>(null);

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
    data: evaluationsData,
    isLoading: evaluationsLoading,
    error: evaluationsError,
  } = useEvaluations({
    page: evaluationPage,
    search: evaluationSearch || undefined,
  });

  // All datasets for creating evaluations (separate from paginated list)
  const { data: allDatasetsData } = useDatasets({ page: 1, pageSize: 100 });

  // All evaluators for creating evaluations (separate from paginated list)
  const { data: allEvaluatorsData } = useEvaluators({ page: 1, pageSize: 100 });

  // Mutations
  const deleteDataset = useDeleteDataset();
  const deleteEvaluator = useDeleteEvaluator();
  const cloneEvaluator = useCloneEvaluator();
  const createEvaluation = useCreateEvaluation();
  const deleteEvaluation = useDeleteEvaluation();

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

  const handleOpenCreateEvaluationDialog = () => {
    setNewEvaluationName('');
    setNewEvaluationDescription('');
    setNewEvaluationDatasetId(null);
    setNewEvaluationEvaluatorIds([]);
    setShowCreateEvaluationDialog(true);
  };

  const handleCloseCreateEvaluationDialog = () => {
    setShowCreateEvaluationDialog(false);
    // Navigate back to /evaluations if we came from /evaluations/new
    if (location.pathname === '/evaluations/new') {
      navigate('/evaluations?tab=evaluations');
    }
  };

  const handleCreateEvaluation = async () => {
    if (!newEvaluationName.trim() || !newEvaluationDatasetId || newEvaluationEvaluatorIds.length === 0) {
      return;
    }

    try {
      const evaluation = await createEvaluation.mutateAsync({
        name: newEvaluationName.trim(),
        description: newEvaluationDescription.trim() || undefined,
        dataset_id: newEvaluationDatasetId,
        evaluator_ids: newEvaluationEvaluatorIds,
      });
      handleCloseCreateEvaluationDialog();
      navigate(`/evaluations/${evaluation.id}`);
    } catch {
      // Error handled by mutation
    }
  };

  const toggleEvaluatorSelection = (id: number) => {
    setNewEvaluationEvaluatorIds((prev) =>
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
            <TabsTrigger value="evaluations" className="gap-2">
              <Play className="h-4 w-4" />
              Evaluations
              {evaluationsData && (
                <Badge variant="secondary" className="ml-1">
                  {evaluationsData.total}
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
            {activeTab === 'evaluations' && (
              <Button onClick={handleOpenCreateEvaluationDialog}>
                <Plus className="h-4 w-4 mr-2" />
                New Evaluation
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

        {/* Evaluations Tab */}
        <TabsContent value="evaluations">
          <div className="mb-4">
            <div className="relative max-w-md">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search evaluations..."
                value={evaluationSearch}
                onChange={(e) => setEvaluationSearch(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>

          {evaluationsLoading ? (
            <div className="flex justify-center py-12">
              <Spinner size="lg" />
            </div>
          ) : evaluationsError ? (
            <Alert variant="destructive">
              <AlertDescription>{getErrorMessage(evaluationsError)}</AlertDescription>
            </Alert>
          ) : evaluationsData?.evaluations.length === 0 ? (
            <Card className="py-12">
              <div className="text-center">
                <Play className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium mb-2">No evaluations yet</h3>
                <p className="text-muted-foreground mb-4">
                  Create an evaluation to define how you want to test your agents.
                </p>
                <Button onClick={handleOpenCreateEvaluationDialog}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Evaluation
                </Button>
              </div>
            </Card>
          ) : viewMode === 'grid' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {evaluationsData?.evaluations.map((evaluation) => (
                <EvaluationCard
                  key={evaluation.id}
                  evaluation={evaluation}
                  onView={() => navigate(`/evaluations/${evaluation.id}`)}
                  onEdit={() => navigate(`/evaluations/${evaluation.id}/edit`)}
                  onDelete={() => setEvaluationToDelete(evaluation)}
                />
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {evaluationsData?.evaluations.map((evaluation) => (
                <EvaluationListItem
                  key={evaluation.id}
                  evaluation={evaluation}
                  onView={() => navigate(`/evaluations/${evaluation.id}`)}
                  onEdit={() => navigate(`/evaluations/${evaluation.id}/edit`)}
                  onDelete={() => setEvaluationToDelete(evaluation)}
                />
              ))}
            </div>
          )}

          {evaluationsData && evaluationsData.total > 50 && (
            <div className="flex items-center justify-center gap-4 mt-4">
              <Button
                variant="outline"
                size="sm"
                disabled={evaluationPage === 1}
                onClick={() => setEvaluationPage((p) => p - 1)}
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {evaluationPage} of {Math.ceil(evaluationsData.total / 50)}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={evaluationPage >= Math.ceil(evaluationsData.total / 50)}
                onClick={() => setEvaluationPage((p) => p + 1)}
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
        open={!!evaluationToDelete}
        onOpenChange={(open: boolean) => !open && setEvaluationToDelete(null)}
        itemName={evaluationToDelete?.name || 'evaluation'}
        itemType="evaluation"
        onConfirm={async () => {
          if (evaluationToDelete) {
            await deleteEvaluation.mutateAsync(evaluationToDelete.id);
            setEvaluationToDelete(null);
          }
        }}
        isLoading={deleteEvaluation.isPending}
      />

      {/* Create Evaluation Dialog */}
      <Dialog open={showCreateEvaluationDialog} onOpenChange={(open) => !open && handleCloseCreateEvaluationDialog()}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Create Evaluation</DialogTitle>
            <DialogDescription>
              Define a reusable evaluation configuration. You can run it against different agents later.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Evaluation Name */}
            <div className="space-y-2">
              <Label htmlFor="evaluation-name">Name *</Label>
              <Input
                id="evaluation-name"
                placeholder="e.g., Math Problems Test"
                value={newEvaluationName}
                onChange={(e) => setNewEvaluationName(e.target.value)}
              />
            </div>

            {/* Description */}
            <div className="space-y-2">
              <Label htmlFor="evaluation-description">Description</Label>
              <Input
                id="evaluation-description"
                placeholder="Optional description of what this evaluation tests..."
                value={newEvaluationDescription}
                onChange={(e) => setNewEvaluationDescription(e.target.value)}
              />
            </div>

            {/* Dataset Selection */}
            <div className="space-y-2">
              <Label>Dataset *</Label>
              <Select
                value={newEvaluationDatasetId?.toString() || ''}
                onValueChange={(v) => setNewEvaluationDatasetId(parseInt(v))}
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

            {/* Evaluators Selection */}
            <div className="space-y-2">
              <Label>Evaluators * ({newEvaluationEvaluatorIds.length} selected)</Label>
              <div className="border rounded-md p-4 max-h-64 overflow-y-auto space-y-2">
                {allEvaluatorsData?.evaluators.map((evaluator) => (
                  <div
                    key={evaluator.id}
                    className="flex items-center space-x-2 py-1 hover:bg-muted/50 rounded px-2 cursor-pointer"
                    onClick={() => toggleEvaluatorSelection(evaluator.id)}
                  >
                    <Checkbox
                      id={`evaluator-${evaluator.id}`}
                      checked={newEvaluationEvaluatorIds.includes(evaluator.id)}
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
            <Button variant="outline" onClick={handleCloseCreateEvaluationDialog}>
              Cancel
            </Button>
            <Button
              onClick={handleCreateEvaluation}
              disabled={
                !newEvaluationName.trim() ||
                !newEvaluationDatasetId ||
                newEvaluationEvaluatorIds.length === 0 ||
                createEvaluation.isPending
              }
            >
              {createEvaluation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Evaluation'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
