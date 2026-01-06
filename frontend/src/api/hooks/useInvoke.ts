import { useMutation } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import { InvokeRequest, InvokeResponse } from '@/api/types';

export function useInvokeAgent(agentId: number) {
  return useMutation({
    mutationFn: async (data: InvokeRequest): Promise<InvokeResponse> => {
      const response = await apiClient.post<InvokeResponse>(
        `/agents/${agentId}/invoke`,
        data
      );
      return response.data;
    },
  });
}
