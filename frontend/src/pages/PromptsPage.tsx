import { useState, useEffect } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
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
  FileText,
  Plus,
  Search,
  Grid3X3,
  List,
  MoreVertical,
  Pencil,
  Trash2,
  ChevronLeft,
  ChevronRight,
  MessageSquare,
  User,
  Bot,
} from 'lucide-react';
import { usePrompts, useDeletePrompt, getErrorMessage } from '@/api/hooks';
import { Prompt, PromptUseCase, MessageType } from '@/api/types';
import { PromptForm } from '@/components/prompts/PromptForm';

const USE_CASES: { value: PromptUseCase; label: string }[] = [
  { value: 'research', label: 'Research' },
  { value: 'coding', label: 'Coding' },
  { value: 'analysis', label: 'Analysis' },
  { value: 'writing', label: 'Writing' },
  { value: 'general', label: 'General' },
  { value: 'custom', label: 'Custom' },
];

const MESSAGE_TYPES: { value: MessageType; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { value: 'system', label: 'System', icon: MessageSquare },
  { value: 'user', label: 'User', icon: User },
  { value: 'assistant', label: 'Assistant', icon: Bot },
];

function getMessageTypeIcon(type: MessageType) {
  const mt = MESSAGE_TYPES.find((m) => m.value === type);
  return mt?.icon || FileText;
}

interface PromptCardProps {
  prompt: Prompt;
  onEdit: (id: number) => void;
  onDelete: (id: number) => void;
}

function PromptCard({ prompt, onEdit, onDelete }: PromptCardProps) {
  const MessageIcon = getMessageTypeIcon(prompt.message_type);

  return (
    <Card className="group hover:border-primary/50 transition-colors">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <MessageIcon className="h-5 w-5 text-primary" />
            <CardTitle className="text-lg">{prompt.name}</CardTitle>
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
              <DropdownMenuItem onClick={() => onEdit(prompt.id)}>
                <Pencil className="mr-2 h-4 w-4" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive"
                onClick={() => onDelete(prompt.id)}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <CardDescription className="line-clamp-2">
          {prompt.description || 'No description'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-2">
          <Badge variant="secondary">{prompt.use_case}</Badge>
          <Badge variant="outline">{prompt.message_type}</Badge>
          {prompt.tags?.slice(0, 2).map((tag) => (
            <Badge key={tag} variant="outline">
              {tag}
            </Badge>
          ))}
          {prompt.tags && prompt.tags.length > 2 && (
            <Badge variant="outline">+{prompt.tags.length - 2}</Badge>
          )}
        </div>
        <div className="mt-3 flex items-center justify-between text-sm text-muted-foreground">
          <span>{prompt.is_active ? 'Active' : 'Inactive'}</span>
          <span>{new Date(prompt.created_at).toLocaleDateString()}</span>
        </div>
      </CardContent>
    </Card>
  );
}

interface PromptListItemProps extends PromptCardProps {}

function PromptListItem({ prompt, onEdit, onDelete }: PromptListItemProps) {
  const MessageIcon = getMessageTypeIcon(prompt.message_type);

  return (
    <div className="group flex items-center gap-4 rounded-lg border p-4 hover:border-primary/50 transition-colors">
      <MessageIcon className="h-8 w-8 text-primary shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold truncate">{prompt.name}</h3>
          <Badge variant="secondary" className="shrink-0">
            {prompt.use_case}
          </Badge>
          <Badge variant="outline" className="shrink-0">
            {prompt.message_type}
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground truncate">
          {prompt.description || 'No description'}
        </p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {prompt.tags?.slice(0, 2).map((tag) => (
          <Badge key={tag} variant="outline">
            {tag}
          </Badge>
        ))}
      </div>
      <div className="flex items-center gap-2 shrink-0 opacity-0 group-hover:opacity-100">
        <Button size="sm" variant="ghost" onClick={() => onEdit(prompt.id)}>
          <Pencil className="h-4 w-4" />
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm">
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              className="text-destructive"
              onClick={() => onDelete(prompt.id)}
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

export function PromptsPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const location = useLocation();

  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [search, setSearch] = useState('');
  const [useCaseFilter, setUseCaseFilter] = useState<string>('all');
  const [page, setPage] = useState(1);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [promptToDelete, setPromptToDelete] = useState<number | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editingPromptId, setEditingPromptId] = useState<number | null>(null);

  const pageSize = 12;

  const { data, isLoading, error } = usePrompts({
    page,
    pageSize,
    search: search || undefined,
    useCase: useCaseFilter !== 'all' ? (useCaseFilter as PromptUseCase) : undefined,
  });

  const deletePrompt = useDeletePrompt();

  // Handle route-based form opening
  useEffect(() => {
    if (location.pathname === '/prompts/new') {
      setEditingPromptId(null);
      setFormOpen(true);
    } else if (id) {
      setEditingPromptId(parseInt(id));
      setFormOpen(true);
    } else {
      setFormOpen(false);
      setEditingPromptId(null);
    }
  }, [location.pathname, id]);

  const handleEdit = (promptId: number) => {
    navigate(`/prompts/${promptId}`);
  };

  const handleDelete = (promptId: number) => {
    setPromptToDelete(promptId);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (promptToDelete) {
      try {
        await deletePrompt.mutateAsync(promptToDelete);
        setDeleteDialogOpen(false);
        setPromptToDelete(null);
      } catch (err) {
        console.error('Failed to delete prompt:', getErrorMessage(err));
      }
    }
  };

  const handleFormClose = () => {
    setFormOpen(false);
    setEditingPromptId(null);
    navigate('/prompts');
  };

  const handleFormSuccess = () => {
    handleFormClose();
  };

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;
  const prompts = data?.prompts || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Prompts</h1>
          <p className="text-muted-foreground">
            Manage reusable prompt templates.
          </p>
        </div>
        <Button onClick={() => navigate('/prompts/new')}>
          <Plus className="mr-2 h-4 w-4" />
          New Prompt
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search prompts..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="pl-10"
          />
        </div>
        <Select
          value={useCaseFilter}
          onValueChange={(value) => {
            setUseCaseFilter(value);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Use Case" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Use Cases</SelectItem>
            {USE_CASES.map((uc) => (
              <SelectItem key={uc.value} value={uc.value}>
                {uc.label}
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
      {!isLoading && prompts.length === 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              No prompts yet
            </CardTitle>
            <CardDescription>
              Create your first prompt template.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Prompts are reusable templates that guide agent behavior. Create
              system prompts, user templates, and more with variable support.
            </p>
            <Button onClick={() => navigate('/prompts/new')}>
              <Plus className="mr-2 h-4 w-4" />
              Create Prompt
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Prompt Grid */}
      {!isLoading && prompts.length > 0 && viewMode === 'grid' && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {prompts.map((prompt) => (
            <PromptCard
              key={prompt.id}
              prompt={prompt}
              onEdit={handleEdit}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      {/* Prompt List */}
      {!isLoading && prompts.length > 0 && viewMode === 'list' && (
        <div className="space-y-2">
          {prompts.map((prompt) => (
            <PromptListItem
              key={prompt.id}
              prompt={prompt}
              onEdit={handleEdit}
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
            <DialogTitle>Delete Prompt</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this prompt? This action cannot be
              undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={confirmDelete}
              disabled={deletePrompt.isPending}
            >
              {deletePrompt.isPending ? <Spinner className="h-4 w-4" /> : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create/Edit Form Dialog */}
      <PromptForm
        open={formOpen}
        onClose={handleFormClose}
        onSuccess={handleFormSuccess}
        promptId={editingPromptId}
      />
    </div>
  );
}
