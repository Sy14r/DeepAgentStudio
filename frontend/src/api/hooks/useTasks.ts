/**
 * React Query hooks for session task management.
 *
 * Provides hooks to fetch and update tasks for a session's workspace.
 */
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import type { Task, TasksResponse } from '../types';

/**
 * Fetch tasks for a session.
 *
 * @param sessionId - Session ID to fetch tasks for
 * @returns React Query result with tasks
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useTasks(sessionId);
 * if (data) {
 *   console.log(data.tasks);
 * }
 * ```
 */
export function useTasks(sessionId: number | undefined) {
  return useQuery({
    queryKey: ['sessions', sessionId, 'tasks'],
    queryFn: async () => {
      const response = await apiClient.get<TasksResponse>(`/sessions/${sessionId}/tasks`);
      return response.data;
    },
    enabled: !!sessionId,
    staleTime: 5000, // Consider data fresh for 5 seconds
    refetchOnWindowFocus: false,
  });
}

/**
 * Hook to get a function that updates the task cache from WebSocket events.
 *
 * @returns Object with methods to update task cache
 *
 * @example
 * ```tsx
 * const taskUpdater = useTasksUpdater();
 *
 * // In WebSocket handler:
 * onTaskCreated: (payload) => taskUpdater.invalidate(sessionId),
 * onTaskUpdated: (payload) => taskUpdater.invalidate(sessionId),
 * ```
 */
export function useTasksUpdater() {
  const queryClient = useQueryClient();

  return {
    /**
     * Invalidate tasks cache to trigger refetch.
     * Use this when tasks are modified via WebSocket events.
     */
    invalidate: (sessionId: number) => {
      queryClient.invalidateQueries({
        queryKey: ['sessions', sessionId, 'tasks'],
      });
    },

    /**
     * Optimistically update a task in the cache.
     * Use for immediate UI updates before server confirmation.
     */
    updateTask: (sessionId: number, taskId: number, updates: Partial<Task>) => {
      queryClient.setQueryData<TasksResponse>(
        ['sessions', sessionId, 'tasks'],
        (old) => {
          if (!old) return old;
          return {
            ...old,
            tasks: old.tasks.map((task) =>
              task.id === taskId ? { ...task, ...updates } : task
            ),
          };
        }
      );
    },

    /**
     * Add a new task to the cache optimistically.
     */
    addTask: (sessionId: number, task: Task) => {
      queryClient.setQueryData<TasksResponse>(
        ['sessions', sessionId, 'tasks'],
        (old) => {
          if (!old) return { tasks: [task] };
          return {
            ...old,
            tasks: [...old.tasks, task],
          };
        }
      );
    },

    /**
     * Remove a task from the cache.
     */
    removeTask: (sessionId: number, taskId: number) => {
      queryClient.setQueryData<TasksResponse>(
        ['sessions', sessionId, 'tasks'],
        (old) => {
          if (!old) return old;
          return {
            ...old,
            tasks: old.tasks.filter((task) => task.id !== taskId),
          };
        }
      );
    },
  };
}
