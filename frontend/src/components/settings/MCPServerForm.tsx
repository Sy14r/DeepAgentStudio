import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Button,
  Input,
  Label,
  Textarea,
  RadioGroup,
  RadioGroupItem,
  Spinner,
  Alert,
  AlertDescription,
} from '@/components/ui';
import {
  useCreateMCPServer,
  useUpdateMCPServer,
  useMCPServer,
  getErrorMessage,
} from '@/api/hooks';
import { MCPTransportType } from '@/api/types';

interface MCPServerFormProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  serverId?: number | null;
}

interface FormData {
  name: string;
  description: string;
  transport_type: MCPTransportType;
  command: string;
  args: string;
  url: string;
  headers: string;
  env_vars: string;
}

const initialFormData: FormData = {
  name: '',
  description: '',
  transport_type: 'stdio',
  command: '',
  args: '',
  url: '',
  headers: '',
  env_vars: '',
};

export function MCPServerForm({
  open,
  onClose,
  onSuccess,
  serverId,
}: MCPServerFormProps) {
  const [formData, setFormData] = useState<FormData>(initialFormData);
  const [error, setError] = useState<string | null>(null);

  const { data: existingServer, isLoading: isLoadingServer } = useMCPServer(
    serverId ?? undefined
  );
  const createMutation = useCreateMCPServer();
  const updateMutation = useUpdateMCPServer(serverId ?? 0);

  const isEditing = !!serverId;
  const isSubmitting = createMutation.isPending || updateMutation.isPending;

  useEffect(() => {
    if (open && existingServer && isEditing) {
      setFormData({
        name: existingServer.name,
        description: existingServer.description || '',
        transport_type: existingServer.transport_type,
        command: existingServer.stdio_config?.command || '',
        args: existingServer.stdio_config?.args?.join(' ') || '',
        url: existingServer.http_config?.url || '',
        headers: existingServer.http_config?.headers
          ? JSON.stringify(existingServer.http_config.headers, null, 2)
          : '',
        env_vars: '', // Never prefill env vars for security
      });
    } else if (open && !isEditing) {
      setFormData(initialFormData);
    }
  }, [open, existingServer, isEditing]);

  const handleChange = (field: keyof FormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validate
    if (!formData.name.trim()) {
      setError('Name is required');
      return;
    }

    if (formData.transport_type === 'stdio' && !formData.command.trim()) {
      setError('Command is required for stdio transport');
      return;
    }

    if (
      (formData.transport_type === 'sse' ||
        formData.transport_type === 'streamable_http') &&
      !formData.url.trim()
    ) {
      setError('URL is required for HTTP transport');
      return;
    }

    // Parse headers JSON if provided
    let headers: Record<string, string> | undefined;
    if (formData.headers.trim()) {
      try {
        headers = JSON.parse(formData.headers);
      } catch {
        setError('Invalid JSON in headers');
        return;
      }
    }

    // Parse env vars JSON if provided
    let env_vars: Record<string, string> | undefined;
    if (formData.env_vars.trim()) {
      try {
        env_vars = JSON.parse(formData.env_vars);
      } catch {
        setError('Invalid JSON in environment variables');
        return;
      }
    }

    // Build request data
    const requestData = {
      name: formData.name.trim(),
      description: formData.description.trim() || undefined,
      transport_type: formData.transport_type,
      stdio_config:
        formData.transport_type === 'stdio'
          ? {
              command: formData.command.trim(),
              args: formData.args.trim()
                ? formData.args.trim().split(/\s+/)
                : [],
            }
          : undefined,
      http_config:
        formData.transport_type !== 'stdio'
          ? {
              url: formData.url.trim(),
              headers,
            }
          : undefined,
      env_vars,
    };

    try {
      if (isEditing) {
        await updateMutation.mutateAsync(requestData);
      } else {
        await createMutation.mutateAsync(requestData);
      }
      onSuccess();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? 'Edit MCP Server' : 'Add MCP Server'}
          </DialogTitle>
          <DialogDescription>
            {isEditing
              ? 'Update the MCP server configuration.'
              : 'Configure a connection to an MCP (Model Context Protocol) server.'}
          </DialogDescription>
        </DialogHeader>

        {isLoadingServer ? (
          <div className="flex justify-center py-8">
            <Spinner className="h-8 w-8" />
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="name">Name *</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => handleChange('name', e.target.value)}
                placeholder="My MCP Server"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => handleChange('description', e.target.value)}
                placeholder="Optional description"
                rows={2}
              />
            </div>

            <div className="space-y-2">
              <Label>Transport Type *</Label>
              <RadioGroup
                value={formData.transport_type}
                onValueChange={(value) =>
                  handleChange('transport_type', value as MCPTransportType)
                }
                className="flex gap-4"
              >
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="stdio" id="stdio" />
                  <Label htmlFor="stdio" className="font-normal">
                    Stdio (Local)
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="sse" id="sse" />
                  <Label htmlFor="sse" className="font-normal">
                    SSE (HTTP)
                  </Label>
                </div>
              </RadioGroup>
            </div>

            {formData.transport_type === 'stdio' ? (
              <>
                <div className="space-y-2">
                  <Label htmlFor="command">Command *</Label>
                  <Input
                    id="command"
                    value={formData.command}
                    onChange={(e) => handleChange('command', e.target.value)}
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
                    value={formData.args}
                    onChange={(e) => handleChange('args', e.target.value)}
                    placeholder="-y @modelcontextprotocol/server-filesystem /path"
                  />
                  <p className="text-xs text-muted-foreground">
                    Space-separated arguments
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="env_vars">Environment Variables</Label>
                  <Textarea
                    id="env_vars"
                    value={formData.env_vars}
                    onChange={(e) => handleChange('env_vars', e.target.value)}
                    placeholder='{"API_KEY": "your-secret-key"}'
                    rows={2}
                    className="font-mono text-sm"
                  />
                  <p className="text-xs text-muted-foreground">
                    JSON object of environment variables (encrypted at rest)
                  </p>
                </div>
              </>
            ) : (
              <>
                <div className="space-y-2">
                  <Label htmlFor="url">URL *</Label>
                  <Input
                    id="url"
                    value={formData.url}
                    onChange={(e) => handleChange('url', e.target.value)}
                    placeholder="http://localhost:3000/mcp"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="headers">Headers</Label>
                  <Textarea
                    id="headers"
                    value={formData.headers}
                    onChange={(e) => handleChange('headers', e.target.value)}
                    placeholder='{"Authorization": "Bearer ..."}'
                    rows={2}
                    className="font-mono text-sm"
                  />
                  <p className="text-xs text-muted-foreground">
                    JSON object of HTTP headers (may include auth tokens)
                  </p>
                </div>
              </>
            )}

            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? (
                  <Spinner className="h-4 w-4" />
                ) : isEditing ? (
                  'Update'
                ) : (
                  'Create'
                )}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
