import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  Button,
  Input,
  Textarea,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  Spinner,
  Alert,
  AlertDescription,
  Badge,
} from '@/components/ui';
import { X } from 'lucide-react';
import {
  usePrompt,
  useCreatePrompt,
  useUpdatePrompt,
  useCreatePromptVersion,
  getErrorMessage,
} from '@/api/hooks';
import { PromptUseCase, MessageType } from '@/api/types';

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

interface PromptFormProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  promptId: number | null;
}

export function PromptForm({ open, onClose, onSuccess, promptId }: PromptFormProps) {
  const [tagInput, setTagInput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [detectedVariables, setDetectedVariables] = useState<string[]>([]);

  const isEditing = promptId !== null;

  const { data: prompt, isLoading: isLoadingPrompt } = usePrompt(promptId ?? undefined);

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

  // Detect variables in content (e.g., {variable_name})
  const detectVariables = (content: string) => {
    const matches = content.match(/\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g) || [];
    const uniqueVars = [...new Set(matches.map((m) => m.slice(1, -1)))];
    setDetectedVariables(uniqueVars);
  };

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
      detectVariables(prompt.current_version?.template || '');
    }
  }, [prompt, isEditing, form]);

  // Reset form when dialog closes
  useEffect(() => {
    if (!open) {
      form.reset({
        name: '',
        description: '',
        use_case: 'other',
        message_type: 'system',
        tags: [],
        template: '',
      });
      setTagInput('');
      setError(null);
      setDetectedVariables([]);
    }
  }, [open, form]);

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

  const handleTemplateChange = (value: string) => {
    form.setValue('template', value);
    detectVariables(value);
  };

  const onSubmit = async (data: PromptFormData) => {
    setError(null);

    try {
      if (isEditing) {
        // When editing, update metadata and optionally create new version if template or message_type changed
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
        // When creating, use nested version structure
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
        await createPrompt.mutateAsync(createPayload);
      }
      onSuccess();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const isPending = createPrompt.isPending || updatePrompt.isPending || createVersion.isPending;

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Edit Prompt' : 'Create Prompt'}</DialogTitle>
        </DialogHeader>

        {isLoadingPrompt && isEditing ? (
          <div className="flex justify-center py-8">
            <Spinner className="h-8 w-8" />
          </div>
        ) : (
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col flex-1 overflow-hidden">
              {error && (
                <Alert variant="destructive" className="mb-4">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <div className="space-y-4 overflow-y-auto pr-2">
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
                          rows={2}
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <div className="grid gap-4 md:grid-cols-2">
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
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

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
                          onChange={(e) => handleTemplateChange(e.target.value)}
                        />
                      </FormControl>
                      <FormDescription>
                        Use {'{variable_name}'} syntax for template variables
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {detectedVariables.length > 0 && (
                  <div>
                    <p className="text-sm font-medium mb-2">Detected Variables:</p>
                    <div className="flex flex-wrap gap-2">
                      {detectedVariables.map((variable) => (
                        <Badge key={variable} variant="outline">
                          {'{'}
                          {variable}
                          {'}'}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t mt-4">
                <Button type="button" variant="outline" onClick={onClose}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isPending}>
                  {isPending ? (
                    <Spinner className="h-4 w-4" />
                  ) : isEditing ? (
                    'Save Changes'
                  ) : (
                    'Create Prompt'
                  )}
                </Button>
              </div>
            </form>
          </Form>
        )}
      </DialogContent>
    </Dialog>
  );
}
