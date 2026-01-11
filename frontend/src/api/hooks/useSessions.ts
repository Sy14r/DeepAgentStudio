import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import { SessionListResponse, SessionDetail, SessionStatus, SessionStatistics, Message, TraceStep } from '@/api/types';

interface SessionUpdateData {
  title?: string;
}

interface UseSessionsParams {
  page?: number;
  pageSize?: number;
  agentId?: number;
  status?: SessionStatus;
  excludeEvaluation?: boolean;
}

export function useSessions(params: UseSessionsParams = {}) {
  const { page = 1, pageSize = 10, agentId, status, excludeEvaluation } = params;

  return useQuery({
    queryKey: ['sessions', { page, pageSize, agentId, status, excludeEvaluation }],
    queryFn: async () => {
      const searchParams = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });

      if (agentId) {
        searchParams.append('agent_id', agentId.toString());
      }
      if (status) {
        searchParams.append('status', status);
      }
      if (excludeEvaluation) {
        searchParams.append('exclude_evaluation', 'true');
      }

      const response = await apiClient.get<SessionListResponse>(
        `/sessions?${searchParams.toString()}`
      );
      return response.data;
    },
  });
}

export function useSession(sessionId: number | undefined) {
  return useQuery({
    queryKey: ['sessions', sessionId],
    queryFn: async () => {
      if (!sessionId) throw new Error('Session ID is required');
      const response = await apiClient.get<SessionDetail>(`/sessions/${sessionId}`);
      return response.data;
    },
    enabled: !!sessionId,
  });
}

export function useSessionStatistics(agentId?: number) {
  return useQuery({
    queryKey: ['sessions', 'statistics', agentId],
    queryFn: async () => {
      const url = agentId
        ? `/sessions/statistics?agent_id=${agentId}`
        : '/sessions/statistics';
      const response = await apiClient.get<SessionStatistics>(url);
      return response.data;
    },
  });
}

/**
 * Fetch messages for a specific session.
 * Useful for loading chat history when resuming a session.
 */
export function useSessionMessages(sessionId: number | undefined) {
  return useQuery({
    queryKey: ['sessions', sessionId, 'messages'],
    queryFn: async () => {
      if (!sessionId) throw new Error('Session ID is required');
      const response = await apiClient.get<Message[]>(`/sessions/${sessionId}/messages`);
      return response.data;
    },
    enabled: !!sessionId,
  });
}

/**
 * Fetch trace steps for a specific session.
 * Used to sync real-time traces with complete database traces.
 */
export function useSessionTraces(sessionId: number | undefined, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['sessions', sessionId, 'traces'],
    queryFn: async () => {
      if (!sessionId) throw new Error('Session ID is required');
      const response = await apiClient.get<TraceStep[]>(`/sessions/${sessionId}/traces`);
      return response.data;
    },
    enabled: options?.enabled !== undefined ? options.enabled && !!sessionId : !!sessionId,
  });
}

/**
 * Update session data (e.g., rename).
 */
export function useUpdateSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ sessionId, data }: { sessionId: number; data: SessionUpdateData }) => {
      const response = await apiClient.put<SessionDetail>(`/sessions/${sessionId}`, data);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      queryClient.setQueryData(['sessions', data.id], data);
    },
  });
}

/**
 * Delete a session.
 */
export function useDeleteSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (sessionId: number) => {
      await apiClient.delete(`/sessions/${sessionId}`);
      return sessionId;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
  });
}
