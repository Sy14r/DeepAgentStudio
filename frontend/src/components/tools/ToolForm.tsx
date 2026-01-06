import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import Editor from '@monaco-editor/react';
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
} from '@/components/ui';
import {
  useTool,
  useCreateTool,
  useUpdateTool,
  useGenerateSchema,
  getErrorMessage,
} from '@/api/hooks';
import { ToolCategory, ToolCreateRequest } from '@/api/types';

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

const DEFAULT_FUNCTION_CODE = `def my_tool(input_param: str) -> str:
    """
    Description of what this tool does.

    Args:
        input_param: Description of the input parameter

    Returns:
        Description of what the function returns
    """
    # Your implementation here
    result = f"Processed: {input_param}"
    return result
`;

const toolFormSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100, 'Name must be less than 100 characters'),
  description: z.string().min(1, 'Description is required').max(500, 'Description must be less than 500 characters'),
  category: z.enum(['search', 'calculator', 'filesystem', 'api', 'database', 'retrieval', 'python', 'other']),
  function_code: z.string().min(1, 'Function code is required'),
});

type ToolFormData = z.infer<typeof toolFormSchema>;

interface ToolFormProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  toolId: number | null;
}

export function ToolForm({ open, onClose, onSuccess, toolId }: ToolFormProps) {
  const [error, setError] = useState<string | null>(null);
  const [codeValue, setCodeValue] = useState(DEFAULT_FUNCTION_CODE);

  const isEditing = toolId !== null;

  const { data: tool, isLoading: isLoadingTool } = useTool(toolId ?? undefined);

  const createTool = useCreateTool();
  const updateTool = useUpdateTool(toolId ?? 0);
  const generateSchema = useGenerateSchema();

  const form = useForm<ToolFormData>({
    resolver: zodResolver(toolFormSchema),
    defaultValues: {
      name: '',
      description: '',
      category: 'other',
      function_code: DEFAULT_FUNCTION_CODE,
    },
  });

  // Load tool data when editing
  useEffect(() => {
    if (tool && isEditing) {
      form.reset({
        name: tool.name,
        description: tool.description,
        category: tool.category,
        function_code: tool.function_code || DEFAULT_FUNCTION_CODE,
      });
      setCodeValue(tool.function_code || DEFAULT_FUNCTION_CODE);
    }
  }, [tool, isEditing, form]);

  // Reset form when dialog closes
  useEffect(() => {
    if (!open) {
      form.reset({
        name: '',
        description: '',
        category: 'other',
        function_code: DEFAULT_FUNCTION_CODE,
      });
      setCodeValue(DEFAULT_FUNCTION_CODE);
      setError(null);
    }
  }, [open, form]);

  const handleCodeChange = (value: string | undefined) => {
    const code = value || '';
    setCodeValue(code);
    form.setValue('function_code', code);
  };

  const onSubmit = async (data: ToolFormData) => {
    setError(null);

    try {
      // Auto-generate input schema from function code
      const schemaResult = await generateSchema.mutateAsync(data.function_code);

      let inputSchema: Record<string, unknown>;
      if (schemaResult.success && schemaResult.schema) {
        inputSchema = schemaResult.schema;
      } else {
        // Fallback to generic schema if generation fails
        console.warn('Schema generation failed:', schemaResult.error);
        inputSchema = {
          type: 'object',
          properties: {
            input: { type: 'string', description: 'Input parameter' }
          },
          required: ['input']
        };
      }

      const payload: ToolCreateRequest = {
        name: data.name,
        description: data.description,
        category: data.category,
        function_code: data.function_code,
        input_schema: inputSchema,
      };

      if (isEditing) {
        await updateTool.mutateAsync(payload);
      } else {
        await createTool.mutateAsync(payload);
      }
      onSuccess();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const isPending = createTool.isPending || updateTool.isPending || generateSchema.isPending;

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? 'Edit Tool' : 'Create Tool'}
          </DialogTitle>
        </DialogHeader>

        {isLoadingTool && isEditing ? (
          <div className="flex justify-center py-8">
            <Spinner className="h-8 w-8" />
          </div>
        ) : (
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              {error && (
                <Alert variant="destructive" className="mb-4">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <div className="grid gap-4 md:grid-cols-2 mb-4">
                <FormField
                  control={form.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Name</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="my_tool"
                          {...field}
                        />
                      </FormControl>
                      <FormDescription>
                        Use snake_case for the tool name
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="category"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Category</FormLabel>
                      <Select
                        onValueChange={field.onChange}
                        value={field.value}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select category" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {TOOL_CATEGORIES.map((cat) => (
                            <SelectItem key={cat.value} value={cat.value}>
                              {cat.label}
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
                name="description"
                render={({ field }) => (
                  <FormItem className="mb-4">
                    <FormLabel>Description</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Describe what this tool does..."
                        className="resize-none"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      This description helps the agent understand when to use this tool
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="function_code"
                render={() => (
                  <FormItem>
                    <FormLabel>Function Code (Python)</FormLabel>
                    <FormControl>
                      <div className="border rounded-md overflow-hidden">
                        <Editor
                          key={`editor-${toolId}`}
                          height="300px"
                          defaultLanguage="python"
                          value={codeValue}
                          onChange={handleCodeChange}
                          theme="vs-dark"
                          options={{
                            minimap: { enabled: false },
                            fontSize: 14,
                            lineNumbers: 'on',
                            scrollBeyondLastLine: false,
                            automaticLayout: true,
                            readOnly: false,
                          }}
                        />
                      </div>
                    </FormControl>
                    <FormDescription>
                      Write a Python function that will be executed when the tool is called
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

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
                    'Create Tool'
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
