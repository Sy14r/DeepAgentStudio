/**
 * TaskList Component
 *
 * Displays a list of tasks for a session with status indicators,
 * color-coded backgrounds, and expandable details.
 */
import { useState } from 'react';
import { Badge, ScrollArea } from '@/components/ui';
import {
  Circle,
  PlayCircle,
  CheckCircle,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  ListTodo,
} from 'lucide-react';
import type { Task, TaskStatus } from '@/api/types';

interface TaskItemProps {
  task: Task;
}

function TaskItem({ task }: TaskItemProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const hasDetails = task.description || task.notes;

  const getStatusIcon = (status: TaskStatus) => {
    switch (status) {
      case 'pending':
        return <Circle className="h-4 w-4 text-gray-400" />;
      case 'in_progress':
        return <PlayCircle className="h-4 w-4 text-blue-500" />;
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'blocked':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Circle className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStatusColor = (status: TaskStatus) => {
    switch (status) {
      case 'pending':
        return 'border-gray-200 bg-gray-50 dark:bg-gray-950/30 dark:border-gray-800';
      case 'in_progress':
        return 'border-blue-200 bg-blue-50 dark:bg-blue-950/30 dark:border-blue-800';
      case 'completed':
        return 'border-green-200 bg-green-50 dark:bg-green-950/30 dark:border-green-800';
      case 'blocked':
        return 'border-red-200 bg-red-50 dark:bg-red-950/30 dark:border-red-800';
      default:
        return 'border-gray-200 bg-gray-50 dark:bg-gray-950/30 dark:border-gray-800';
    }
  };

  const getStatusBadgeVariant = (status: TaskStatus): 'default' | 'secondary' | 'destructive' | 'outline' => {
    switch (status) {
      case 'pending':
        return 'secondary';
      case 'in_progress':
        return 'default';
      case 'completed':
        return 'outline';
      case 'blocked':
        return 'destructive';
      default:
        return 'secondary';
    }
  };

  return (
    <div
      className={`rounded-lg border p-3 transition-all ${getStatusColor(task.status)}`}
    >
      <div className="flex items-start gap-3">
        <span className="shrink-0 mt-0.5">{getStatusIcon(task.status)}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-sm">
              #{task.id}: {task.title}
            </span>
            <Badge variant={getStatusBadgeVariant(task.status)} className="text-xs capitalize">
              {task.status.replace('_', ' ')}
            </Badge>
          </div>

          {/* Expandable details */}
          {isExpanded && hasDetails && (
            <div className="mt-2 space-y-2">
              {task.description && (
                <p className="text-sm text-muted-foreground">{task.description}</p>
              )}
              {task.notes && (
                <div className="text-xs bg-background/50 rounded p-2 whitespace-pre-wrap">
                  <span className="font-medium">Notes:</span>
                  <p className="mt-1 text-muted-foreground">{task.notes}</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Expand/collapse button */}
        {hasDetails && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="shrink-0 p-1 hover:bg-background/50 rounded transition-colors"
            title={isExpanded ? 'Collapse' : 'Expand'}
          >
            {isExpanded ? (
              <ChevronUp className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            )}
          </button>
        )}
      </div>
    </div>
  );
}

interface TaskListProps {
  tasks: Task[];
  isLoading?: boolean;
}

export function TaskList({ tasks, isLoading }: TaskListProps) {
  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        <span>Loading tasks...</span>
      </div>
    );
  }

  if (tasks.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-muted-foreground text-center gap-2">
        <ListTodo className="h-8 w-8 opacity-50" />
        <p>No tasks yet.</p>
        <p className="text-sm">Tasks will appear here as the agent creates them.</p>
      </div>
    );
  }

  // Sort tasks: in_progress first, then pending, blocked, completed last
  const sortedTasks = [...tasks].sort((a, b) => {
    const order: Record<TaskStatus, number> = {
      in_progress: 0,
      pending: 1,
      blocked: 2,
      completed: 3,
    };
    return (order[a.status] ?? 4) - (order[b.status] ?? 4);
  });

  // Count tasks by status
  const statusCounts = tasks.reduce(
    (acc, task) => {
      acc[task.status] = (acc[task.status] || 0) + 1;
      return acc;
    },
    {} as Record<TaskStatus, number>
  );

  return (
    <div className="h-full flex flex-col">
      {/* Summary badges */}
      <div className="flex flex-wrap gap-1.5 px-4 pt-4 pb-2">
        {statusCounts.in_progress && (
          <Badge variant="default" className="text-xs flex items-center gap-1">
            <PlayCircle className="h-3 w-3" />
            {statusCounts.in_progress} in progress
          </Badge>
        )}
        {statusCounts.pending && (
          <Badge variant="secondary" className="text-xs flex items-center gap-1">
            <Circle className="h-3 w-3" />
            {statusCounts.pending} pending
          </Badge>
        )}
        {statusCounts.completed && (
          <Badge variant="outline" className="text-xs flex items-center gap-1">
            <CheckCircle className="h-3 w-3" />
            {statusCounts.completed} completed
          </Badge>
        )}
        {statusCounts.blocked && (
          <Badge variant="destructive" className="text-xs flex items-center gap-1">
            <AlertCircle className="h-3 w-3" />
            {statusCounts.blocked} blocked
          </Badge>
        )}
      </div>

      {/* Task list */}
      <ScrollArea className="flex-1">
        <div className="p-4 pt-2 space-y-2">
          {sortedTasks.map((task) => (
            <TaskItem key={task.id} task={task} />
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
