import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import {
  Prompt,
  PromptDetail,
  PromptListResponse,
  PromptUseCase,
  MessageType,
} from '@/api/types';

interface PromptCreateRequest {
  name: string;
  description?: string;
  use_case: PromptUseCase;
  message_type: MessageType;
  tags?: string[];
  content: string;
  variables?: string[];
}

interface PromptUpdateRequest {
  name?: string;
  description?: string;
  use_case?: PromptUseCase;
  message_type?: MessageType;
  tags?: string[];
  content?: string;
  variables?: string[];
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
