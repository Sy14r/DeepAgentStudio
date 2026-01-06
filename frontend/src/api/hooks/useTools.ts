import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import {
  Tool,
  ToolCreateRequest,
  ToolListResponse,
  ToolCategory,
} from '@/api/types';

interface UseToolsParams {
  page?: number;
  pageSize?: number;
  search?: string;
  category?: ToolCategory;
  isActive?: boolean;
}

export function useTools(params: UseToolsParams = {}) {
  const { page = 1, pageSize = 50, search, category, isActive } = params;

  return useQuery({
    queryKey: ['tools', { page, pageSize, search, category, isActive }],
    queryFn: async (): Promise<ToolListResponse> => {
      const searchParams = new URLSearchParams();
      searchParams.append('page', page.toString());
      searchParams.append('page_size', pageSize.toString());
      if (search) searchParams.append('search', search);
      if (category) searchParams.append('category', category);
      if (isActive !== undefined) searchParams.append('is_active', isActive.toString());

      const response = await apiClient.get<ToolListResponse>(`/tools?${searchParams.toString()}`);
      return response.data;
    },
  });
}

export function useTool(id: number | undefined) {
  return useQuery({
    queryKey: ['tool', id],
    queryFn: async (): Promise<Tool> => {
      const response = await apiClient.get<Tool>(`/tools/${id}`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateTool() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: ToolCreateRequest): Promise<Tool> => {
      const response = await apiClient.post<Tool>('/tools/custom', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tools'] });
    },
  });
}

export function useUpdateTool(id: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<ToolCreateRequest>): Promise<Tool> => {
      const response = await apiClient.put<Tool>(`/tools/${id}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tools'] });
      queryClient.invalidateQueries({ queryKey: ['tool', id] });
    },
  });
}

export function useDeleteTool() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number): Promise<void> => {
      await apiClient.delete(`/tools/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tools'] });
    },
  });
}

interface SchemaGenerateResponse {
  success: boolean;
  schema?: Record<string, unknown>;
  function_name?: string;
  error?: string;
}

export function useGenerateSchema() {
  return useMutation({
    mutationFn: async (functionCode: string): Promise<SchemaGenerateResponse> => {
      const response = await apiClient.post<SchemaGenerateResponse>(
        '/tools/generate-schema',
        { function_code: functionCode }
      );
      return response.data;
    },
  });
}
