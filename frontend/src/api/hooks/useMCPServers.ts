import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import {
  MCPServer,
  MCPServerCreateRequest,
  MCPServerUpdateRequest,
  MCPServerListResponse,
  MCPServerToolsResponse,
  MCPServerTestResponse,
} from '@/api/types';

interface UseMCPServersParams {
  page?: number;
  pageSize?: number;
  activeOnly?: boolean;
}

export function useMCPServers(params: UseMCPServersParams = {}) {
  const { page = 1, pageSize = 50, activeOnly } = params;

  return useQuery({
    queryKey: ['mcp-servers', { page, pageSize, activeOnly }],
    queryFn: async (): Promise<MCPServerListResponse> => {
      const searchParams = new URLSearchParams();
      searchParams.append('skip', ((page - 1) * pageSize).toString());
      searchParams.append('limit', pageSize.toString());
      if (activeOnly !== undefined) searchParams.append('active_only', activeOnly.toString());

      const response = await apiClient.get<MCPServerListResponse>(`/mcp-servers?${searchParams.toString()}`);
      return response.data;
    },
  });
}

export function useMCPServer(id: number | undefined) {
  return useQuery({
    queryKey: ['mcp-server', id],
    queryFn: async (): Promise<MCPServer> => {
      const response = await apiClient.get<MCPServer>(`/mcp-servers/${id}`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateMCPServer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: MCPServerCreateRequest): Promise<MCPServer> => {
      const response = await apiClient.post<MCPServer>('/mcp-servers', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mcp-servers'] });
    },
  });
}

export function useUpdateMCPServer(id: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: MCPServerUpdateRequest): Promise<MCPServer> => {
      const response = await apiClient.put<MCPServer>(`/mcp-servers/${id}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mcp-servers'] });
      queryClient.invalidateQueries({ queryKey: ['mcp-server', id] });
    },
  });
}

export function useDeleteMCPServer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number): Promise<void> => {
      await apiClient.delete(`/mcp-servers/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mcp-servers'] });
    },
  });
}

export function useTestMCPServer(id: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (): Promise<MCPServerTestResponse> => {
      const response = await apiClient.post<MCPServerTestResponse>(`/mcp-servers/${id}/test`);
      return response.data;
    },
    onSuccess: () => {
      // Refresh the server data to get updated cached_tools_count
      queryClient.invalidateQueries({ queryKey: ['mcp-server', id] });
      queryClient.invalidateQueries({ queryKey: ['mcp-servers'] });
    },
  });
}

export function useMCPServerTools(id: number | undefined, refresh: boolean = false) {
  return useQuery({
    queryKey: ['mcp-server-tools', id, refresh],
    queryFn: async (): Promise<MCPServerToolsResponse> => {
      const params = refresh ? '?refresh=true' : '';
      const response = await apiClient.get<MCPServerToolsResponse>(`/mcp-servers/${id}/tools${params}`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useRefreshMCPServerTools(id: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (): Promise<MCPServerToolsResponse> => {
      const response = await apiClient.get<MCPServerToolsResponse>(`/mcp-servers/${id}/tools?refresh=true`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mcp-server-tools', id] });
      queryClient.invalidateQueries({ queryKey: ['mcp-server', id] });
      queryClient.invalidateQueries({ queryKey: ['mcp-servers'] });
    },
  });
}

// Agent MCP Server Assignment Hooks

export function useAgentMCPServers(agentId: number | undefined) {
  return useQuery({
    queryKey: ['agent-mcp-servers', agentId],
    queryFn: async (): Promise<MCPServer[]> => {
      const response = await apiClient.get<MCPServer[]>(`/agents/${agentId}/mcp-servers`);
      return response.data;
    },
    enabled: !!agentId,
  });
}

export function useAssignAgentMCPServers(agentId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (serverIds: number[]): Promise<MCPServer[]> => {
      const response = await apiClient.post<MCPServer[]>(`/agents/${agentId}/mcp-servers`, {
        mcp_server_ids: serverIds,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent-mcp-servers', agentId] });
    },
  });
}
