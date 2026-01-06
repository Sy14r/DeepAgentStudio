import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Button,
  Input,
  Textarea,
  Badge,
  Spinner,
  Alert,
  AlertDescription,
  RadioGroup,
  RadioGroupItem,
  Label,
  ScrollArea,
} from '@/components/ui';
import {
  Save,
  X,
  Plug2,
  AlertCircle,
  CheckCircle,
  Terminal,
  Globe,
  TestTube2,
  Wrench,
} from 'lucide-react';
import {
  useMCPServer,
  useCreateMCPServer,
  useUpdateMCPServer,
  useTestMCPServer,
  getErrorMessage,
} from '@/api/hooks';
import { MCPTransportType, MCPServerTestResponse } from '@/api/types';

export function MCPServerEditorPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const isEditing = id !== undefined && id !== 'new';
  const serverId = isEditing ? parseInt(id) : null;

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [transportType, setTransportType] = useState<MCPTransportType>('stdio');
  const [command, setCommand] = useState('');
  const [args, setArgs] = useState('');
  const [url, setUrl] = useState('');
  const [headers, setHeaders] = useState('');
  const [envVars, setEnvVars] = useState('');

  // Editor state
  const [error, setError] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Test state
  const [testResult, setTestResult] = useState<MCPServerTestResponse | null>(null);
  const [isTesting, setIsTesting] = useState(false);

  // Data hooks
  const { data: server, isLoading: isLoadingServer } = useMCPServer(serverId ?? undefined);
  const createMutation = useCreateMCPServer();
  const updateMutation = useUpdateMCPServer(serverId ?? 0);
  const testMutation = useTestMCPServer(serverId ?? 0);

  // Initialize with server data
  useEffect(() => {
    if (isEditing && server) {
      setName(server.name);
      setDescription(server.description || '');
      setTransportType(server.transport_type);
      setCommand(server.stdio_config?.command || '');
      setArgs(server.stdio_config?.args?.join(' ') || '');
      setUrl(server.http_config?.url || '');
      setHeaders(
        server.http_config?.headers
          ? JSON.stringify(server.http_config.headers, null, 2)
          : ''
      );
      setEnvVars(''); // Never prefill env vars for security
      setHasUnsavedChanges(false);
    } else if (!isEditing) {
      setName('');
      setDescription('');
      setTransportType('stdio');
      setCommand('');
      setArgs('');
      setUrl('');
      setHeaders('');
      setEnvVars('');
      setHasUnsavedChanges(false);
    }
  }, [isEditing, server]);

  // Track unsaved changes
  useEffect(() => {
    if (!isLoadingServer) {
      setHasUnsavedChanges(true);
    }
  }, [name, description, transportType, command, args, url, headers, envVars]);

  const handleSave = async () => {
    setError(null);

    // Validate
    if (!name.trim()) {
      setError('Server name is required');
      return;
    }

    if (transportType === 'stdio' && !command.trim()) {
      setError('Command is required for stdio transport');
      return;
    }

    if ((transportType === 'sse' || transportType === 'streamable_http') && !url.trim()) {
      setError('URL is required for HTTP transport');
      return;
    }

    // Parse headers JSON if provided
    let parsedHeaders: Record<string, string> | undefined;
    if (headers.trim()) {
      try {
        parsedHeaders = JSON.parse(headers);
      } catch {
        setError('Invalid JSON in headers');
        return;
      }
    }

    // Parse env vars JSON if provided
    let parsedEnvVars: Record<string, string> | undefined;
    if (envVars.trim()) {
      try {
        parsedEnvVars = JSON.parse(envVars);
      } catch {
        setError('Invalid JSON in environment variables');
        return;
      }
    }

    // Build request data
    const requestData = {
      name: name.trim(),
      description: description.trim() || undefined,
      transport_type: transportType,
      stdio_config:
        transportType === 'stdio'
          ? {
              command: command.trim(),
              args: args.trim() ? args.trim().split(/\s+/) : [],
            }
          : undefined,
      http_config:
        transportType !== 'stdio'
          ? {
              url: url.trim(),
              headers: parsedHeaders,
            }
          : undefined,
      env_vars: parsedEnvVars,
    };

    try {
      if (isEditing && serverId) {
        await updateMutation.mutateAsync(requestData);
      } else {
        const created = await createMutation.mutateAsync(requestData);
        // Navigate to edit page for newly created server
        navigate(`/tools/mcp/${created.id}/edit`, { replace: true });
      }
      setHasUnsavedChanges(false);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const handleCancel = () => {
    navigate('/tools');
  };

  const handleTest = async () => {
    if (!serverId) {
      setError('Please save the server configuration first to test the connection');
      return;
    }

    setIsTesting(true);
    setTestResult(null);

    try {
      const result = await testMutation.mutateAsync();
      setTestResult(result);
    } catch (err) {
      setTestResult({
        success: false,
        message: getErrorMessage(err),
        tools_count: 0,
        latency_ms: null,
        tools: [],
      });
    } finally {
      setIsTesting(false);
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  if (isLoadingServer && isEditing) {
    return (
      <div className="h-[calc(100vh-8rem)] flex items-center justify-center">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <Plug2 className="h-6 w-6 text-purple-600 dark:text-purple-400" />
          <div>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              {name || 'New MCP Server'}
              {hasUnsavedChanges && (
                <Badge variant="outline" className="text-yellow-600">
                  Unsaved
                </Badge>
              )}
            </h1>
            <p className="text-sm text-muted-foreground">
              {isEditing ? 'Edit MCP server configuration' : 'Add a new MCP server'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleCancel}>
            <X className="mr-2 h-4 w-4" />
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={isPending}>
            {isPending ? (
              <Spinner className="mr-2 h-4 w-4" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            {isEditing ? 'Save' : 'Create'}
          </Button>
        </div>
      </div>

      {/* Error alerts */}
      {error && (
        <Alert variant="destructive" className="shrink-0">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Main content - split view */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 min-h-0">
        {/* Left side - Connection Configuration (2/3 width) */}
        <div className="lg:col-span-2 flex flex-col min-h-0 border rounded-lg overflow-hidden">
          {/* Header */}
          <div className="flex items-center gap-2 px-4 py-2 border-b bg-muted/30 shrink-0">
            <Terminal className="h-4 w-4" />
            <span className="text-sm font-medium">Connection Configuration</span>
          </div>

          {/* Content */}
          <ScrollArea className="flex-1">
            <div className="p-4 space-y-6">
              {/* Transport Type */}
              <div className="space-y-3">
                <Label className="text-sm font-medium">Transport Type</Label>
                <RadioGroup
                  value={transportType}
                  onValueChange={(value) => setTransportType(value as MCPTransportType)}
                  className="flex gap-4"
                >
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="stdio" id="stdio" />
                    <Label htmlFor="stdio" className="font-normal flex items-center gap-2">
                      <Terminal className="h-4 w-4" />
                      Stdio (Local subprocess)
                    </Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="sse" id="sse" />
                    <Label htmlFor="sse" className="font-normal flex items-center gap-2">
                      <Globe className="h-4 w-4" />
                      SSE (HTTP)
                    </Label>
                  </div>
                </RadioGroup>
              </div>

              {/* Stdio Config */}
              {transportType === 'stdio' && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="command">Command *</Label>
                    <Input
                      id="command"
                      value={command}
                      onChange={(e) => setCommand(e.target.value)}
                      placeholder="npx"
                    />
                    <p className="text-xs text-muted-foreground">
                      The command to run (e.g., npx, python, node)
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="args">Arguments</Label>
                    <Input
                      id="args"
                      value={args}
                      onChange={(e) => setArgs(e.target.value)}
                      placeholder="-y @modelcontextprotocol/server-filesystem /path"
                    />
                    <p className="text-xs text-muted-foreground">
                      Space-separated arguments
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="envVars">Environment Variables</Label>
                    <Textarea
                      id="envVars"
                      value={envVars}
                      onChange={(e) => setEnvVars(e.target.value)}
                      placeholder='{"API_KEY": "your-secret-key"}'
                      rows={3}
                      className="font-mono text-sm"
                    />
                    <p className="text-xs text-muted-foreground">
                      JSON object of environment variables (encrypted at rest)
                    </p>
                  </div>
                </>
              )}

              {/* HTTP Config */}
              {transportType !== 'stdio' && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="url">URL *</Label>
                    <Input
                      id="url"
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                      placeholder="http://localhost:3000/mcp"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="headers">Headers</Label>
                    <Textarea
                      id="headers"
                      value={headers}
                      onChange={(e) => setHeaders(e.target.value)}
                      placeholder='{"Authorization": "Bearer ..."}'
                      rows={3}
                      className="font-mono text-sm"
                    />
                    <p className="text-xs text-muted-foreground">
                      JSON object of HTTP headers (may include auth tokens)
                    </p>
                  </div>
                </>
              )}

              {/* Test Connection Button */}
              <div className="pt-4 border-t">
                <Button
                  onClick={handleTest}
                  disabled={isTesting || !isEditing}
                  variant="secondary"
                  className="w-full"
                >
                  {isTesting ? (
                    <Spinner className="mr-2 h-4 w-4" />
                  ) : (
                    <TestTube2 className="mr-2 h-4 w-4" />
                  )}
                  Test Connection
                </Button>
                {!isEditing && (
                  <p className="text-xs text-muted-foreground text-center mt-2">
                    Save the server first to test the connection
                  </p>
                )}

                {/* Test Result */}
                {testResult && (
                  <div className={`mt-4 p-3 rounded-md ${
                    testResult.success
                      ? 'bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-900'
                      : 'bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900'
                  }`}>
                    <div className={`flex items-center gap-2 text-sm font-medium ${
                      testResult.success
                        ? 'text-green-700 dark:text-green-400'
                        : 'text-red-700 dark:text-red-400'
                    }`}>
                      {testResult.success ? (
                        <CheckCircle className="h-4 w-4" />
                      ) : (
                        <AlertCircle className="h-4 w-4" />
                      )}
                      {testResult.success ? 'Connection Successful' : 'Connection Failed'}
                    </div>
                    <p className={`mt-1 text-sm ${
                      testResult.success
                        ? 'text-green-600 dark:text-green-500'
                        : 'text-red-600 dark:text-red-500'
                    }`}>
                      {testResult.message}
                    </p>
                    {testResult.latency_ms && (
                      <p className="mt-1 text-xs text-muted-foreground">
                        Latency: {testResult.latency_ms}ms
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>
          </ScrollArea>
        </div>

        {/* Right side - Server Settings & Discovered Tools (1/3 width) */}
        <div className="flex flex-col min-h-0 gap-4">
          {/* Server Settings */}
          <div className="border rounded-lg overflow-hidden shrink-0">
            <div className="flex items-center gap-2 px-4 py-2 border-b bg-muted/30 text-sm font-medium">
              <Plug2 className="h-4 w-4" />
              Server Settings
            </div>
            <div className="p-4 space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name *</Label>
                <Input
                  id="name"
                  placeholder="My MCP Server"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="What does this server provide?"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="resize-none h-20"
                />
              </div>

              {/* Status info for existing servers */}
              {isEditing && server && (
                <div className="pt-3 border-t space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Status</span>
                    <Badge variant={server.is_active ? 'default' : 'secondary'}>
                      {server.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                  {server.last_connected_at && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Last connected</span>
                      <span>{new Date(server.last_connected_at).toLocaleDateString()}</span>
                    </div>
                  )}
                  {server.last_error && (
                    <div className="text-red-600 dark:text-red-400 text-xs mt-2">
                      Last error: {server.last_error}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Discovered Tools */}
          <div className="flex-1 flex flex-col min-h-0 border rounded-lg overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/30 shrink-0">
              <div className="flex items-center gap-2 text-sm font-medium">
                <Wrench className="h-4 w-4" />
                Discovered Tools
              </div>
              {testResult?.tools_count ? (
                <Badge variant="secondary">{testResult.tools_count}</Badge>
              ) : server?.cached_tools_count ? (
                <Badge variant="secondary">{server.cached_tools_count}</Badge>
              ) : null}
            </div>

            <ScrollArea className="flex-1 p-4">
              {/* Show tools from test result or cached */}
              {testResult?.tools && testResult.tools.length > 0 ? (
                <div className="space-y-3">
                  {testResult.tools.map((tool, index) => (
                    <div key={index} className="p-3 rounded-md bg-muted/50">
                      <div className="font-medium text-sm">{tool.name}</div>
                      <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                        {tool.description || 'No description'}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Wrench className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">
                    {isEditing
                      ? 'Test the connection to discover available tools'
                      : 'Save and test to discover tools'}
                  </p>
                </div>
              )}
            </ScrollArea>
          </div>
        </div>
      </div>
    </div>
  );
}
