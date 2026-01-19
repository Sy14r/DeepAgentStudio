import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient, getErrorMessage } from '@/api/client';
import {
  Agent,
  AgentDetail,
  AgentCreateRequest,
  AgentUpdateRequest,
  AgentListResponse,
  AgentPermission,
  AgentPermissionUpdate,
} from '@/api/types';

interface UseAgentsParams {
  page?: number;
  pageSize?: number;
  search?: string;
  agentTypeId?: number;
  tags?: string[];
  isActive?: boolean;
}

export function useAgents(params: UseAgentsParams = {}) {
  const { page = 1, pageSize = 10, search, agentTypeId, tags, isActive } = params;

  return useQuery({
    queryKey: ['agents', { page, pageSize, search, agentTypeId, tags, isActive }],
    queryFn: async (): Promise<AgentListResponse> => {
      const searchParams = new URLSearchParams();
      searchParams.append('page', page.toString());
      searchParams.append('page_size', pageSize.toString());
      if (search) searchParams.append('search', search);
      if (agentTypeId !== undefined) searchParams.append('agent_type_id', agentTypeId.toString());
      if (tags && tags.length > 0) {
        tags.forEach((tag) => searchParams.append('tags', tag));
      }
      if (isActive !== undefined) searchParams.append('is_active', isActive.toString());

      const response = await apiClient.get<AgentListResponse>(`/agents?${searchParams.toString()}`);
      return response.data;
    },
  });
}

export function useAgent(id: number | undefined) {
  return useQuery({
    queryKey: ['agent', id],
    queryFn: async (): Promise<AgentDetail> => {
      const response = await apiClient.get<AgentDetail>(`/agents/${id}`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateAgent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: AgentCreateRequest): Promise<Agent> => {
      const response = await apiClient.post<Agent>('/agents', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
  });
}

export function useUpdateAgent(id: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: AgentUpdateRequest): Promise<Agent> => {
      const response = await apiClient.put<Agent>(`/agents/${id}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      queryClient.invalidateQueries({ queryKey: ['agent', id] });
    },
  });
}

export function useDeleteAgent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number): Promise<void> => {
      await apiClient.delete(`/agents/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
  });
}

export function useCloneAgent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number): Promise<Agent> => {
      const response = await apiClient.post<Agent>(`/agents/${id}/clone`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
  });
}

// ============================================================================
// Agent Permissions Hooks
// ============================================================================

export function useAgentPermissions(agentId: number | undefined) {
  return useQuery({
    queryKey: ['agentPermissions', agentId],
    queryFn: async (): Promise<AgentPermission> => {
      const response = await apiClient.get<AgentPermission>(`/agents/${agentId}/permissions`);
      return response.data;
    },
    enabled: !!agentId,
  });
}

export function useUpdateAgentPermissions(agentId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: AgentPermissionUpdate): Promise<AgentPermission> => {
      const response = await apiClient.put<AgentPermission>(`/agents/${agentId}/permissions`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agentPermissions', agentId] });
      queryClient.invalidateQueries({ queryKey: ['agent', agentId] });
    },
  });
}

export { getErrorMessage };
