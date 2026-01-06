import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import { LLMProvider, LLMProviderCreateRequest } from '@/api/types';

interface LLMProviderListResponse {
  providers: LLMProvider[];
  total: number;
  page: number;
  page_size: number;
}

interface UseLLMProvidersParams {
  page?: number;
  pageSize?: number;
  isActive?: boolean;
}

export function useLLMProviders(params: UseLLMProvidersParams = {}) {
  const { page = 1, pageSize = 50, isActive } = params;

  return useQuery({
    queryKey: ['llm-providers', { page, pageSize, isActive }],
    queryFn: async (): Promise<LLMProviderListResponse> => {
      const searchParams = new URLSearchParams();
      searchParams.append('page', page.toString());
      searchParams.append('page_size', pageSize.toString());
      if (isActive !== undefined) searchParams.append('is_active', isActive.toString());

      const response = await apiClient.get<LLMProviderListResponse>(`/llm-providers?${searchParams.toString()}`);
      return response.data;
    },
  });
}

export function useLLMProvider(id: number | undefined) {
  return useQuery({
    queryKey: ['llm-provider', id],
    queryFn: async (): Promise<LLMProvider> => {
      const response = await apiClient.get<LLMProvider>(`/llm-providers/${id}`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateLLMProvider() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: LLMProviderCreateRequest): Promise<LLMProvider> => {
      const response = await apiClient.post<LLMProvider>('/llm-providers', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['llm-providers'] });
    },
  });
}

export function useUpdateLLMProvider(id: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<LLMProviderCreateRequest>): Promise<LLMProvider> => {
      const response = await apiClient.put<LLMProvider>(`/llm-providers/${id}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['llm-providers'] });
      queryClient.invalidateQueries({ queryKey: ['llm-provider', id] });
    },
  });
}

export function useUpdateLLMProviderAPIKey(id: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (api_key: string): Promise<LLMProvider> => {
      const response = await apiClient.put<LLMProvider>(`/llm-providers/${id}/api-key`, { api_key });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['llm-providers'] });
      queryClient.invalidateQueries({ queryKey: ['llm-provider', id] });
    },
  });
}

export function useDeleteLLMProvider() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number): Promise<void> => {
      await apiClient.delete(`/llm-providers/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['llm-providers'] });
    },
  });
}

export function useTestLLMProvider(id: number) {
  return useMutation({
    mutationFn: async (): Promise<{ success: boolean; message: string }> => {
      const response = await apiClient.post<{ success: boolean; message: string }>(`/llm-providers/${id}/test`);
      return response.data;
    },
  });
}
