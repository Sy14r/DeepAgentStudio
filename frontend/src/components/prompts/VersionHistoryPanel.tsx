import {
  Button,
  Badge,
  Spinner,
  ScrollArea,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui';
import { usePromptVersions, useRollbackPrompt } from '@/api/hooks';
import { PromptVersion } from '@/api/types';
import { History, Eye, RotateCcw, Star, Clock, Hash } from 'lucide-react';
import { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';

interface VersionHistoryPanelProps {
  promptId: number | undefined;
  currentVersionId: number | null;
  onViewVersion: (version: PromptVersion) => void;
}

export function VersionHistoryPanel({
  promptId,
  currentVersionId,
  onViewVersion,
}: VersionHistoryPanelProps) {
  const [rollbackDialogOpen, setRollbackDialogOpen] = useState(false);
  const [selectedVersionForRollback, setSelectedVersionForRollback] = useState<PromptVersion | null>(null);

  const { data: versionsData, isLoading } = usePromptVersions(promptId);
  const rollback = useRollbackPrompt(promptId ?? 0);

  const versions = versionsData?.versions || [];

  const handleRollbackClick = (version: PromptVersion) => {
    setSelectedVersionForRollback(version);
    setRollbackDialogOpen(true);
  };

  const confirmRollback = async () => {
    if (selectedVersionForRollback) {
      try {
        await rollback.mutateAsync(selectedVersionForRollback.id);
        setRollbackDialogOpen(false);
        setSelectedVersionForRollback(null);
      } catch (error) {
        console.error('Failed to rollback:', error);
      }
    }
  };

  if (!promptId) {
    return (
      <div className="p-4 text-center text-muted-foreground">
        <History className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">Save your prompt to see version history</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-2 p-4 border-b">
        <History className="h-4 w-4" />
        <h3 className="font-semibold">Version History</h3>
        <Badge variant="secondary" className="ml-auto">
          {versions.length} version{versions.length !== 1 ? 's' : ''}
        </Badge>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-3">
          {versions.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              No versions yet
            </p>
          ) : (
            versions.map((version) => {
              const isCurrent = version.id === currentVersionId;

              return (
                <div
                  key={version.id}
                  className={`rounded-lg border p-3 space-y-2 transition-colors ${
                    isCurrent ? 'border-primary bg-primary/5' : 'hover:border-muted-foreground/50'
                  }`}
                >
                  {/* Version Header */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Hash className="h-3 w-3 text-muted-foreground" />
                      <span className="font-medium">v{version.version_number}</span>
                      {isCurrent && (
                        <Badge variant="default" className="text-xs gap-1">
                          <Star className="h-3 w-3" />
                          Current
                        </Badge>
                      )}
                      {!version.is_active && (
                        <Badge variant="secondary" className="text-xs">
                          Inactive
                        </Badge>
                      )}
                    </div>
                    <Badge variant="outline" className="text-xs">
                      {version.message_type}
                    </Badge>
                  </div>

                  {/* Version Meta */}
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    <span>
                      {formatDistanceToNow(new Date(version.created_at), { addSuffix: true })}
                    </span>
                    <span className="mx-1">•</span>
                    <span>{version.usage_count} uses</span>
                  </div>

                  {/* Variables */}
                  {version.variables.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {version.variables.map((variable) => (
                        <Badge key={variable} variant="outline" className="text-xs font-mono">
                          {'{'}
                          {variable}
                          {'}'}
                        </Badge>
                      ))}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-2 pt-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 text-xs"
                      onClick={() => onViewVersion(version)}
                    >
                      <Eye className="h-3 w-3 mr-1" />
                      View
                    </Button>
                    {!isCurrent && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 text-xs"
                        onClick={() => handleRollbackClick(version)}
                      >
                        <RotateCcw className="h-3 w-3 mr-1" />
                        Rollback
                      </Button>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </ScrollArea>

      {/* Rollback Confirmation Dialog */}
      <Dialog open={rollbackDialogOpen} onOpenChange={setRollbackDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rollback to Version {selectedVersionForRollback?.version_number}?</DialogTitle>
            <DialogDescription>
              This will create a new version based on version {selectedVersionForRollback?.version_number}.
              The current version will be preserved in history.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRollbackDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={confirmRollback} disabled={rollback.isPending}>
              {rollback.isPending ? <Spinner className="h-4 w-4" /> : 'Rollback'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
