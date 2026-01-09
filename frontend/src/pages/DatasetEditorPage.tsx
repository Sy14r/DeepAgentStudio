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
  Card,
  CardContent,
  Label,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Breadcrumb,
} from '@/components/ui';
import {
  Save,
  X,
  Plus,
  Database,
  AlertCircle,
  Trash2,
  Edit,
  FileUp,
  FileDown,
  Search,
  ChevronLeft,
  ChevronRight,
  Tag,
  ClipboardList,
} from 'lucide-react';
import {
  useDataset,
  useDatasetExamples,
  useCreateDataset,
  useUpdateDataset,
  useCreateDatasetExample,
  useDeleteDatasetExample,
  useImportDataset,
  useExportDataset,
  getErrorMessage,
} from '@/api/hooks';
import { apiClient } from '@/api/client';
import { useQueryClient } from '@tanstack/react-query';
import {
  DatasetSchemaType,
  DatasetExample,
  DatasetExampleCreateRequest,
} from '@/api/types';

const SCHEMA_TYPES: { value: DatasetSchemaType; label: string; description: string }[] = [
  { value: 'text', label: 'Text', description: 'Simple text input/output pairs' },
  { value: 'structured', label: 'Structured', description: 'JSON-based structured data' },
];

export function DatasetEditorPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const isEditing = id !== undefined && id !== 'new';
  const datasetId = isEditing ? parseInt(id) : null;

  // Update example state
  const [isUpdatingExample, setIsUpdatingExample] = useState(false);

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [schemaType, setSchemaType] = useState<DatasetSchemaType>('text');
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');

  // Editor state
  const [error, setError] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Example management state
  const [examplePage, setExamplePage] = useState(1);
  const [exampleSearch, setExampleSearch] = useState('');
  const [showExampleDialog, setShowExampleDialog] = useState(false);
  const [editingExample, setEditingExample] = useState<DatasetExample | null>(null);
  const [exampleForm, setExampleForm] = useState({
    name: '',
    input: '',
    expected_output: '',
    context: '',
    metadata: '',
    tags: [] as string[],
  });
  const [exampleTagInput, setExampleTagInput] = useState('');

  // Import/Export state
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [importFormat, setImportFormat] = useState<'json' | 'csv'>('json');
  const [importFile, setImportFile] = useState<File | null>(null);

  // Data hooks
  const { data: dataset, isLoading: isLoadingDataset } = useDataset(datasetId ?? undefined);
  const { data: examplesData, isLoading: isLoadingExamples } = useDatasetExamples({
    datasetId: datasetId ?? 0,
    page: examplePage,
    pageSize: 20,
  });

  const createDataset = useCreateDataset();
  const updateDataset = useUpdateDataset(datasetId ?? 0);
  const createExample = useCreateDatasetExample(datasetId ?? 0);
  const deleteExample = useDeleteDatasetExample(datasetId ?? 0);
  const importExamples = useImportDataset(datasetId ?? 0);
  const exportExamples = useExportDataset(datasetId ?? 0);

  // Initialize with dataset data
  useEffect(() => {
    if (isEditing && dataset) {
      setName(dataset.name);
      setDescription(dataset.description || '');
      setSchemaType(dataset.schema_type);
      setTags(dataset.tags || []);
      setHasUnsavedChanges(false);
    } else if (!isEditing) {
      setName('');
      setDescription('');
      setSchemaType('text');
      setTags([]);
      setHasUnsavedChanges(false);
    }
  }, [isEditing, dataset]);

  // Track unsaved changes
  useEffect(() => {
    if (!isLoadingDataset && (name || description)) {
      setHasUnsavedChanges(true);
    }
  }, [name, description, schemaType, tags]);

  const handleSave = async () => {
    if (!name.trim()) {
      setError('Dataset name is required');
      return;
    }

    setError(null);

    try {
      const payload = {
        name: name.trim(),
        description: description.trim() || undefined,
        schema_type: schemaType,
        tags: tags.length > 0 ? tags : undefined,
      };

      if (isEditing && datasetId) {
        await updateDataset.mutateAsync(payload);
      } else {
        const created = await createDataset.mutateAsync(payload);
        navigate(`/evaluations/datasets/${created.id}`, { replace: true });
      }
      setHasUnsavedChanges(false);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const handleCancel = () => {
    navigate('/evaluations');
  };

  const handleAddTag = () => {
    if (tagInput.trim() && !tags.includes(tagInput.trim())) {
      setTags([...tags, tagInput.trim()]);
      setTagInput('');
    }
  };

  const handleRemoveTag = (tag: string) => {
    setTags(tags.filter((t) => t !== tag));
  };

  // Example management
  const openExampleDialog = (example?: DatasetExample) => {
    if (example) {
      setEditingExample(example);
      setExampleForm({
        name: example.name || '',
        input: typeof example.input === 'string' ? example.input : JSON.stringify(example.input, null, 2),
        expected_output: typeof example.expected_output === 'string'
          ? example.expected_output
          : JSON.stringify(example.expected_output, null, 2),
        context: example.context ? JSON.stringify(example.context, null, 2) : '',
        metadata: example.metadata ? JSON.stringify(example.metadata, null, 2) : '',
        tags: example.tags || [],
      });
    } else {
      setEditingExample(null);
      setExampleForm({
        name: '',
        input: '',
        expected_output: '',
        context: '',
        metadata: '',
        tags: [],
      });
    }
    setExampleTagInput('');
    setShowExampleDialog(true);
  };

  const handleSaveExample = async () => {
    if (!exampleForm.input.trim()) {
      setError('Example input is required');
      return;
    }

    setError(null);

    try {
      // Parse input and output based on schema type
      let input: unknown = exampleForm.input;
      let expectedOutput: unknown = exampleForm.expected_output;
      let context: unknown = undefined;
      let metadata: Record<string, unknown> | undefined = undefined;

      if (schemaType === 'structured') {
        try {
          input = JSON.parse(exampleForm.input);
        } catch {
          setError('Input must be valid JSON for structured schema');
          return;
        }
        if (exampleForm.expected_output.trim()) {
          try {
            expectedOutput = JSON.parse(exampleForm.expected_output);
          } catch {
            setError('Expected output must be valid JSON for structured schema');
            return;
          }
        }
      }

      if (exampleForm.context.trim()) {
        try {
          context = JSON.parse(exampleForm.context);
        } catch {
          setError('Context must be valid JSON');
          return;
        }
      }

      if (exampleForm.metadata.trim()) {
        try {
          metadata = JSON.parse(exampleForm.metadata);
        } catch {
          setError('Metadata must be valid JSON');
          return;
        }
      }

      const payload: DatasetExampleCreateRequest = {
        name: exampleForm.name.trim() || undefined,
        input,
        expected_output: expectedOutput,
        context,
        metadata,
        tags: exampleForm.tags.length > 0 ? exampleForm.tags : undefined,
      };

      if (editingExample) {
        setIsUpdatingExample(true);
        try {
          await apiClient.put(
            `/evaluations/datasets/${datasetId}/examples/${editingExample.id}`,
            payload
          );
          queryClient.invalidateQueries({ queryKey: ['dataset-examples', datasetId] });
        } finally {
          setIsUpdatingExample(false);
        }
      } else {
        await createExample.mutateAsync(payload);
      }

      setShowExampleDialog(false);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const handleDeleteExample = async (exampleId: number) => {
    if (confirm('Are you sure you want to delete this example?')) {
      try {
        await deleteExample.mutateAsync(exampleId);
      } catch (err) {
        setError(getErrorMessage(err));
      }
    }
  };

  const handleAddExampleTag = () => {
    if (exampleTagInput.trim() && !exampleForm.tags.includes(exampleTagInput.trim())) {
      setExampleForm({ ...exampleForm, tags: [...exampleForm.tags, exampleTagInput.trim()] });
      setExampleTagInput('');
    }
  };

  const handleRemoveExampleTag = (tag: string) => {
    setExampleForm({ ...exampleForm, tags: exampleForm.tags.filter((t) => t !== tag) });
  };

  // Import/Export
  const handleImport = async () => {
    if (!importFile) {
      setError('Please select a file to import');
      return;
    }

    try {
      await importExamples.mutateAsync({ file: importFile, format: importFormat });
      setShowImportDialog(false);
      setImportFile(null);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const handleExport = async (format: 'json' | 'csv') => {
    try {
      const blob = await exportExamples.mutateAsync(format);
      // Download the file
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${name || 'dataset'}_examples.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const isPending = createDataset.isPending || updateDataset.isPending;
  const isLoading = isLoadingDataset && isEditing;

  const examples = examplesData?.examples || [];
  const totalExamples = examplesData?.total || 0;
  const totalPages = Math.ceil(totalExamples / 20);

  if (isLoading) {
    return (
      <div className="container mx-auto py-6 px-4 max-w-5xl flex items-center justify-center min-h-[400px]">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  const breadcrumbItems = [
    { label: 'Evaluations', href: '/evaluations', icon: ClipboardList },
    { label: 'Datasets', href: '/evaluations' },
    { label: name || (isEditing ? 'Loading...' : 'New Dataset'), icon: Database },
  ];

  return (
    <div className="container mx-auto py-6 px-4 max-w-5xl space-y-6">
      {/* Breadcrumb */}
      <Breadcrumb items={breadcrumbItems} />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Database className="h-6 w-6 text-primary" />
          <div>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              {name || 'New Dataset'}
              {hasUnsavedChanges && (
                <Badge variant="outline" className="text-yellow-600">
                  Unsaved
                </Badge>
              )}
            </h1>
            <p className="text-sm text-muted-foreground">
              {isEditing ? 'Edit dataset and manage examples' : 'Create a new evaluation dataset'}
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
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Main content */}
      <Tabs defaultValue="settings">
        <TabsList>
          <TabsTrigger value="settings">Settings</TabsTrigger>
          {isEditing && <TabsTrigger value="examples">Examples ({totalExamples})</TabsTrigger>}
        </TabsList>

        {/* Settings Tab */}
        <TabsContent value="settings" className="mt-6">
          <Card>
            <CardContent className="p-6 space-y-6">
              {/* Name */}
              <div className="space-y-2">
                <Label>Dataset Name</Label>
                <Input
                  placeholder="Enter dataset name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>

              {/* Description */}
              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea
                  placeholder="Describe what this dataset is for..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="resize-none h-24"
                />
              </div>

              {/* Schema Type */}
              <div className="space-y-2">
                <Label>Schema Type</Label>
                <Select
                  value={schemaType}
                  onValueChange={(v) => setSchemaType(v as DatasetSchemaType)}
                  disabled={isEditing && totalExamples > 0}
                >
                  <SelectTrigger className="w-full max-w-xs">
                    <SelectValue placeholder="Select schema type" />
                  </SelectTrigger>
                  <SelectContent>
                    {SCHEMA_TYPES.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        <div>
                          <div className="font-medium">{type.label}</div>
                          <div className="text-xs text-muted-foreground">{type.description}</div>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {isEditing && totalExamples > 0 && (
                  <p className="text-xs text-muted-foreground">
                    Schema type cannot be changed after examples have been added
                  </p>
                )}
              </div>

              {/* Tags */}
              <div className="space-y-2">
                <Label>Tags</Label>
                <div className="flex gap-2 max-w-md">
                  <Input
                    placeholder="Add a tag..."
                    value={tagInput}
                    onChange={(e) => setTagInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
                  />
                  <Button variant="outline" onClick={handleAddTag}>
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
                {tags.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {tags.map((tag) => (
                      <Badge key={tag} variant="secondary" className="gap-1">
                        <Tag className="h-3 w-3" />
                        {tag}
                        <button
                          onClick={() => handleRemoveTag(tag)}
                          className="ml-1 hover:text-destructive"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Examples Tab */}
        {isEditing && (
          <TabsContent value="examples" className="mt-6 space-y-4">
            {/* Examples toolbar */}
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-2 flex-1 max-w-md">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search examples..."
                    value={exampleSearch}
                    onChange={(e) => setExampleSearch(e.target.value)}
                    className="pl-9"
                  />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="outline" onClick={() => setShowImportDialog(true)}>
                  <FileUp className="mr-2 h-4 w-4" />
                  Import
                </Button>
                <Button variant="outline" onClick={() => handleExport('json')} disabled={totalExamples === 0}>
                  <FileDown className="mr-2 h-4 w-4" />
                  Export
                </Button>
                <Button onClick={() => openExampleDialog()}>
                  <Plus className="mr-2 h-4 w-4" />
                  Add Example
                </Button>
              </div>
            </div>

            {/* Examples list */}
            {isLoadingExamples ? (
              <div className="flex items-center justify-center py-12">
                <Spinner className="h-8 w-8" />
              </div>
            ) : examples.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                  <Database className="h-12 w-12 text-muted-foreground mb-4" />
                  <h3 className="text-lg font-semibold">No examples yet</h3>
                  <p className="text-muted-foreground mb-4">
                    Add examples to this dataset to start evaluating your agents.
                  </p>
                  <Button onClick={() => openExampleDialog()}>
                    <Plus className="mr-2 h-4 w-4" />
                    Add First Example
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {examples.map((example) => (
                  <Card key={example.id}>
                    <CardContent className="p-5">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-3">
                            <span className="font-medium text-base">
                              {example.name || `Example #${example.id}`}
                            </span>
                            {example.tags && example.tags.length > 0 && (
                              <div className="flex gap-1">
                                {example.tags.slice(0, 3).map((tag) => (
                                  <Badge key={tag} variant="outline" className="text-xs">
                                    {tag}
                                  </Badge>
                                ))}
                                {example.tags.length > 3 && (
                                  <Badge variant="outline" className="text-xs">
                                    +{example.tags.length - 3}
                                  </Badge>
                                )}
                              </div>
                            )}
                          </div>
                          <div className="grid grid-cols-2 gap-6">
                            <div>
                              <div className="text-sm font-medium text-muted-foreground mb-2">Input</div>
                              <pre className="bg-muted p-3 rounded-md text-sm overflow-x-auto whitespace-pre-wrap break-words">
                                {typeof example.input === 'string'
                                  ? example.input
                                  : JSON.stringify(example.input, null, 2)}
                              </pre>
                            </div>
                            <div>
                              <div className="text-sm font-medium text-muted-foreground mb-2">Expected Output</div>
                              <pre className="bg-muted p-3 rounded-md text-sm overflow-x-auto whitespace-pre-wrap break-words">
                                {typeof example.expected_output === 'string'
                                  ? example.expected_output
                                  : JSON.stringify(example.expected_output, null, 2)}
                              </pre>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-1 shrink-0">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => openExampleDialog(example)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDeleteExample(example.id)}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 pt-4">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setExamplePage((p) => Math.max(1, p - 1))}
                  disabled={examplePage === 1}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <span className="text-sm text-muted-foreground">
                  Page {examplePage} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setExamplePage((p) => Math.min(totalPages, p + 1))}
                  disabled={examplePage === totalPages}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            )}
          </TabsContent>
        )}
      </Tabs>

      {/* Example Dialog */}
      <Dialog open={showExampleDialog} onOpenChange={setShowExampleDialog}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingExample ? 'Edit Example' : 'Add Example'}</DialogTitle>
            <DialogDescription>
              {schemaType === 'text'
                ? 'Enter text input and expected output'
                : 'Enter JSON-structured input and expected output'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Name */}
            <div className="space-y-2">
              <Label>Name (optional)</Label>
              <Input
                placeholder="Example name for easy identification"
                value={exampleForm.name}
                onChange={(e) => setExampleForm({ ...exampleForm, name: e.target.value })}
              />
            </div>

            {/* Input */}
            <div className="space-y-2">
              <Label>Input *</Label>
              <Textarea
                placeholder={schemaType === 'text' ? 'Enter the input text...' : '{\n  "key": "value"\n}'}
                value={exampleForm.input}
                onChange={(e) => setExampleForm({ ...exampleForm, input: e.target.value })}
                className="resize-none h-32 font-mono text-sm"
              />
            </div>

            {/* Expected Output */}
            <div className="space-y-2">
              <Label>Expected Output</Label>
              <Textarea
                placeholder={schemaType === 'text' ? 'Enter the expected output...' : '{\n  "result": "value"\n}'}
                value={exampleForm.expected_output}
                onChange={(e) => setExampleForm({ ...exampleForm, expected_output: e.target.value })}
                className="resize-none h-32 font-mono text-sm"
              />
            </div>

            {/* Context (optional) */}
            <div className="space-y-2">
              <Label>Context (optional, JSON)</Label>
              <Textarea
                placeholder='{"additional": "context"}'
                value={exampleForm.context}
                onChange={(e) => setExampleForm({ ...exampleForm, context: e.target.value })}
                className="resize-none h-20 font-mono text-sm"
              />
            </div>

            {/* Metadata (optional) */}
            <div className="space-y-2">
              <Label>Metadata (optional, JSON)</Label>
              <Textarea
                placeholder='{"difficulty": "easy", "category": "math"}'
                value={exampleForm.metadata}
                onChange={(e) => setExampleForm({ ...exampleForm, metadata: e.target.value })}
                className="resize-none h-20 font-mono text-sm"
              />
            </div>

            {/* Tags */}
            <div className="space-y-2">
              <Label>Tags</Label>
              <div className="flex gap-2">
                <Input
                  placeholder="Add a tag..."
                  value={exampleTagInput}
                  onChange={(e) => setExampleTagInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddExampleTag())}
                />
                <Button variant="outline" onClick={handleAddExampleTag}>
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              {exampleForm.tags.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {exampleForm.tags.map((tag) => (
                    <Badge key={tag} variant="secondary" className="gap-1">
                      {tag}
                      <button
                        onClick={() => handleRemoveExampleTag(tag)}
                        className="ml-1 hover:text-destructive"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowExampleDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSaveExample}
              disabled={createExample.isPending || isUpdatingExample}
            >
              {(createExample.isPending || isUpdatingExample) && (
                <Spinner className="mr-2 h-4 w-4" />
              )}
              {editingExample ? 'Update' : 'Add'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Import Dialog */}
      <Dialog open={showImportDialog} onOpenChange={setShowImportDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Import Examples</DialogTitle>
            <DialogDescription>
              Import examples from JSON or CSV format
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Format</Label>
              <Select value={importFormat} onValueChange={(v) => setImportFormat(v as 'json' | 'csv')}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="json">JSON</SelectItem>
                  <SelectItem value="csv">CSV</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>File</Label>
              <Input
                type="file"
                accept={importFormat === 'json' ? '.json' : '.csv'}
                onChange={(e) => setImportFile(e.target.files?.[0] || null)}
              />
              <p className="text-xs text-muted-foreground">
                {importFormat === 'json'
                  ? 'JSON array of objects with "input" and "expected_output" fields'
                  : 'CSV with "input" and "expected_output" columns'}
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowImportDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleImport} disabled={importExamples.isPending}>
              {importExamples.isPending && <Spinner className="mr-2 h-4 w-4" />}
              Import
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
