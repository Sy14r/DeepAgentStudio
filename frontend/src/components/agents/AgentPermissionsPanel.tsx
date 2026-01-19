/**
 * AgentPermissionsPanel - MCP permission management for agents
 *
 * Allows users to configure what MCP tools an agent can access when
 * connecting via the MCP server.
 */
import { useState, useEffect } from 'react';
import { Eye, Sparkles, Wrench, Crown, Settings, Shield, Check, Info, Loader2 } from 'lucide-react';
import { useAgentPermissions, useUpdateAgentPermissions } from '@/api/hooks/useAgents';
import { PermissionPreset, PERMISSION_PRESET_INFO } from '@/api/types';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Alert,
  AlertDescription,
} from '@/components/ui/alert';
import { ChevronDown, ChevronRight } from 'lucide-react';

interface AgentPermissionsPanelProps {
  agentId: number;
  isBuiltin?: boolean;
}

// Icon mapping for presets
const PRESET_ICONS: Record<PermissionPreset, React.ReactNode> = {
  observer: <Eye className="h-5 w-5" />,
  self_improve: <Sparkles className="h-5 w-5" />,
  tool_creator: <Wrench className="h-5 w-5" />,
  meta_agent: <Crown className="h-5 w-5" />,
  custom: <Settings className="h-5 w-5" />,
};

// Available permissions for custom selection
const AVAILABLE_PERMISSIONS = [
  { group: 'Agents', permissions: [
    { value: 'agents:list', label: 'List agents' },
    { value: 'agents:read', label: 'Read agent details' },
    { value: 'agents:create', label: 'Create new agents' },
    { value: 'agents:update:self', label: 'Update own configuration' },
    { value: 'agents:update:*', label: 'Update any agent' },
    { value: 'agents:delete', label: 'Delete agents' },
    { value: 'agents:*', label: 'Full agent access' },
  ]},
  { group: 'Tools', permissions: [
    { value: 'tools:list', label: 'List tools' },
    { value: 'tools:read', label: 'Read tool details' },
    { value: 'tools:create', label: 'Create tools' },
    { value: 'tools:update:own', label: 'Update own tools' },
    { value: 'tools:delete', label: 'Delete tools' },
    { value: 'tools:*', label: 'Full tool access' },
  ]},
  { group: 'Prompts', permissions: [
    { value: 'prompts:list', label: 'List prompts' },
    { value: 'prompts:read', label: 'Read prompts' },
    { value: 'prompts:create', label: 'Create prompts' },
    { value: 'prompts:update:own', label: 'Update own prompts' },
    { value: 'prompts:*', label: 'Full prompt access' },
  ]},
  { group: 'Datasets', permissions: [
    { value: 'datasets:list', label: 'List datasets' },
    { value: 'datasets:read', label: 'Read datasets' },
    { value: 'datasets:create', label: 'Create datasets' },
    { value: 'datasets:update:examples', label: 'Add/update examples' },
    { value: 'datasets:*', label: 'Full dataset access' },
  ]},
  { group: 'Evaluations', permissions: [
    { value: 'evaluations:list', label: 'List evaluations' },
    { value: 'evaluations:read', label: 'Read evaluation results' },
    { value: 'evaluations:run', label: 'Run evaluations' },
    { value: 'evaluations:*', label: 'Full evaluation access' },
  ]},
  { group: 'Sessions', permissions: [
    { value: 'sessions:read:own', label: 'Read own session' },
    { value: 'sessions:list', label: 'List sessions' },
  ]},
];

export function AgentPermissionsPanel({ agentId, isBuiltin = false }: AgentPermissionsPanelProps) {
  const { data: permissions, isLoading, error } = useAgentPermissions(agentId);
  const updatePermissions = useUpdateAgentPermissions(agentId);

  const [selectedPreset, setSelectedPreset] = useState<PermissionPreset>('observer');
  const [customPermissions, setCustomPermissions] = useState<string[]>([]);
  const [showCustomPermissions, setShowCustomPermissions] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  // Sync state with loaded data
  useEffect(() => {
    if (permissions) {
      setSelectedPreset(permissions.preset as PermissionPreset);
      setCustomPermissions(permissions.custom_permissions || []);
      setShowCustomPermissions(permissions.preset === 'custom');
    }
  }, [permissions]);

  // Track changes
  useEffect(() => {
    if (!permissions) return;

    const presetChanged = selectedPreset !== permissions.preset;
    const customChanged = selectedPreset === 'custom' &&
      JSON.stringify(customPermissions.sort()) !== JSON.stringify((permissions.custom_permissions || []).sort());

    setHasChanges(presetChanged || customChanged);
  }, [selectedPreset, customPermissions, permissions]);

  const handlePresetSelect = (preset: PermissionPreset) => {
    setSelectedPreset(preset);
    setShowCustomPermissions(preset === 'custom');
    if (preset !== 'custom') {
      setCustomPermissions([]);
    }
  };

  const handlePermissionToggle = (permission: string) => {
    setCustomPermissions(prev =>
      prev.includes(permission)
        ? prev.filter(p => p !== permission)
        : [...prev, permission]
    );
  };

  const handleSave = async () => {
    try {
      await updatePermissions.mutateAsync({
        preset: selectedPreset,
        custom_permissions: selectedPreset === 'custom' ? customPermissions : undefined,
      });
    } catch (err) {
      console.error('Failed to update permissions:', err);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          Failed to load permissions. Please try again.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-medium flex items-center gap-2">
            <Shield className="h-5 w-5" />
            MCP Permissions
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            Control what this agent can do when connected via MCP.
          </p>
        </div>
        {hasChanges && !isBuiltin && (
          <Button
            onClick={handleSave}
            disabled={updatePermissions.isPending}
            size="sm"
          >
            {updatePermissions.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : null}
            Save Changes
          </Button>
        )}
      </div>

      {isBuiltin && (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            Built-in agents have fixed permissions. Clone this agent to customize its permissions.
          </AlertDescription>
        </Alert>
      )}

      {/* Preset Selection */}
      <div className="grid gap-3">
        {(Object.keys(PERMISSION_PRESET_INFO) as PermissionPreset[]).map((preset) => {
          const info = PERMISSION_PRESET_INFO[preset];
          const isSelected = selectedPreset === preset;

          return (
            <button
              key={preset}
              onClick={() => !isBuiltin && handlePresetSelect(preset)}
              disabled={isBuiltin}
              className={cn(
                'flex items-start gap-4 p-4 rounded-lg border text-left transition-colors',
                isSelected
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-muted-foreground/50',
                isBuiltin && 'opacity-60 cursor-not-allowed'
              )}
            >
              <div className={cn(
                'p-2 rounded-md',
                isSelected ? 'bg-primary text-primary-foreground' : 'bg-muted'
              )}>
                {PRESET_ICONS[preset]}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{info.label}</span>
                  {isSelected && (
                    <Badge variant="secondary" className="text-xs">
                      <Check className="h-3 w-3 mr-1" />
                      Active
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground mt-1">
                  {info.description}
                </p>
              </div>
            </button>
          );
        })}
      </div>

      {/* Custom Permissions */}
      {selectedPreset === 'custom' && !isBuiltin && (
        <div>
          <Button
            variant="outline"
            className="w-full justify-between"
            onClick={() => setShowCustomPermissions(!showCustomPermissions)}
          >
            <span className="flex items-center gap-2">
              {showCustomPermissions ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              Configure Custom Permissions
            </span>
            <Badge variant="secondary">{customPermissions.length} selected</Badge>
          </Button>
          {showCustomPermissions && (
            <div className="border rounded-lg p-4 space-y-6 mt-4">
              {AVAILABLE_PERMISSIONS.map((group) => (
                <div key={group.group}>
                  <h4 className="font-medium text-sm mb-3">{group.group}</h4>
                  <div className="grid gap-2">
                    {group.permissions.map((perm) => (
                      <div key={perm.value} className="flex items-center space-x-2">
                        <Checkbox
                          id={perm.value}
                          checked={customPermissions.includes(perm.value)}
                          onCheckedChange={() => handlePermissionToggle(perm.value)}
                        />
                        <Label
                          htmlFor={perm.value}
                          className="text-sm cursor-pointer flex-1"
                        >
                          {perm.label}
                          <code className="ml-2 text-xs text-muted-foreground">
                            {perm.value}
                          </code>
                        </Label>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Effective Permissions Display */}
      {permissions && (
        <div className="mt-6 pt-6 border-t">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <h4 className="text-sm font-medium flex items-center gap-2 cursor-help">
                  Effective Permissions
                  <Info className="h-3.5 w-3.5 text-muted-foreground" />
                </h4>
              </TooltipTrigger>
              <TooltipContent>
                <p>These are the actual permissions this agent will have when connecting via MCP.</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
          <div className="flex flex-wrap gap-1.5 mt-3">
            {permissions.effective_permissions.map((perm) => (
              <Badge key={perm} variant="outline" className="text-xs font-mono">
                {perm}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* MCP Connection Info */}
      <div className="mt-6 pt-6 border-t">
        <h4 className="text-sm font-medium mb-2">MCP Connection</h4>
        <p className="text-sm text-muted-foreground mb-3">
          Connect to this agent via MCP using the following endpoint:
        </p>
        <code className="block p-3 bg-muted rounded-md text-xs font-mono break-all">
          {window.location.origin}/api/v1/mcp/sse?agent_id={agentId}
        </code>
      </div>
    </div>
  );
}
