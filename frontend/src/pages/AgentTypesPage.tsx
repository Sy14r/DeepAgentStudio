import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Button,
  Input,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  Badge,
  Spinner,
  Alert,
  AlertDescription,
} from '@/components/ui';
import {
  Brain,
  ListChecks,
  MessageCircle,
  Sparkles,
  Plus,
  Search,
  Grid3X3,
  List,
  ChevronLeft,
  ChevronRight,
  MoreVertical,
  Pencil,
  Copy,
  Trash2,
  Lock,
} from 'lucide-react';
import { useAgentTypes, useDeleteAgentType, useCloneAgentType, getErrorMessage } from '@/api/hooks';
import { AgentTypeConfig, ExecutionStrategy } from '@/api/types';

const STRATEGY_OPTIONS: { value: ExecutionStrategy | 'all'; label: string }[] = [
  { value: 'all', label: 'All Strategies' },
  { value: 'react', label: 'ReAct' },
  { value: 'plan_and_execute', label: 'Plan & Execute' },
  { value: 'conversational', label: 'Conversational' },
  { value: 'codeact', label: 'CodeAct' },
];

const STRATEGY_LABELS: Record<ExecutionStrategy, string> = {
  react: 'ReAct',
  plan_and_execute: 'Plan & Execute',
  conversational: 'Conversational',
  codeact: 'CodeAct',
};

const STRATEGY_COLORS: Record<ExecutionStrategy, string> = {
  react: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  plan_and_execute: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
  conversational: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  codeact: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
};

// Icon mapping for agent types
const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  brain: Brain,
  'list-checks': ListChecks,
  'message-circle': MessageCircle,
  sparkles: Sparkles,
};

function getIconComponent(iconName: string | null): React.ComponentType<{ className?: string }> {
  if (!iconName) return Sparkles;
  return ICON_MAP[iconName] || Sparkles;
}

interface AgentTypeCardProps {
  agentType: AgentTypeConfig;
  onEdit: (id: number) => void;
  onClone: (id: number) => void;
  onDelete: (id: number) => void;
}

function AgentTypeCard({ agentType, onEdit, onClone, onDelete }: AgentTypeCardProps) {
  const IconComponent = getIconComponent(agentType.icon);

  return (
    <Card className="group relative hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <IconComponent className="h-5 w-5 text-primary" />
            </div>
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                {agentType.name}
                {agentType.is_builtin && (
                  <Lock className="h-3 w-3 text-muted-foreground" />
                )}
              </CardTitle>
              <div className="flex items-center gap-2 mt-1">
                <Badge className={STRATEGY_COLORS[agentType.execution_strategy]}>
                  {STRATEGY_LABELS[agentType.execution_strategy]}
                </Badge>
                {agentType.is_builtin && (
                  <Badge variant="outline" className="text-xs">Builtin</Badge>
                )}
              </div>
            </div>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => onEdit(agentType.id)}>
                <Pencil className="mr-2 h-4 w-4" />
                {agentType.is_builtin ? 'View' : 'Edit'}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onClone(agentType.id)}>
                <Copy className="mr-2 h-4 w-4" />
                Clone
              </DropdownMenuItem>
              {!agentType.is_builtin && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    className="text-destructive"
                    onClick={() => onDelete(agentType.id)}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent>
        <CardDescription className="line-clamp-2 min-h-[2.5rem]">
          {agentType.description || 'No description'}
        </CardDescription>
        <div className="mt-3 flex items-center gap-4 text-sm text-muted-foreground">
          <span>Max iterations: {agentType.max_iterations}</span>
          {agentType.recommended_tools.length > 0 && (
            <span>{agentType.recommended_tools.length} recommended tools</span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

interface AgentTypeListItemProps {
  agentType: AgentTypeConfig;
  onEdit: (id: number) => void;
  onClone: (id: number) => void;
  onDelete: (id: number) => void;
}

function AgentTypeListItem({ agentType, onEdit, onClone, onDelete }: AgentTypeListItemProps) {
  const IconComponent = getIconComponent(agentType.icon);

  return (
    <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent/50 transition-colors group">
      <div className="flex items-center gap-4">
        <div className="p-2 rounded-lg bg-primary/10">
          <IconComponent className="h-5 w-5 text-primary" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-medium">{agentType.name}</span>
            {agentType.is_builtin && (
              <Lock className="h-3 w-3 text-muted-foreground" />
            )}
            <Badge className={STRATEGY_COLORS[agentType.execution_strategy]}>
              {STRATEGY_LABELS[agentType.execution_strategy]}
            </Badge>
            {agentType.is_builtin && (
              <Badge variant="outline" className="text-xs">Builtin</Badge>
            )}
          </div>
          <p className="text-sm text-muted-foreground line-clamp-1">
            {agentType.description || 'No description'}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground mr-4">
          Max: {agentType.max_iterations}
        </span>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => onEdit(agentType.id)}>
              <Pencil className="mr-2 h-4 w-4" />
              {agentType.is_builtin ? 'View' : 'Edit'}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onClone(agentType.id)}>
              <Copy className="mr-2 h-4 w-4" />
              Clone
            </DropdownMenuItem>
            {!agentType.is_builtin && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  className="text-destructive"
                  onClick={() => onDelete(agentType.id)}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}

export function AgentTypesPage() {
  const navigate = useNavigate();

  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [search, setSearch] = useState('');
  const [strategyFilter, setStrategyFilter] = useState<ExecutionStrategy | 'all'>('all');
  const [page, setPage] = useState(1);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [typeToDelete, setTypeToDelete] = useState<AgentTypeConfig | null>(null);

  const pageSize = 12;

  const {
    data: agentTypesData,
    isLoading,
    error,
  } = useAgentTypes({
    page: 1,
    pageSize: 100, // Fetch all for client-side filtering
    search: search || undefined,
    strategy: strategyFilter !== 'all' ? strategyFilter : undefined,
  });

  const deleteAgentType = useDeleteAgentType();
  const cloneAgentType = useCloneAgentType();

  const agentTypes = agentTypesData?.agent_types || [];

  // Client-side pagination
  const totalPages = Math.ceil(agentTypes.length / pageSize);
  const paginatedTypes = agentTypes.slice((page - 1) * pageSize, page * pageSize);

  const handleEdit = (id: number) => {
    navigate(`/agent-types/${id}/edit`);
  };

  const handleClone = async (id: number) => {
    try {
      const cloned = await cloneAgentType.mutateAsync({ id });
      navigate(`/agent-types/${cloned.id}/edit`);
    } catch (err) {
      console.error('Failed to clone agent type:', getErrorMessage(err));
    }
  };

  const handleDelete = (id: number) => {
    const agentType = agentTypes.find((t) => t.id === id);
    if (agentType) {
      setTypeToDelete(agentType);
      setDeleteDialogOpen(true);
    }
  };

  const confirmDelete = async () => {
    if (!typeToDelete) return;

    try {
      await deleteAgentType.mutateAsync(typeToDelete.id);
      setDeleteDialogOpen(false);
      setTypeToDelete(null);
    } catch (err) {
      console.error('Failed to delete agent type:', getErrorMessage(err));
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Agent Types</h1>
          <p className="text-muted-foreground">
            Define execution strategies and default configurations for your agents.
          </p>
        </div>
        <Button onClick={() => navigate('/agent-types/new')}>
          <Plus className="mr-2 h-4 w-4" />
          New Type
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search agent types..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="pl-10"
          />
        </div>
        <Select
          value={strategyFilter}
          onValueChange={(value) => {
            setStrategyFilter(value as ExecutionStrategy | 'all');
            setPage(1);
          }}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Strategy" />
          </SelectTrigger>
          <SelectContent>
            {STRATEGY_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {/* View Mode Toggle */}
        <div className="flex items-center gap-1 border rounded-md p-1">
          <Button
            variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => setViewMode('grid')}
          >
            <Grid3X3 className="h-4 w-4" />
          </Button>
          <Button
            variant={viewMode === 'list' ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => setViewMode('list')}
          >
            <List className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{getErrorMessage(error)}</AlertDescription>
        </Alert>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex justify-center py-12">
          <Spinner className="h-8 w-8" />
        </div>
      )}

      {/* Empty State */}
      {!isLoading && paginatedTypes.length === 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5" />
              No agent types found
            </CardTitle>
            <CardDescription>
              {search || strategyFilter !== 'all'
                ? 'Try adjusting your filters.'
                : 'Create a custom agent type to define reusable execution configurations.'}
            </CardDescription>
          </CardHeader>
          {!search && strategyFilter === 'all' && (
            <CardContent>
              <Button onClick={() => navigate('/agent-types/new')}>
                <Plus className="mr-2 h-4 w-4" />
                Create Agent Type
              </Button>
            </CardContent>
          )}
        </Card>
      )}

      {/* Grid View */}
      {!isLoading && paginatedTypes.length > 0 && viewMode === 'grid' && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {paginatedTypes.map((agentType) => (
            <AgentTypeCard
              key={agentType.id}
              agentType={agentType}
              onEdit={handleEdit}
              onClone={handleClone}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      {/* List View */}
      {!isLoading && paginatedTypes.length > 0 && viewMode === 'list' && (
        <div className="space-y-2">
          {paginatedTypes.map((agentType) => (
            <AgentTypeListItem
              key={agentType.id}
              agentType={agentType}
              onEdit={handleEdit}
              onClone={handleClone}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {!isLoading && totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            <ChevronLeft className="h-4 w-4" />
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Agent Type</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{typeToDelete?.name}"? This action cannot be undone.
              Agents using this type will need to be reconfigured.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={confirmDelete}
              disabled={deleteAgentType.isPending}
            >
              {deleteAgentType.isPending ? <Spinner className="h-4 w-4" /> : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
