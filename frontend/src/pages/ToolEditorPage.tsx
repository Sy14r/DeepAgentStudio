import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Editor, { OnMount } from '@monaco-editor/react';
import {
  Button,
  Input,
  Textarea,
  Badge,
  Spinner,
  Alert,
  AlertDescription,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  ScrollArea,
} from '@/components/ui';
import {
  Save,
  X,
  Play,
  Wrench,
  AlertCircle,
  CheckCircle,
  Code,
  FileCode,
} from 'lucide-react';
import {
  useTool,
  useCreateTool,
  useUpdateTool,
  useGenerateSchema,
  getErrorMessage,
} from '@/api/hooks';
import { useUIStore } from '@/stores/uiStore';
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

export function ToolEditorPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { theme } = useUIStore();

  const isEditing = id !== undefined && id !== 'new';
  const toolId = isEditing ? parseInt(id) : null;

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState<ToolCategory>('other');
  const [code, setCode] = useState(DEFAULT_FUNCTION_CODE);

  // Editor state
  const [error, setError] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const editorRef = useRef<any>(null);

  // Test state
  const [testInput, setTestInput] = useState('');
  const [testOutput, setTestOutput] = useState<string | null>(null);
  const [testError, setTestError] = useState<string | null>(null);
  const [isTesting, setIsTesting] = useState(false);

  // Data hooks
  const { data: tool, isLoading: isLoadingTool } = useTool(toolId ?? undefined);
  const createTool = useCreateTool();
  const updateTool = useUpdateTool(toolId ?? 0);
  const generateSchema = useGenerateSchema();

  // Determine Monaco theme
  const getMonacoTheme = () => {
    if (theme === 'system') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'deepagent-dark'
        : 'deepagent-light';
    }
    return theme === 'dark' ? 'deepagent-dark' : 'deepagent-light';
  };

  // Initialize with tool data
  useEffect(() => {
    if (isEditing && tool) {
      setName(tool.name);
      setDescription(tool.description);
      setCategory(tool.category);
      setCode(tool.function_code || DEFAULT_FUNCTION_CODE);
      setHasUnsavedChanges(false);
    } else if (!isEditing) {
      setName('');
      setDescription('');
      setCategory('other');
      setCode(DEFAULT_FUNCTION_CODE);
      setHasUnsavedChanges(false);
    }
  }, [isEditing, tool]);

  // Track unsaved changes
  useEffect(() => {
    if (!isLoadingTool) {
      setHasUnsavedChanges(true);
    }
  }, [name, description, category, code]);

  const handleEditorMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;

    // Define custom themes
    monaco.editor.defineTheme('deepagent-dark', {
      base: 'vs-dark',
      inherit: true,
      rules: [
        { token: 'keyword', foreground: 'C586C0' },
        { token: 'string', foreground: 'CE9178' },
        { token: 'number', foreground: 'B5CEA8' },
        { token: 'comment', foreground: '6A9955' },
        { token: 'function', foreground: 'DCDCAA' },
        { token: 'variable', foreground: '9CDCFE' },
      ],
      colors: {
        'editor.background': '#0f0f17',
        'editor.foreground': '#e4e4e7',
        'editor.lineHighlightBackground': '#1a1a2e',
        'editor.selectionBackground': '#3d3d5c',
        'editorCursor.foreground': '#60a5fa',
        'editorLineNumber.foreground': '#6b7280',
        'editorLineNumber.activeForeground': '#e4e4e7',
        'editor.inactiveSelectionBackground': '#2d2d44',
      },
    });

    monaco.editor.defineTheme('deepagent-light', {
      base: 'vs',
      inherit: true,
      rules: [
        { token: 'keyword', foreground: 'AF00DB' },
        { token: 'string', foreground: 'A31515' },
        { token: 'number', foreground: '098658' },
        { token: 'comment', foreground: '008000' },
        { token: 'function', foreground: '795E26' },
        { token: 'variable', foreground: '0451A5' },
      ],
      colors: {
        'editor.background': '#fafafa',
        'editor.foreground': '#1f2937',
        'editor.lineHighlightBackground': '#f3f4f6',
        'editor.selectionBackground': '#add6ff',
        'editorCursor.foreground': '#2563eb',
        'editorLineNumber.foreground': '#9ca3af',
        'editorLineNumber.activeForeground': '#1f2937',
        'editor.inactiveSelectionBackground': '#e5ebf1',
      },
    });

    monaco.editor.setTheme(getMonacoTheme());
  };

  const handleSave = async () => {
    if (!name.trim()) {
      setError('Tool name is required');
      return;
    }

    if (!description.trim()) {
      setError('Tool description is required');
      return;
    }

    if (!code.trim()) {
      setError('Function code is required');
      return;
    }

    setError(null);

    try {
      // Auto-generate input schema from function code
      const schemaResult = await generateSchema.mutateAsync(code);

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
        name: name.trim(),
        description: description.trim(),
        category,
        function_code: code,
        input_schema: inputSchema,
      };

      if (isEditing && toolId) {
        await updateTool.mutateAsync(payload);
      } else {
        const created = await createTool.mutateAsync(payload);
        // Navigate to edit page for newly created tool
        navigate(`/tools/${created.id}/edit`, { replace: true });
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
    setIsTesting(true);
    setTestError(null);
    setTestOutput(null);

    try {
      // Simple client-side execution simulation
      // In a real implementation, this would call a backend endpoint
      setTestOutput(`Test execution is not yet implemented.\n\nTo test this tool, save it and use it with an agent in the Playground.`);
    } catch (err) {
      setTestError(getErrorMessage(err));
    } finally {
      setIsTesting(false);
    }
  };

  const isPending = createTool.isPending || updateTool.isPending || generateSchema.isPending;

  if (isLoadingTool && isEditing) {
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
          <Wrench className="h-6 w-6 text-primary" />
          <div>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              {name || 'New Tool'}
              {hasUnsavedChanges && (
                <Badge variant="outline" className="text-yellow-600">
                  Unsaved
                </Badge>
              )}
            </h1>
            <p className="text-sm text-muted-foreground">
              {isEditing ? 'Edit tool implementation' : 'Create a new tool'}
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
        {/* Left side - Code Editor (2/3 width) */}
        <div className="lg:col-span-2 flex flex-col min-h-0 border rounded-lg overflow-hidden">
          {/* Editor header */}
          <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/30 shrink-0">
            <div className="flex items-center gap-2 text-sm font-medium">
              <FileCode className="h-4 w-4" />
              Python Implementation
            </div>
            <Badge variant="secondary" className="text-xs">
              {category}
            </Badge>
          </div>

          {/* Monaco Editor */}
          <div className="flex-1 min-h-0">
            <Editor
              height="100%"
              defaultLanguage="python"
              value={code}
              onChange={(value) => setCode(value || '')}
              onMount={handleEditorMount}
              theme={getMonacoTheme()}
              options={{
                minimap: { enabled: true, maxColumn: 80 },
                fontSize: 14,
                fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                wordWrap: 'on',
                automaticLayout: true,
                tabSize: 4,
                folding: true,
                bracketPairColorization: { enabled: true },
                guides: {
                  bracketPairs: true,
                  indentation: true,
                },
              }}
            />
          </div>
        </div>

        {/* Right side - Tool Settings (1/3 width) */}
        <div className="flex flex-col min-h-0 gap-4">
          {/* Tool Metadata */}
          <div className="border rounded-lg overflow-hidden shrink-0">
            <div className="flex items-center gap-2 px-4 py-2 border-b bg-muted/30 text-sm font-medium">
              <Code className="h-4 w-4" />
              Tool Configuration
            </div>
            <div className="p-4 space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Name</label>
                <Input
                  placeholder="my_tool (use snake_case)"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Use snake_case for OpenAI compatibility
                </p>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Category</label>
                <Select value={category} onValueChange={(v) => setCategory(v as ToolCategory)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select category" />
                  </SelectTrigger>
                  <SelectContent>
                    {TOOL_CATEGORIES.map((cat) => (
                      <SelectItem key={cat.value} value={cat.value}>
                        {cat.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Description</label>
                <Textarea
                  placeholder="Describe what this tool does and when the agent should use it..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="resize-none h-24"
                />
                <p className="text-xs text-muted-foreground">
                  This helps the LLM understand when to use this tool
                </p>
              </div>
            </div>
          </div>

          {/* Test Panel */}
          <div className="flex-1 flex flex-col min-h-0 border rounded-lg overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/30 shrink-0">
              <div className="flex items-center gap-2 text-sm font-medium">
                <Play className="h-4 w-4" />
                Test Tool
              </div>
            </div>

            <ScrollArea className="flex-1 p-4">
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Test Input</label>
                  <Textarea
                    placeholder='Enter test input (e.g., "hello world" or {"key": "value"})'
                    value={testInput}
                    onChange={(e) => setTestInput(e.target.value)}
                    className="resize-none h-20 font-mono text-sm"
                  />
                </div>

                <Button
                  onClick={handleTest}
                  disabled={isTesting}
                  className="w-full"
                  variant="secondary"
                >
                  {isTesting ? (
                    <Spinner className="mr-2 h-4 w-4" />
                  ) : (
                    <Play className="mr-2 h-4 w-4" />
                  )}
                  Run Test
                </Button>

                {testOutput && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm font-medium text-green-600">
                      <CheckCircle className="h-4 w-4" />
                      Output
                    </div>
                    <pre className="p-3 rounded-md bg-muted text-sm font-mono whitespace-pre-wrap overflow-x-auto">
                      {testOutput}
                    </pre>
                  </div>
                )}

                {testError && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm font-medium text-red-600">
                      <AlertCircle className="h-4 w-4" />
                      Error
                    </div>
                    <pre className="p-3 rounded-md bg-red-50 dark:bg-red-950/30 text-sm font-mono text-red-600 whitespace-pre-wrap overflow-x-auto">
                      {testError}
                    </pre>
                  </div>
                )}

                {!testOutput && !testError && (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    Click "Run Test" to execute the tool with your test input.
                  </p>
                )}
              </div>
            </ScrollArea>
          </div>
        </div>
      </div>
    </div>
  );
}
