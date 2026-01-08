import { useEffect, useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Button,
  Input,
  Textarea,
  Badge,
  Spinner,
  Alert,
  AlertDescription,
  ScrollArea,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui';
import {
  Save,
  X,
  FileText,
  AlertCircle,
  Variable,
  Eye,
} from 'lucide-react';
import {
  usePrompt,
  useCreatePrompt,
  useUpdatePrompt,
  useCreatePromptVersion,
  getErrorMessage,
} from '@/api/hooks';
import { PromptUseCase, MessageType, PromptVersion } from '@/api/types';
import { VersionHistoryPanel, VersionDetailDialog } from '@/components/prompts';

const USE_CASES: { value: PromptUseCase; label: string }[] = [
  { value: 'research', label: 'Research' },
  { value: 'coding', label: 'Coding' },
  { value: 'analysis', label: 'Analysis' },
  { value: 'writing', label: 'Writing' },
  { value: 'conversation', label: 'Conversation' },
  { value: 'planning', label: 'Planning' },
  { value: 'other', label: 'Other' },
];

const MESSAGE_TYPES: { value: MessageType; label: string }[] = [
  { value: 'system', label: 'System' },
  { value: 'user', label: 'User' },
  { value: 'assistant', label: 'Assistant' },
];

const promptFormSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100, 'Name must be less than 100 characters'),
  description: z.string().max(500, 'Description must be less than 500 characters').optional(),
  use_case: z.enum(['research', 'coding', 'analysis', 'writing', 'conversation', 'planning', 'other']),
  message_type: z.enum(['system', 'user', 'assistant']),
  tags: z.array(z.string()).default([]),
  template: z.string().min(1, 'Template is required').max(10000, 'Template must be less than 10000 characters'),
});

type PromptFormData = z.infer<typeof promptFormSchema>;

export function PromptEditorPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const isEditing = id !== undefined && id !== 'new';
  const promptId = isEditing ? parseInt(id) : undefined;

  // Form state
  const [activeTab, setActiveTab] = useState('basic');
  const [tagInput, setTagInput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Version detail dialog state
  const [selectedVersion, setSelectedVersion] = useState<PromptVersion | null>(null);
  const [versionDialogOpen, setVersionDialogOpen] = useState(false);

  // Data hooks
  const { data: prompt, isLoading: isLoadingPrompt } = usePrompt(promptId);

  const createPrompt = useCreatePrompt();
  const updatePrompt = useUpdatePrompt(promptId ?? 0);
  const createVersion = useCreatePromptVersion(promptId ?? 0);

  const form = useForm<PromptFormData>({
    resolver: zodResolver(promptFormSchema),
    defaultValues: {
      name: '',
      description: '',
      use_case: 'other',
      message_type: 'system',
      tags: [],
      template: '',
    },
  });

  // Detect variables in template
  const detectedVariables = useMemo(() => {
    const template = form.watch('template');
    if (!template) return [];
    const matches = template.match(/\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g) || [];
    return [...new Set(matches.map((m) => m.slice(1, -1)))];
  }, [form.watch('template')]);

  // Load prompt data when editing
  useEffect(() => {
    if (prompt && isEditing) {
      form.reset({
        name: prompt.name,
        description: prompt.description || '',
        use_case: prompt.use_case,
        message_type: prompt.current_version?.message_type || 'system',
        tags: prompt.tags || [],
        template: prompt.current_version?.template || '',
      });
      setHasUnsavedChanges(false);
    }
  }, [prompt, isEditing, form]);

  // Track unsaved changes
  useEffect(() => {
    const subscription = form.watch(() => {
      if (!isLoadingPrompt) {
        setHasUnsavedChanges(true);
      }
    });
    return () => subscription.unsubscribe();
  }, [form, isLoadingPrompt]);

  const handleAddTag = () => {
    const tag = tagInput.trim();
    if (tag && !form.getValues('tags').includes(tag)) {
      form.setValue('tags', [...form.getValues('tags'), tag]);
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    form.setValue(
      'tags',
      form.getValues('tags').filter((tag) => tag !== tagToRemove)
    );
  };

  const onSubmit = async (data: PromptFormData) => {
    setError(null);

    try {
      if (isEditing && promptId) {
        // Update metadata
        const metadataPayload = {
          name: data.name,
          description: data.description || undefined,
          use_case: data.use_case,
          tags: data.tags,
        };
        await updatePrompt.mutateAsync(metadataPayload);

        // Check if template or message_type changed - if so, create a new version
        const originalTemplate = prompt?.current_version?.template || '';
        const originalMessageType = prompt?.current_version?.message_type || 'system';
        const templateChanged = data.template !== originalTemplate;
        const messageTypeChanged = data.message_type !== originalMessageType;

        if (templateChanged || messageTypeChanged) {
          await createVersion.mutateAsync({
            template: data.template,
            message_type: data.message_type,
          });
        }
      } else {
        // Create new prompt with version
        const createPayload = {
          name: data.name,
          description: data.description || undefined,
          use_case: data.use_case,
          tags: data.tags,
          version: {
            template: data.template,
            message_type: data.message_type,
          },
        };
        const created = await createPrompt.mutateAsync(createPayload);
        navigate(`/prompts/${created.id}`, { replace: true });
      }
      setHasUnsavedChanges(false);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const handleCancel = () => {
    navigate('/prompts');
  };

  const handleViewVersion = (version: PromptVersion) => {
    setSelectedVersion(version);
    setVersionDialogOpen(true);
  };

  const isPending = createPrompt.isPending || updatePrompt.isPending || createVersion.isPending;
  const currentPromptName = form.watch('name') || 'New Prompt';

  if (isLoadingPrompt && isEditing) {
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
          <FileText className="h-6 w-6 text-primary" />
          <div>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              {currentPromptName}
              {hasUnsavedChanges && (
                <Badge variant="outline" className="text-yellow-600">
                  Unsaved
                </Badge>
              )}
            </h1>
            <p className="text-sm text-muted-foreground">
              {isEditing ? 'Edit prompt template' : 'Create a new prompt'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleCancel}>
            <X className="mr-2 h-4 w-4" />
            Cancel
          </Button>
          <Button onClick={form.handleSubmit(onSubmit)} disabled={isPending}>
            {isPending ? (
              <Spinner className="mr-2 h-4 w-4" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            {isEditing ? 'Save' : 'Create'}
          </Button>
        </div>
      </div>

      {/* Error alert */}
      {error && (
        <Alert variant="destructive" className="shrink-0">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Main content - split view */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 min-h-0">
        {/* Left side - Form (2/3 width) */}
        <div className="lg:col-span-2 flex flex-col min-h-0 border rounded-lg overflow-hidden">
          <Form {...form}>
            <form className="flex flex-col flex-1 overflow-hidden">
              <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden">
                <TabsList className="grid w-full grid-cols-2 mx-4 mt-4 mb-2" style={{ width: 'calc(100% - 2rem)' }}>
                  <TabsTrigger value="basic">Basic Info</TabsTrigger>
                  <TabsTrigger value="template">Template</TabsTrigger>
                </TabsList>

                <ScrollArea className="flex-1 px-4">
                  {/* Basic Info Tab */}
                  <TabsContent value="basic" className="space-y-4 mt-2 pb-4">
                    <FormField
                      control={form.control}
                      name="name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Name</FormLabel>
                          <FormControl>
                            <Input placeholder="My Prompt" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="description"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Description</FormLabel>
                          <FormControl>
                            <Textarea
                              placeholder="Describe what this prompt does..."
                              className="resize-none"
                              rows={3}
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="use_case"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Use Case</FormLabel>
                          <Select onValueChange={field.onChange} value={field.value}>
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue placeholder="Select use case" />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              {USE_CASES.map((uc) => (
                                <SelectItem key={uc.value} value={uc.value}>
                                  {uc.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="tags"
                      render={() => (
                        <FormItem>
                          <FormLabel>Tags</FormLabel>
                          <div className="flex gap-2">
                            <Input
                              placeholder="Add a tag..."
                              value={tagInput}
                              onChange={(e) => setTagInput(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                  e.preventDefault();
                                  handleAddTag();
                                }
                              }}
                            />
                            <Button type="button" variant="secondary" onClick={handleAddTag}>
                              Add
                            </Button>
                          </div>
                          <div className="flex flex-wrap gap-2 mt-2">
                            {form.watch('tags').map((tag) => (
                              <Badge key={tag} variant="secondary" className="gap-1">
                                {tag}
                                <button
                                  type="button"
                                  onClick={() => handleRemoveTag(tag)}
                                  className="ml-1 hover:text-destructive"
                                >
                                  <X className="h-3 w-3" />
                                </button>
                              </Badge>
                            ))}
                          </div>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </TabsContent>

                  {/* Template Tab */}
                  <TabsContent value="template" className="space-y-4 mt-2 pb-4">
                    <FormField
                      control={form.control}
                      name="message_type"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Message Type</FormLabel>
                          <Select onValueChange={field.onChange} value={field.value}>
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue placeholder="Select message type" />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              {MESSAGE_TYPES.map((mt) => (
                                <SelectItem key={mt.value} value={mt.value}>
                                  {mt.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <FormDescription>
                            The role this prompt will be used for in conversations
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="template"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Prompt Template</FormLabel>
                          <FormControl>
                            <Textarea
                              placeholder="You are a helpful assistant that..."
                              className="resize-none min-h-[200px] font-mono text-sm"
                              {...field}
                            />
                          </FormControl>
                          <FormDescription>
                            Use {'{variable_name}'} syntax for template variables
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    {/* Detected Variables */}
                    {detectedVariables.length > 0 && (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <Variable className="h-4 w-4" />
                          <span className="text-sm font-medium">Detected Variables</span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {detectedVariables.map((variable) => (
                            <Badge key={variable} variant="outline" className="font-mono">
                              {'{'}
                              {variable}
                              {'}'}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Preview */}
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <Eye className="h-4 w-4" />
                        <span className="text-sm font-medium">Preview</span>
                      </div>
                      <div className="rounded-md border p-4 bg-muted/50 max-h-[200px] overflow-y-auto">
                        <pre className="text-sm whitespace-pre-wrap font-mono">
                          {form.watch('template') || 'Enter a template to see preview...'}
                        </pre>
                      </div>
                    </div>
                  </TabsContent>
                </ScrollArea>
              </Tabs>
            </form>
          </Form>
        </div>

        {/* Right side - Version History (1/3 width) */}
        <div className="flex flex-col min-h-0 border rounded-lg overflow-hidden">
          <VersionHistoryPanel
            promptId={promptId}
            currentVersionId={prompt?.current_version_id ?? null}
            onViewVersion={handleViewVersion}
          />
        </div>
      </div>

      {/* Version Detail Dialog */}
      <VersionDetailDialog
        open={versionDialogOpen}
        onClose={() => {
          setVersionDialogOpen(false);
          setSelectedVersion(null);
        }}
        version={selectedVersion}
        currentVersion={prompt?.current_version ?? null}
        promptId={promptId ?? 0}
        isCurrentVersion={selectedVersion?.id === prompt?.current_version_id}
      />
    </div>
  );
}
