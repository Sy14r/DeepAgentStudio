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
  Badge,
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
  Spinner,
  Alert,
  AlertDescription,
} from '@/components/ui';
import {
  Bot,
  Plus,
  Search,
  Grid3X3,
  List,
  MoreVertical,
  Pencil,
  Copy,
  Trash2,
  Play,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { useAgents, useDeleteAgent, useCloneAgent, getErrorMessage } from '@/api/hooks';
import { Agent, AgentType } from '@/api/types';

const AGENT_TYPES: AgentType[] = ['ReAct', 'Plan-and-Execute', 'Conversational', 'Custom'];

interface AgentCardProps {
  agent: Agent;
  onEdit: (id: number) => void;
  onClone: (id: number) => void;
  onDelete: (id: number) => void;
  onPlayground: (id: number) => void;
}

function AgentCard({ agent, onEdit, onClone, onDelete, onPlayground }: AgentCardProps) {
  return (
    <Card className="group hover:border-primary/50 transition-colors">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-primary" />
            <CardTitle className="text-lg">{agent.name}</CardTitle>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100"
              >
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => onEdit(agent.id)}>
                <Pencil className="mr-2 h-4 w-4" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onClone(agent.id)}>
                <Copy className="mr-2 h-4 w-4" />
                Clone
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onPlayground(agent.id)}>
                <Play className="mr-2 h-4 w-4" />
                Open in Playground
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive"
                onClick={() => onDelete(agent.id)}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <CardDescription className="line-clamp-2">
          {agent.description || 'No description'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-2">
          <Badge variant="secondary">{agent.agent_type}</Badge>
          {agent.tags?.slice(0, 3).map((tag) => (
            <Badge key={tag} variant="outline">
              {tag}
            </Badge>
          ))}
          {agent.tags && agent.tags.length > 3 && (
            <Badge variant="outline">+{agent.tags.length - 3}</Badge>
          )}
        </div>
        <div className="mt-3 flex items-center justify-between text-sm text-muted-foreground">
          <span>{agent.is_active ? 'Active' : 'Inactive'}</span>
          <span>
            {new Date(agent.created_at).toLocaleDateString()}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

interface AgentListItemProps extends AgentCardProps {}

function AgentListItem({ agent, onEdit, onClone, onDelete, onPlayground }: AgentListItemProps) {
  return (
    <div className="group flex items-center gap-4 rounded-lg border p-4 hover:border-primary/50 transition-colors">
      <Bot className="h-8 w-8 text-primary shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold truncate">{agent.name}</h3>
          <Badge variant="secondary" className="shrink-0">
            {agent.agent_type}
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground truncate">
          {agent.description || 'No description'}
        </p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {agent.tags?.slice(0, 2).map((tag) => (
          <Badge key={tag} variant="outline">
            {tag}
          </Badge>
        ))}
      </div>
      <div className="flex items-center gap-2 shrink-0 opacity-0 group-hover:opacity-100">
        <Button size="sm" variant="ghost" onClick={() => onPlayground(agent.id)}>
          <Play className="h-4 w-4" />
        </Button>
        <Button size="sm" variant="ghost" onClick={() => onEdit(agent.id)}>
          <Pencil className="h-4 w-4" />
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm">
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => onClone(agent.id)}>
              <Copy className="mr-2 h-4 w-4" />
              Clone
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-destructive"
              onClick={() => onDelete(agent.id)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}

export function AgentsPage() {
  const navigate = useNavigate();

  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [search, setSearch] = useState('');
  const [agentTypeFilter, setAgentTypeFilter] = useState<string>('all');
  const [page, setPage] = useState(1);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [agentToDelete, setAgentToDelete] = useState<number | null>(null);

  const pageSize = 12;

  const { data, isLoading, error } = useAgents({
    page,
    pageSize,
    search: search || undefined,
    agentType: agentTypeFilter !== 'all' ? (agentTypeFilter as AgentType) : undefined,
  });

  const deleteAgent = useDeleteAgent();
  const cloneAgent = useCloneAgent();

  const handleEdit = (agentId: number) => {
    navigate(`/agents/${agentId}/edit`);
  };

  const handleClone = async (agentId: number) => {
    try {
      await cloneAgent.mutateAsync(agentId);
    } catch (err) {
      console.error('Failed to clone agent:', getErrorMessage(err));
    }
  };

  const handleDelete = (agentId: number) => {
    setAgentToDelete(agentId);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (agentToDelete) {
      try {
        await deleteAgent.mutateAsync(agentToDelete);
        setDeleteDialogOpen(false);
        setAgentToDelete(null);
      } catch (err) {
        console.error('Failed to delete agent:', getErrorMessage(err));
      }
    }
  };

  const handlePlayground = (agentId: number) => {
    navigate(`/playground/${agentId}`);
  };

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;
  const agents = data?.agents || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Agents</h1>
          <p className="text-muted-foreground">
            Create and manage your AI agents.
          </p>
        </div>
        <Button onClick={() => navigate('/agents/new')}>
          <Plus className="mr-2 h-4 w-4" />
          New Agent
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search agents..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="pl-10"
          />
        </div>
        <Select
          value={agentTypeFilter}
          onValueChange={(value) => {
            setAgentTypeFilter(value);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Agent Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            {AGENT_TYPES.map((type) => (
              <SelectItem key={type} value={type}>
                {type}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
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
      {!isLoading && agents.length === 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bot className="h-5 w-5" />
              No agents yet
            </CardTitle>
            <CardDescription>
              Create your first agent to get started.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Agents are AI assistants that can use tools to accomplish tasks.
              Create agents with different configurations for various use cases.
            </p>
            <Button onClick={() => navigate('/agents/new')}>
              <Plus className="mr-2 h-4 w-4" />
              Create Agent
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Agent Grid */}
      {!isLoading && agents.length > 0 && viewMode === 'grid' && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              onEdit={handleEdit}
              onClone={handleClone}
              onDelete={handleDelete}
              onPlayground={handlePlayground}
            />
          ))}
        </div>
      )}

      {/* Agent List */}
      {!isLoading && agents.length > 0 && viewMode === 'list' && (
        <div className="space-y-2">
          {agents.map((agent) => (
            <AgentListItem
              key={agent.id}
              agent={agent}
              onEdit={handleEdit}
              onClone={handleClone}
              onDelete={handleDelete}
              onPlayground={handlePlayground}
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
            <DialogTitle>Delete Agent</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this agent? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={confirmDelete}
              disabled={deleteAgent.isPending}
            >
              {deleteAgent.isPending ? <Spinner className="h-4 w-4" /> : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
