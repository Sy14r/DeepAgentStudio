import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import {
  AgentTypeConfig,
  AgentTypeConfigCreateRequest,
  AgentTypeConfigUpdateRequest,
  AgentTypeConfigListResponse,
  ExecutionStrategy,
  StrategyValidateRequest,
  StrategyValidateResponse,
  StrategyTemplatesResponse,
  StrategyTemplateResponse,
} from '@/api/types';

interface UseAgentTypesParams {
  page?: number;
  pageSize?: number;
  search?: string;
  strategy?: ExecutionStrategy;
  includeBuiltin?: boolean;
  isActive?: boolean;
}

export function useAgentTypes(params: UseAgentTypesParams = {}) {
  const { page = 1, pageSize = 50, search, strategy, includeBuiltin = true, isActive } = params;

  return useQuery({
    queryKey: ['agentTypes', { page, pageSize, search, strategy, includeBuiltin, isActive }],
    queryFn: async (): Promise<AgentTypeConfigListResponse> => {
      const searchParams = new URLSearchParams();
      searchParams.append('page', page.toString());
      searchParams.append('page_size', pageSize.toString());
      if (search) searchParams.append('search', search);
      if (strategy) searchParams.append('strategy', strategy);
      searchParams.append('include_builtin', includeBuiltin.toString());
      if (isActive !== undefined) searchParams.append('is_active', isActive.toString());

      const response = await apiClient.get<AgentTypeConfigListResponse>(`/agent-types?${searchParams.toString()}`);
      return response.data;
    },
  });
}

export function useAgentType(id: number | undefined) {
  return useQuery({
    queryKey: ['agentType', id],
    queryFn: async (): Promise<AgentTypeConfig> => {
      const response = await apiClient.get<AgentTypeConfig>(`/agent-types/${id}`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateAgentType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: AgentTypeConfigCreateRequest): Promise<AgentTypeConfig> => {
      const response = await apiClient.post<AgentTypeConfig>('/agent-types', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agentTypes'] });
    },
  });
}

export function useUpdateAgentType(id: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: AgentTypeConfigUpdateRequest): Promise<AgentTypeConfig> => {
      const response = await apiClient.put<AgentTypeConfig>(`/agent-types/${id}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agentTypes'] });
      queryClient.invalidateQueries({ queryKey: ['agentType', id] });
    },
  });
}

export function useDeleteAgentType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number): Promise<void> => {
      await apiClient.delete(`/agent-types/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agentTypes'] });
    },
  });
}

export function useCloneAgentType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, newName }: { id: number; newName?: string }): Promise<AgentTypeConfig> => {
      const searchParams = newName ? `?new_name=${encodeURIComponent(newName)}` : '';
      const response = await apiClient.post<AgentTypeConfig>(`/agent-types/${id}/clone${searchParams}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agentTypes'] });
    },
  });
}

// Strategy validation and templates hooks

export function useValidateStrategyCode() {
  return useMutation({
    mutationFn: async (data: StrategyValidateRequest): Promise<StrategyValidateResponse> => {
      const response = await apiClient.post<StrategyValidateResponse>('/agent-types/strategies/validate', data);
      return response.data;
    },
  });
}

export function useStrategyTemplates() {
  return useQuery({
    queryKey: ['strategyTemplates'],
    queryFn: async (): Promise<StrategyTemplatesResponse> => {
      const response = await apiClient.get<StrategyTemplatesResponse>('/agent-types/strategies/templates');
      return response.data;
    },
    staleTime: 1000 * 60 * 60, // Cache for 1 hour - templates don't change often
  });
}

export function useStrategyTemplate(templateName: string | undefined) {
  return useQuery({
    queryKey: ['strategyTemplate', templateName],
    queryFn: async (): Promise<StrategyTemplateResponse> => {
      const response = await apiClient.get<StrategyTemplateResponse>(`/agent-types/strategies/templates/${templateName}`);
      return response.data;
    },
    enabled: !!templateName,
    staleTime: 1000 * 60 * 60, // Cache for 1 hour
  });
}
