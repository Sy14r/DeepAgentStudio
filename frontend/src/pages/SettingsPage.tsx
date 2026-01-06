import { useState } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Button,
  Separator,
  Badge,
  Spinner,
  Alert,
  AlertDescription,
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
} from '@/components/ui';
import {
  Settings,
  Key,
  Palette,
  User,
  Plus,
  MoreVertical,
  Pencil,
  Trash2,
  CheckCircle,
  XCircle,
  TestTube,
  Loader2,
} from 'lucide-react';
import { useUIStore } from '@/stores/uiStore';
import { useAuthStore } from '@/stores/authStore';
import {
  useLLMProviders,
  useDeleteLLMProvider,
  getErrorMessage,
} from '@/api/hooks';
import { LLMProvider, LLMProviderType } from '@/api/types';
import { LLMProviderForm } from '@/components/settings/LLMProviderForm';

const PROVIDER_LABELS: Record<LLMProviderType, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  google: 'Google',
  azure_openai: 'Azure OpenAI',
  ollama: 'Ollama',
  llamacpp: 'LlamaCpp',
};

const PROVIDER_COLORS: Record<LLMProviderType, string> = {
  openai: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  anthropic: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  google: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  azure_openai: 'bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-400',
  ollama: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
  llamacpp: 'bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-400',
};

interface ProviderRowProps {
  provider: LLMProvider;
  onEdit: (id: number) => void;
  onDelete: (id: number) => void;
  onTest: (id: number) => void;
  isTestingId: number | null;
  testResult: { id: number; success: boolean; message: string } | null;
}

function ProviderRow({
  provider,
  onEdit,
  onDelete,
  onTest,
  isTestingId,
  testResult,
}: ProviderRowProps) {
  const isTesting = isTestingId === provider.id;
  const hasTestResult = testResult?.id === provider.id;

  return (
    <div className="flex items-center justify-between py-3 border-b last:border-0">
      <div className="flex items-center gap-3">
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <span className="font-medium">{provider.name}</span>
            <Badge className={PROVIDER_COLORS[provider.provider_type]}>
              {PROVIDER_LABELS[provider.provider_type]}
            </Badge>
            {provider.is_active ? (
              <Badge variant="outline" className="text-green-600">
                Active
              </Badge>
            ) : (
              <Badge variant="outline" className="text-red-600">
                Inactive
              </Badge>
            )}
          </div>
          <span className="text-sm text-muted-foreground">
            {provider.last_used_at
              ? `Last used: ${new Date(provider.last_used_at).toLocaleDateString()}`
              : 'Never used'}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {hasTestResult && (
          <div className="flex items-center gap-1 text-sm">
            {testResult.success ? (
              <>
                <CheckCircle className="h-4 w-4 text-green-500" />
                <span className="text-green-600">Connected</span>
              </>
            ) : (
              <>
                <XCircle className="h-4 w-4 text-red-500" />
                <span className="text-red-600 max-w-[150px] truncate">
                  {testResult.message}
                </span>
              </>
            )}
          </div>
        )}

        <Button
          variant="ghost"
          size="sm"
          onClick={() => onTest(provider.id)}
          disabled={isTesting}
        >
          {isTesting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <TestTube className="h-4 w-4" />
          )}
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm">
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => onEdit(provider.id)}>
              <Pencil className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-destructive"
              onClick={() => onDelete(provider.id)}
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

export function SettingsPage() {
  const { theme, setTheme } = useUIStore();
  const { user } = useAuthStore();

  // LLM Provider state
  const [formOpen, setFormOpen] = useState(false);
  const [editingProviderId, setEditingProviderId] = useState<number | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [providerToDelete, setProviderToDelete] = useState<number | null>(null);
  const [testingProviderId, setTestingProviderId] = useState<number | null>(null);
  const [testResult, setTestResult] = useState<{
    id: number;
    success: boolean;
    message: string;
  } | null>(null);

  const { data: providersData, isLoading, error } = useLLMProviders();
  const deleteProvider = useDeleteLLMProvider();

  const providers = providersData?.providers || [];

  const handleAddProvider = () => {
    setEditingProviderId(null);
    setFormOpen(true);
  };

  const handleEditProvider = (id: number) => {
    setEditingProviderId(id);
    setFormOpen(true);
  };

  const handleDeleteProvider = (id: number) => {
    setProviderToDelete(id);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (providerToDelete) {
      try {
        await deleteProvider.mutateAsync(providerToDelete);
        setDeleteDialogOpen(false);
        setProviderToDelete(null);
      } catch (err) {
        console.error('Failed to delete provider:', getErrorMessage(err));
      }
    }
  };

  const handleFormClose = () => {
    setFormOpen(false);
    setEditingProviderId(null);
  };

  const handleFormSuccess = () => {
    handleFormClose();
  };

  const handleTestProvider = async (providerId: number) => {
    setTestingProviderId(providerId);
    setTestResult(null);
    try {
      const response = await fetch(`/api/llm-providers/${providerId}/test`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      const result = await response.json();
      if (response.ok) {
        setTestResult({ id: providerId, success: result.success, message: result.message });
      } else {
        setTestResult({ id: providerId, success: false, message: result.detail || 'Test failed' });
      }
    } catch (err) {
      setTestResult({
        id: providerId,
        success: false,
        message: getErrorMessage(err),
      });
    } finally {
      setTestingProviderId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Manage your account and preferences.
        </p>
      </div>

      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Profile
            </CardTitle>
            <CardDescription>Your account information.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
              <div className="text-sm font-medium">Username</div>
              <div className="text-sm text-muted-foreground">
                {user?.username || '-'}
              </div>
            </div>
            <Separator />
            <div className="grid gap-2">
              <div className="text-sm font-medium">Email</div>
              <div className="text-sm text-muted-foreground">
                {user?.email || '-'}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Palette className="h-5 w-5" />
              Appearance
            </CardTitle>
            <CardDescription>
              Customize how DeepAgent Studio looks.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2">
              <div className="text-sm font-medium">Theme</div>
              <div className="flex gap-2">
                <Button
                  variant={theme === 'light' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setTheme('light')}
                >
                  Light
                </Button>
                <Button
                  variant={theme === 'dark' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setTheme('dark')}
                >
                  Dark
                </Button>
                <Button
                  variant={theme === 'system' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setTheme('system')}
                >
                  System
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Key className="h-5 w-5" />
                  LLM Providers
                </CardTitle>
                <CardDescription>
                  Configure API keys for language model providers.
                </CardDescription>
              </div>
              <Button onClick={handleAddProvider}>
                <Plus className="mr-2 h-4 w-4" />
                Add Provider
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {error && (
              <Alert variant="destructive" className="mb-4">
                <AlertDescription>{getErrorMessage(error)}</AlertDescription>
              </Alert>
            )}

            {isLoading ? (
              <div className="flex justify-center py-8">
                <Spinner className="h-8 w-8" />
              </div>
            ) : providers.length === 0 ? (
              <div className="text-center py-8">
                <Key className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground mb-4">
                  No LLM providers configured yet.
                </p>
                <p className="text-sm text-muted-foreground mb-4">
                  Add API keys for OpenAI, Anthropic, Google, and other
                  providers to use their models with your agents.
                </p>
                <Button onClick={handleAddProvider}>
                  <Plus className="mr-2 h-4 w-4" />
                  Add Your First Provider
                </Button>
              </div>
            ) : (
              <div className="divide-y">
                {providers.map((provider) => (
                  <ProviderRow
                    key={provider.id}
                    provider={provider}
                    onEdit={handleEditProvider}
                    onDelete={handleDeleteProvider}
                    onTest={handleTestProvider}
                    isTestingId={testingProviderId}
                    testResult={testResult}
                  />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Advanced
            </CardTitle>
            <CardDescription>
              Advanced settings and preferences.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Additional settings will be available here in future updates.
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Provider</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this LLM provider? This action
              cannot be undone. Agents using this provider will need to be
              reconfigured.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={confirmDelete}
              disabled={deleteProvider.isPending}
            >
              {deleteProvider.isPending ? (
                <Spinner className="h-4 w-4" />
              ) : (
                'Delete'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create/Edit Form Dialog */}
      <LLMProviderForm
        open={formOpen}
        onClose={handleFormClose}
        onSuccess={handleFormSuccess}
        providerId={editingProviderId}
      />
    </div>
  );
}
