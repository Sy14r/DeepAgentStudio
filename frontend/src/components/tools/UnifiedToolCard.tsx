import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Badge,
  Button,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui';
import {
  MoreVertical,
  Pencil,
  Trash2,
  Code,
  Plug2,
  Cog,
  Globe,
  Folder,
  Database,
  Search as SearchIcon,
} from 'lucide-react';
import { Tool, MCPServer, ToolCategory } from '@/api/types';

// Type colors for visual distinction
const TOOL_TYPE_COLORS = {
  python: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  mcp: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
  builtin: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400',
};

const TRANSPORT_COLORS = {
  stdio: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  sse: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  streamable_http: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-400',
};

// Category icons for Python tools
const CATEGORY_ICONS: Record<ToolCategory, React.ComponentType<{ className?: string }>> = {
  search: SearchIcon,
  calculator: Code,
  filesystem: Folder,
  api: Globe,
  database: Database,
  retrieval: Globe,
  python: Code,
  other: Cog,
};

// Union type for unified items
export type UnifiedToolItem =
  | { type: 'tool'; data: Tool }
  | { type: 'mcp'; data: MCPServer };

interface UnifiedToolCardProps {
  item: UnifiedToolItem;
  onEdit: (item: UnifiedToolItem) => void;
  onDelete: (item: UnifiedToolItem) => void;
}

export function UnifiedToolCard({ item, onEdit, onDelete }: UnifiedToolCardProps) {
  const isMCP = item.type === 'mcp';
  const data = item.data;

  // Determine icon based on type
  let Icon: React.ComponentType<{ className?: string }>;
  if (isMCP) {
    Icon = Plug2;
  } else {
    const tool = data as Tool;
    Icon = tool.tool_type === 'builtin'
      ? Cog
      : CATEGORY_ICONS[tool.category] || Code;
  }

  // Get name and description
  const name = data.name;
  const description = data.description || (isMCP ? 'MCP Server' : 'No description');

  // Determine if deletable
  const canDelete = isMCP || (data as Tool).tool_type !== 'builtin';

  return (
    <Card className="group hover:border-primary/50 transition-colors">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <Icon className={`h-5 w-5 ${isMCP ? 'text-purple-600 dark:text-purple-400' : 'text-primary'}`} />
            <CardTitle className="text-lg">{name}</CardTitle>
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
              <DropdownMenuItem onClick={() => onEdit(item)}>
                <Pencil className="mr-2 h-4 w-4" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive"
                onClick={() => onDelete(item)}
                disabled={!canDelete}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <CardDescription className="line-clamp-2">
          {description}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-2">
          {/* Type badge */}
          {isMCP ? (
            <>
              <Badge className={TOOL_TYPE_COLORS.mcp}>MCP</Badge>
              <Badge className={TRANSPORT_COLORS[(data as MCPServer).transport_type]}>
                {(data as MCPServer).transport_type}
              </Badge>
              {(data as MCPServer).cached_tools_count > 0 && (
                <Badge variant="outline">
                  {(data as MCPServer).cached_tools_count} tools
                </Badge>
              )}
            </>
          ) : (
            <>
              <Badge className={
                (data as Tool).tool_type === 'builtin'
                  ? TOOL_TYPE_COLORS.builtin
                  : TOOL_TYPE_COLORS.python
              }>
                {(data as Tool).tool_type === 'builtin' ? 'Builtin' : 'Python'}
              </Badge>
              <Badge variant="secondary">{(data as Tool).category}</Badge>
            </>
          )}
        </div>
        <div className="mt-3 flex items-center justify-between text-sm text-muted-foreground">
          <span>{data.is_active ? 'Active' : 'Inactive'}</span>
          <span>{new Date(data.created_at).toLocaleDateString()}</span>
        </div>
      </CardContent>
    </Card>
  );
}

// List item variant
interface UnifiedToolListItemProps extends UnifiedToolCardProps {}

export function UnifiedToolListItem({ item, onEdit, onDelete }: UnifiedToolListItemProps) {
  const isMCP = item.type === 'mcp';
  const data = item.data;

  // Determine icon based on type
  let Icon: React.ComponentType<{ className?: string }>;
  if (isMCP) {
    Icon = Plug2;
  } else {
    const tool = data as Tool;
    Icon = tool.tool_type === 'builtin'
      ? Cog
      : CATEGORY_ICONS[tool.category] || Code;
  }

  // Get name and description
  const name = data.name;
  const description = data.description || (isMCP ? 'MCP Server' : 'No description');

  // Determine if deletable
  const canDelete = isMCP || (data as Tool).tool_type !== 'builtin';

  return (
    <div className="group flex items-center gap-4 rounded-lg border p-4 hover:border-primary/50 transition-colors">
      <Icon className={`h-8 w-8 shrink-0 ${isMCP ? 'text-purple-600 dark:text-purple-400' : 'text-primary'}`} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <h3 className="font-semibold truncate">{name}</h3>
          {/* Type badge */}
          {isMCP ? (
            <>
              <Badge className={`${TOOL_TYPE_COLORS.mcp} shrink-0`}>MCP</Badge>
              <Badge className={`${TRANSPORT_COLORS[(data as MCPServer).transport_type]} shrink-0`}>
                {(data as MCPServer).transport_type}
              </Badge>
              {(data as MCPServer).cached_tools_count > 0 && (
                <Badge variant="outline" className="shrink-0">
                  {(data as MCPServer).cached_tools_count} tools
                </Badge>
              )}
            </>
          ) : (
            <>
              <Badge className={`shrink-0 ${
                (data as Tool).tool_type === 'builtin'
                  ? TOOL_TYPE_COLORS.builtin
                  : TOOL_TYPE_COLORS.python
              }`}>
                {(data as Tool).tool_type === 'builtin' ? 'Builtin' : 'Python'}
              </Badge>
              <Badge variant="secondary" className="shrink-0">
                {(data as Tool).category}
              </Badge>
            </>
          )}
        </div>
        <p className="text-sm text-muted-foreground truncate">
          {description}
        </p>
      </div>
      <div className="flex items-center gap-2 shrink-0 opacity-0 group-hover:opacity-100">
        <Button size="sm" variant="ghost" onClick={() => onEdit(item)}>
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
              onClick={() => onDelete(item)}
              disabled={!canDelete}
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
