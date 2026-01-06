import { useState, useMemo } from 'react';
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
  DropdownMenuTrigger,
  Spinner,
  Alert,
  AlertDescription,
} from '@/components/ui';
import {
  Wrench,
  Plus,
  Search,
  Grid3X3,
  List,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Code,
  Plug2,
} from 'lucide-react';
import { useTools, useMCPServers, useDeleteTool, useDeleteMCPServer, getErrorMessage } from '@/api/hooks';
import { ToolCategory } from '@/api/types';
import { UnifiedToolCard, UnifiedToolListItem, UnifiedToolItem } from '@/components/tools/UnifiedToolCard';

// Type filter options
type TypeFilter = 'all' | 'python' | 'mcp';

const TYPE_OPTIONS: { value: TypeFilter; label: string }[] = [
  { value: 'all', label: 'All Types' },
  { value: 'python', label: 'Python Tools' },
  { value: 'mcp', label: 'MCP Servers' },
];

const TOOL_CATEGORIES: { value: ToolCategory; label: string }[] = [
  { value: 'search', label: 'Search' },
  { value: 'calculator', label: 'Calculator' },
  { value: 'filesystem', label: 'Filesystem' },
  { value: 'api', label: 'API' },
  { value: 'database', label: 'Database' },
  { value: 'retrieval', label: 'Retrieval' },
  { value: 'python', label: 'Python' },
  { value: 'other', label: 'Other' },
];

export function ToolsPage() {
  const navigate = useNavigate();

  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [page, setPage] = useState(1);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [itemToDelete, setItemToDelete] = useState<UnifiedToolItem | null>(null);

  const pageSize = 12;

  // Fetch Python tools
  const {
    data: toolsData,
    isLoading: isLoadingTools,
    error: toolsError,
  } = useTools({
    page: 1,
    pageSize: 100, // Fetch all for client-side filtering
    search: search || undefined,
    category: categoryFilter !== 'all' ? (categoryFilter as ToolCategory) : undefined,
  });

  // Fetch MCP servers
  const {
    data: mcpData,
    isLoading: isLoadingMCP,
    error: mcpError,
  } = useMCPServers();

  const deleteTool = useDeleteTool();
  const deleteMCPServer = useDeleteMCPServer();

  // Combine and filter items
  const unifiedItems = useMemo(() => {
    const items: UnifiedToolItem[] = [];

    // Add Python tools
    if (typeFilter === 'all' || typeFilter === 'python') {
      const tools = toolsData?.tools || [];
      tools.forEach((tool) => {
        items.push({ type: 'tool', data: tool });
      });
    }

    // Add MCP servers
    if (typeFilter === 'all' || typeFilter === 'mcp') {
      const servers = mcpData?.servers || [];
      servers.forEach((server) => {
        // Apply search filter to MCP servers
        if (search) {
          const searchLower = search.toLowerCase();
          if (
            !server.name.toLowerCase().includes(searchLower) &&
            !(server.description || '').toLowerCase().includes(searchLower)
          ) {
            return;
          }
        }
        items.push({ type: 'mcp', data: server });
      });
    }

    // Sort by created_at descending
    items.sort((a, b) => {
      const dateA = new Date(a.data.created_at).getTime();
      const dateB = new Date(b.data.created_at).getTime();
      return dateB - dateA;
    });

    return items;
  }, [toolsData, mcpData, typeFilter, search]);

  // Paginate
  const totalPages = Math.ceil(unifiedItems.length / pageSize);
  const paginatedItems = unifiedItems.slice((page - 1) * pageSize, page * pageSize);

  const isLoading = isLoadingTools || isLoadingMCP;
  const error = toolsError || mcpError;

  const handleEdit = (item: UnifiedToolItem) => {
    if (item.type === 'tool') {
      navigate(`/tools/${item.data.id}/edit`);
    } else {
      navigate(`/tools/mcp/${item.data.id}/edit`);
    }
  };

  const handleDelete = (item: UnifiedToolItem) => {
    setItemToDelete(item);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!itemToDelete) return;

    try {
      if (itemToDelete.type === 'tool') {
        await deleteTool.mutateAsync(itemToDelete.data.id);
      } else {
        await deleteMCPServer.mutateAsync(itemToDelete.data.id);
      }
      setDeleteDialogOpen(false);
      setItemToDelete(null);
    } catch (err) {
      console.error('Failed to delete:', getErrorMessage(err));
    }
  };

  const isDeleting = deleteTool.isPending || deleteMCPServer.isPending;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Tools</h1>
          <p className="text-muted-foreground">
            Manage Python tools and MCP servers for your agents.
          </p>
        </div>
        {/* New Tool Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              New Tool
              <ChevronDown className="ml-2 h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => navigate('/tools/new')}>
              <Code className="mr-2 h-4 w-4" />
              Python Tool
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => navigate('/tools/mcp/new')}>
              <Plug2 className="mr-2 h-4 w-4" />
              MCP Server
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search tools..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="pl-10"
          />
        </div>
        {/* Type Filter */}
        <Select
          value={typeFilter}
          onValueChange={(value) => {
            setTypeFilter(value as TypeFilter);
            setPage(1);
            // Reset category filter when switching to MCP
            if (value === 'mcp') {
              setCategoryFilter('all');
            }
          }}
        >
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent>
            {TYPE_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {/* Category Filter - only show for Python tools */}
        {typeFilter !== 'mcp' && (
          <Select
            value={categoryFilter}
            onValueChange={(value) => {
              setCategoryFilter(value);
              setPage(1);
            }}
          >
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="Category" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              {TOOL_CATEGORIES.map((cat) => (
                <SelectItem key={cat.value} value={cat.value}>
                  {cat.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
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
      {!isLoading && paginatedItems.length === 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wrench className="h-5 w-5" />
              {typeFilter === 'mcp' ? 'No MCP servers yet' : typeFilter === 'python' ? 'No Python tools yet' : 'No tools yet'}
            </CardTitle>
            <CardDescription>
              {typeFilter === 'mcp'
                ? 'Connect to MCP servers for additional tools like filesystem access, git operations, and more.'
                : typeFilter === 'python'
                  ? 'Create custom Python tools to extend what agents can do.'
                  : 'Create Python tools or connect MCP servers for your agents.'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              {typeFilter !== 'mcp' && (
                <Button onClick={() => navigate('/tools/new')}>
                  <Code className="mr-2 h-4 w-4" />
                  Create Python Tool
                </Button>
              )}
              {typeFilter !== 'python' && (
                <Button variant={typeFilter === 'mcp' ? 'default' : 'outline'} onClick={() => navigate('/tools/mcp/new')}>
                  <Plug2 className="mr-2 h-4 w-4" />
                  Add MCP Server
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Grid View */}
      {!isLoading && paginatedItems.length > 0 && viewMode === 'grid' && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {paginatedItems.map((item) => (
            <UnifiedToolCard
              key={`${item.type}-${item.data.id}`}
              item={item}
              onEdit={handleEdit}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      {/* List View */}
      {!isLoading && paginatedItems.length > 0 && viewMode === 'list' && (
        <div className="space-y-2">
          {paginatedItems.map((item) => (
            <UnifiedToolListItem
              key={`${item.type}-${item.data.id}`}
              item={item}
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
            <DialogTitle>
              Delete {itemToDelete?.type === 'mcp' ? 'MCP Server' : 'Tool'}
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{itemToDelete?.data.name}"? This action cannot be
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
              disabled={isDeleting}
            >
              {isDeleting ? <Spinner className="h-4 w-4" /> : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
