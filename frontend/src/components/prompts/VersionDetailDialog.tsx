import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  Button,
  Badge,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  ScrollArea,
  Spinner,
} from '@/components/ui';
import { PromptVersion } from '@/api/types';
import { useRollbackPrompt } from '@/api/hooks';
import {
  Eye,
  GitCompare,
  RotateCcw,
  Clock,
  Hash,
  Variable,
  FileText,
} from 'lucide-react';
import { format } from 'date-fns';

interface VersionDetailDialogProps {
  open: boolean;
  onClose: () => void;
  version: PromptVersion | null;
  currentVersion: PromptVersion | null;
  promptId: number;
  isCurrentVersion: boolean;
}

// Simple diff line component
function DiffLine({ line, type }: { line: string; type: 'added' | 'removed' | 'unchanged' }) {
  const bgColor = {
    added: 'bg-green-500/10 text-green-700 dark:text-green-400',
    removed: 'bg-red-500/10 text-red-700 dark:text-red-400',
    unchanged: '',
  }[type];

  const prefix = {
    added: '+',
    removed: '-',
    unchanged: ' ',
  }[type];

  return (
    <div className={`font-mono text-sm px-2 py-0.5 ${bgColor}`}>
      <span className="select-none text-muted-foreground mr-2">{prefix}</span>
      {line}
    </div>
  );
}

// Simple line-by-line diff
function computeDiff(oldText: string, newText: string): Array<{ line: string; type: 'added' | 'removed' | 'unchanged' }> {
  const oldLines = oldText.split('\n');
  const newLines = newText.split('\n');
  const result: Array<{ line: string; type: 'added' | 'removed' | 'unchanged' }> = [];

  // Simple diff algorithm - show removed then added
  const maxLen = Math.max(oldLines.length, newLines.length);

  for (let i = 0; i < maxLen; i++) {
    const oldLine = oldLines[i];
    const newLine = newLines[i];

    if (oldLine === newLine) {
      result.push({ line: oldLine || '', type: 'unchanged' });
    } else {
      if (oldLine !== undefined) {
        result.push({ line: oldLine, type: 'removed' });
      }
      if (newLine !== undefined) {
        result.push({ line: newLine, type: 'added' });
      }
    }
  }

  return result;
}

export function VersionDetailDialog({
  open,
  onClose,
  version,
  currentVersion,
  promptId,
  isCurrentVersion,
}: VersionDetailDialogProps) {
  const [activeTab, setActiveTab] = useState<string>('view');
  const [confirmRollback, setConfirmRollback] = useState(false);
  const rollback = useRollbackPrompt(promptId);

  const handleRollback = async () => {
    if (!version) return;

    if (!confirmRollback) {
      setConfirmRollback(true);
      return;
    }

    try {
      await rollback.mutateAsync(version.id);
      onClose();
    } catch (error) {
      console.error('Failed to rollback:', error);
    } finally {
      setConfirmRollback(false);
    }
  };

  const handleClose = () => {
    setConfirmRollback(false);
    setActiveTab('view');
    onClose();
  };

  if (!version) return null;

  const diffLines = currentVersion && version.id !== currentVersion.id
    ? computeDiff(version.template, currentVersion.template)
    : null;

  const hasChanges = diffLines && diffLines.some((l) => l.type !== 'unchanged');

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && handleClose()}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Hash className="h-5 w-5" />
            Version {version.version_number}
            {isCurrentVersion && (
              <Badge variant="default" className="ml-2">Current</Badge>
            )}
          </DialogTitle>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="view" className="flex items-center gap-2">
              <Eye className="h-4 w-4" />
              View
            </TabsTrigger>
            <TabsTrigger
              value="compare"
              className="flex items-center gap-2"
              disabled={isCurrentVersion || !currentVersion}
            >
              <GitCompare className="h-4 w-4" />
              Compare
            </TabsTrigger>
          </TabsList>

          <TabsContent value="view" className="flex-1 overflow-hidden mt-4">
            <ScrollArea className="h-[400px]">
              <div className="space-y-4 pr-4">
                {/* Meta Info */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      Created
                    </div>
                    <div className="text-sm">
                      {format(new Date(version.created_at), 'PPpp')}
                    </div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground flex items-center gap-1">
                      <FileText className="h-3 w-3" />
                      Message Type
                    </div>
                    <div>
                      <Badge variant="outline">{version.message_type}</Badge>
                    </div>
                  </div>
                </div>

                {/* Usage */}
                <div className="space-y-1">
                  <div className="text-xs text-muted-foreground">Usage</div>
                  <div className="text-sm">{version.usage_count} times used</div>
                </div>

                {/* Variables */}
                {version.variables.length > 0 && (
                  <div className="space-y-2">
                    <div className="text-xs text-muted-foreground flex items-center gap-1">
                      <Variable className="h-3 w-3" />
                      Variables
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {version.variables.map((variable) => (
                        <Badge key={variable} variant="secondary" className="font-mono">
                          {'{'}
                          {variable}
                          {'}'}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Template */}
                <div className="space-y-2">
                  <div className="text-xs text-muted-foreground">Template</div>
                  <pre className="rounded-md border p-4 text-sm font-mono whitespace-pre-wrap bg-muted/50">
                    {version.template}
                  </pre>
                </div>
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="compare" className="flex-1 overflow-hidden mt-4">
            <ScrollArea className="h-[400px]">
              <div className="space-y-4 pr-4">
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">v{version.version_number}</Badge>
                    <span className="text-muted-foreground">vs</span>
                    <Badge variant="default">v{currentVersion?.version_number} (current)</Badge>
                  </div>
                  {hasChanges ? (
                    <Badge variant="secondary">Has changes</Badge>
                  ) : (
                    <Badge variant="outline">No template changes</Badge>
                  )}
                </div>

                {/* Message Type Change */}
                {currentVersion && version.message_type !== currentVersion.message_type && (
                  <div className="rounded-md border p-3 bg-muted/30">
                    <div className="text-xs text-muted-foreground mb-1">Message Type Changed</div>
                    <div className="flex items-center gap-2 text-sm">
                      <Badge variant="outline" className="bg-red-500/10">{version.message_type}</Badge>
                      <span className="text-muted-foreground">→</span>
                      <Badge variant="outline" className="bg-green-500/10">{currentVersion.message_type}</Badge>
                    </div>
                  </div>
                )}

                {/* Template Diff */}
                <div className="space-y-2">
                  <div className="text-xs text-muted-foreground">Template Diff</div>
                  <div className="rounded-md border overflow-hidden bg-muted/30">
                    {diffLines && diffLines.length > 0 ? (
                      diffLines.map((line, idx) => (
                        <DiffLine key={idx} line={line.line} type={line.type} />
                      ))
                    ) : (
                      <div className="p-4 text-sm text-muted-foreground text-center">
                        No differences
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>

        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={handleClose}>
            Close
          </Button>
          {!isCurrentVersion && (
            <Button
              variant={confirmRollback ? 'default' : 'secondary'}
              onClick={handleRollback}
              disabled={rollback.isPending}
            >
              {rollback.isPending ? (
                <Spinner className="h-4 w-4" />
              ) : confirmRollback ? (
                'Confirm Rollback'
              ) : (
                <>
                  <RotateCcw className="h-4 w-4 mr-2" />
                  Rollback to v{version.version_number}
                </>
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
