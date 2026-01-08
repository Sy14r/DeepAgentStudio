import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import {
  Prompt,
  PromptDetail,
  PromptVersion,
  PromptListResponse,
  PromptUseCase,
  MessageType,
} from '@/api/types';

interface PromptVersionsResponse {
  versions: PromptVersion[];
  total: number;
}

interface PromptVersionConfig {
  template: string;
  message_type: MessageType;
  is_active?: boolean;
}

interface PromptCreateRequest {
  name: string;
  description?: string;
  use_case: PromptUseCase;
  tags?: string[];
  version: PromptVersionConfig;
}

interface PromptUpdateRequest {
  name?: string;
  description?: string;
  use_case?: PromptUseCase;
  tags?: string[];
}

interface PromptVersionCreateRequest {
  template: string;
  message_type?: MessageType;
  is_active?: boolean;
}

interface UsePromptsParams {
  page?: number;
  pageSize?: number;
  search?: string;
  useCase?: PromptUseCase;
  messageType?: MessageType;
  isActive?: boolean;
}

export function usePrompts(params: UsePromptsParams = {}) {
  const { page = 1, pageSize = 50, search, useCase, messageType, isActive } = params;

  return useQuery({
    queryKey: ['prompts', { page, pageSize, search, useCase, messageType, isActive }],
    queryFn: async (): Promise<PromptListResponse> => {
      const searchParams = new URLSearchParams();
      searchParams.append('page', page.toString());
      searchParams.append('page_size', pageSize.toString());
      if (search) searchParams.append('search', search);
      if (useCase) searchParams.append('use_case', useCase);
      if (messageType) searchParams.append('message_type', messageType);
      if (isActive !== undefined) searchParams.append('is_active', isActive.toString());

      const response = await apiClient.get<PromptListResponse>(`/prompts?${searchParams.toString()}`);
      return response.data;
    },
  });
}

export function usePrompt(id: number | undefined) {
  return useQuery({
    queryKey: ['prompt', id],
    queryFn: async (): Promise<PromptDetail> => {
      const response = await apiClient.get<PromptDetail>(`/prompts/${id}`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreatePrompt() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: PromptCreateRequest): Promise<Prompt> => {
      const response = await apiClient.post<Prompt>('/prompts', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompts'] });
    },
  });
}

export function useUpdatePrompt(id: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: PromptUpdateRequest): Promise<Prompt> => {
      const response = await apiClient.put<Prompt>(`/prompts/${id}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompts'] });
      queryClient.invalidateQueries({ queryKey: ['prompt', id] });
    },
  });
}

export function useDeletePrompt() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number): Promise<void> => {
      await apiClient.delete(`/prompts/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompts'] });
    },
  });
}

/**
 * Create a new version for an existing prompt.
 * Used when editing a prompt's content (creates a new version instead of modifying existing).
 */
export function useCreatePromptVersion(promptId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: PromptVersionCreateRequest): Promise<PromptDetail> => {
      const response = await apiClient.post<PromptDetail>(`/prompts/${promptId}/versions`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompts'] });
      queryClient.invalidateQueries({ queryKey: ['prompt', promptId] });
      queryClient.invalidateQueries({ queryKey: ['prompt-versions', promptId] });
    },
  });
}

/**
 * Get all versions for a prompt.
 */
export function usePromptVersions(promptId: number | undefined) {
  return useQuery({
    queryKey: ['prompt-versions', promptId],
    queryFn: async (): Promise<PromptVersionsResponse> => {
      // Backend returns an array directly, not an object
      const response = await apiClient.get<PromptVersion[]>(`/prompts/${promptId}/versions`);
      return {
        versions: response.data,
        total: response.data.length,
      };
    },
    enabled: !!promptId,
  });
}

/**
 * Rollback a prompt to a specific version.
 */
export function useRollbackPrompt(promptId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (versionId: number): Promise<PromptDetail> => {
      const response = await apiClient.post<PromptDetail>(`/prompts/${promptId}/rollback`, {
        version_id: versionId,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompts'] });
      queryClient.invalidateQueries({ queryKey: ['prompt', promptId] });
      queryClient.invalidateQueries({ queryKey: ['prompt-versions', promptId] });
    },
  });
}

// Export types for use in components
export type { PromptCreateRequest, PromptUpdateRequest, PromptVersionCreateRequest, PromptVersionConfig, PromptVersionsResponse };
