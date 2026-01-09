import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type {
  EvaluationDataset,
  DatasetExample,
  DatasetCreateRequest,
  DatasetUpdateRequest,
  DatasetExampleCreateRequest,
  DatasetExampleUpdateRequest,
  DatasetListResponse,
  DatasetExampleListResponse,
  Evaluator,
  EvaluatorCreateRequest,
  EvaluatorUpdateRequest,
  EvaluatorListResponse,
  EvaluatorTestRequest,
  EvaluatorTestResult,
  EvaluatorCategory,
  EvaluatorType,
  Evaluation,
  EvaluationDetail,
  EvaluationCreateRequest,
  EvaluationUpdateRequest,
  EvaluationListResponse,
  EvaluationRun,
  EvaluationRunDetail,
  EvaluationRunCreateRequest,
  EvaluationRunListResponse,
  EvaluationResultDetail,
  EvaluationResultListResponse,
  EvaluationStatus,
  RunComparisonResponse,
} from '@/api/types';

// ============================================================================
// Dataset Hooks
// ============================================================================

interface UseDatasetsParams {
  page?: number;
  pageSize?: number;
  search?: string;
  isActive?: boolean;
}

export function useDatasets(params: UseDatasetsParams = {}) {
  const { page = 1, pageSize = 50, search, isActive } = params;

  return useQuery({
    queryKey: ['datasets', { page, pageSize, search, isActive }],
    queryFn: async (): Promise<DatasetListResponse> => {
      const searchParams = new URLSearchParams();
      searchParams.append('page', page.toString());
      searchParams.append('page_size', pageSize.toString());
      if (search) searchParams.append('search', search);
      if (isActive !== undefined) searchParams.append('is_active', isActive.toString());

      const response = await apiClient.get<DatasetListResponse>(
        `/evaluations/datasets?${searchParams.toString()}`
      );
      return response.data;
    },
  });
}

export function useDataset(id: number | undefined) {
  return useQuery({
    queryKey: ['dataset', id],
    queryFn: async (): Promise<EvaluationDataset> => {
      const response = await apiClient.get<EvaluationDataset>(`/evaluations/datasets/${id}`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateDataset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: DatasetCreateRequest): Promise<EvaluationDataset> => {
      const response = await apiClient.post<EvaluationDataset>('/evaluations/datasets', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
  });
}

export function useUpdateDataset(id: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: DatasetUpdateRequest): Promise<EvaluationDataset> => {
      const response = await apiClient.put<EvaluationDataset>(`/evaluations/datasets/${id}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
      queryClient.invalidateQueries({ queryKey: ['dataset', id] });
    },
  });
}

export function useDeleteDataset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number): Promise<void> => {
      await apiClient.delete(`/evaluations/datasets/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
  });
}

// ============================================================================
// Dataset Example Hooks
// ============================================================================

interface UseDatasetExamplesParams {
  datasetId: number;
  page?: number;
  pageSize?: number;
}

export function useDatasetExamples(params: UseDatasetExamplesParams) {
  const { datasetId, page = 1, pageSize = 50 } = params;

  return useQuery({
    queryKey: ['dataset-examples', datasetId, { page, pageSize }],
    queryFn: async (): Promise<DatasetExampleListResponse> => {
      const searchParams = new URLSearchParams();
      searchParams.append('page', page.toString());
      searchParams.append('page_size', pageSize.toString());

      const response = await apiClient.get<DatasetExampleListResponse>(
        `/evaluations/datasets/${datasetId}/examples?${searchParams.toString()}`
      );
      return response.data;
    },
    enabled: !!datasetId,
  });
}

export function useDatasetExample(datasetId: number | undefined, exampleId: number | undefined) {
  return useQuery({
    queryKey: ['dataset-example', datasetId, exampleId],
    queryFn: async (): Promise<DatasetExample> => {
      const response = await apiClient.get<DatasetExample>(
        `/evaluations/datasets/${datasetId}/examples/${exampleId}`
      );
      return response.data;
    },
    enabled: !!datasetId && !!exampleId,
  });
}

export function useCreateDatasetExample(datasetId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: DatasetExampleCreateRequest): Promise<DatasetExample> => {
      const response = await apiClient.post<DatasetExample>(
        `/evaluations/datasets/${datasetId}/examples`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataset-examples', datasetId] });
      queryClient.invalidateQueries({ queryKey: ['dataset', datasetId] });
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
  });
}

export function useCreateDatasetExamplesBatch(datasetId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (examples: DatasetExampleCreateRequest[]): Promise<DatasetExample[]> => {
      const response = await apiClient.post<DatasetExample[]>(
        `/evaluations/datasets/${datasetId}/examples/batch`,
        { examples }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataset-examples', datasetId] });
      queryClient.invalidateQueries({ queryKey: ['dataset', datasetId] });
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
  });
}

export function useUpdateDatasetExample(datasetId: number, exampleId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: DatasetExampleUpdateRequest): Promise<DatasetExample> => {
      const response = await apiClient.put<DatasetExample>(
        `/evaluations/datasets/${datasetId}/examples/${exampleId}`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataset-examples', datasetId] });
      queryClient.invalidateQueries({ queryKey: ['dataset-example', datasetId, exampleId] });
    },
  });
}

export function useDeleteDatasetExample(datasetId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (exampleId: number): Promise<void> => {
      await apiClient.delete(`/evaluations/datasets/${datasetId}/examples/${exampleId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataset-examples', datasetId] });
      queryClient.invalidateQueries({ queryKey: ['dataset', datasetId] });
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
  });
}

export function useDeleteDatasetExamplesBatch(datasetId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (exampleIds: number[]): Promise<{ deleted_count: number }> => {
      const response = await apiClient.delete<{ deleted_count: number }>(
        `/evaluations/datasets/${datasetId}/examples/batch`,
        { data: { example_ids: exampleIds } }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataset-examples', datasetId] });
      queryClient.invalidateQueries({ queryKey: ['dataset', datasetId] });
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
  });
}

// ============================================================================
// Dataset Import/Export Hooks
// ============================================================================

export function useImportDataset(datasetId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      file,
      format,
    }: {
      file: File;
      format: 'csv' | 'json';
    }): Promise<{ imported_count: number }> => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('format', format);

      const response = await apiClient.post<{ imported_count: number }>(
        `/evaluations/datasets/${datasetId}/import`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataset-examples', datasetId] });
      queryClient.invalidateQueries({ queryKey: ['dataset', datasetId] });
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
  });
}

export function useExportDataset(datasetId: number) {
  return useMutation({
    mutationFn: async (format: 'csv' | 'json'): Promise<Blob> => {
      const response = await apiClient.post(
        `/evaluations/datasets/${datasetId}/export`,
        { format },
        { responseType: 'blob' }
      );
      return response.data;
    },
  });
}

// ============================================================================
// Evaluator Hooks
// ============================================================================

interface UseEvaluatorsParams {
  page?: number;
  pageSize?: number;
  category?: EvaluatorCategory;
  type?: EvaluatorType;
  includeBuiltin?: boolean;
}

export function useEvaluators(params: UseEvaluatorsParams = {}) {
  const { page = 1, pageSize = 50, category, type, includeBuiltin = true } = params;

  return useQuery({
    queryKey: ['evaluators', { page, pageSize, category, type, includeBuiltin }],
    queryFn: async (): Promise<EvaluatorListResponse> => {
      const searchParams = new URLSearchParams();
      searchParams.append('page', page.toString());
      searchParams.append('page_size', pageSize.toString());
      if (category) searchParams.append('category', category);
      if (type) searchParams.append('type', type);
      searchParams.append('include_builtin', includeBuiltin.toString());

      const response = await apiClient.get<EvaluatorListResponse>(
        `/evaluations/evaluators?${searchParams.toString()}`
      );
      return response.data;
    },
  });
}

export function useEvaluator(id: number | undefined) {
  return useQuery({
    queryKey: ['evaluator', id],
    queryFn: async (): Promise<Evaluator> => {
      const response = await apiClient.get<Evaluator>(`/evaluations/evaluators/${id}`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateEvaluator() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: EvaluatorCreateRequest): Promise<Evaluator> => {
      const response = await apiClient.post<Evaluator>('/evaluations/evaluators', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evaluators'] });
    },
  });
}

export function useUpdateEvaluator(id: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: EvaluatorUpdateRequest): Promise<Evaluator> => {
      const response = await apiClient.put<Evaluator>(`/evaluations/evaluators/${id}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evaluators'] });
      queryClient.invalidateQueries({ queryKey: ['evaluator', id] });
    },
  });
}

export function useDeleteEvaluator() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number): Promise<void> => {
      await apiClient.delete(`/evaluations/evaluators/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evaluators'] });
    },
  });
}

export function useCloneEvaluator() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      id,
      name,
    }: {
      id: number;
      name?: string;
    }): Promise<Evaluator> => {
      const response = await apiClient.post<Evaluator>(
        `/evaluations/evaluators/${id}/clone`,
        name ? { name } : {}
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evaluators'] });
    },
  });
}

export function useTestEvaluator(id: number) {
  return useMutation({
    mutationFn: async (data: EvaluatorTestRequest): Promise<EvaluatorTestResult> => {
      const response = await apiClient.post<EvaluatorTestResult>(
        `/evaluations/evaluators/${id}/test`,
        data
      );
      return response.data;
    },
  });
}

export function useSeedBuiltinEvaluators() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (): Promise<{ seeded_count: number }> => {
      const response = await apiClient.post<{ seeded_count: number }>(
        '/evaluations/evaluators/seed'
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evaluators'] });
    },
  });
}

// ============================================================================
// Evaluation Hooks (Reusable Config)
// ============================================================================

interface UseEvaluationsParams {
  page?: number;
  pageSize?: number;
  search?: string;
  datasetId?: number;
  isActive?: boolean;
}

export function useEvaluations(params: UseEvaluationsParams = {}) {
  const { page = 1, pageSize = 50, search, datasetId, isActive } = params;

  return useQuery({
    queryKey: ['evaluations', { page, pageSize, search, datasetId, isActive }],
    queryFn: async (): Promise<EvaluationListResponse> => {
      const searchParams = new URLSearchParams();
      searchParams.append('page', page.toString());
      searchParams.append('page_size', pageSize.toString());
      if (search) searchParams.append('search', search);
      if (datasetId) searchParams.append('dataset_id', datasetId.toString());
      if (isActive !== undefined) searchParams.append('is_active', isActive.toString());

      const response = await apiClient.get<EvaluationListResponse>(
        `/evaluations?${searchParams.toString()}`
      );
      return response.data;
    },
  });
}

export function useEvaluation(id: number | undefined) {
  return useQuery({
    queryKey: ['evaluation', id],
    queryFn: async (): Promise<EvaluationDetail> => {
      const response = await apiClient.get<EvaluationDetail>(`/evaluations/${id}`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateEvaluation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: EvaluationCreateRequest): Promise<Evaluation> => {
      const response = await apiClient.post<Evaluation>('/evaluations', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evaluations'] });
    },
  });
}

export function useUpdateEvaluation(id: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: EvaluationUpdateRequest): Promise<Evaluation> => {
      const response = await apiClient.put<Evaluation>(`/evaluations/${id}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evaluations'] });
      queryClient.invalidateQueries({ queryKey: ['evaluation', id] });
    },
  });
}

export function useDeleteEvaluation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number): Promise<void> => {
      await apiClient.delete(`/evaluations/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evaluations'] });
    },
  });
}

// ============================================================================
// Evaluation Run Hooks (Execution Instances)
// ============================================================================

interface UseEvaluationRunsParams {
  evaluationId: number;
  page?: number;
  pageSize?: number;
  status?: EvaluationStatus;
  /** Enable polling when any run is active (running/evaluating/pending) */
  pollingEnabled?: boolean;
}

export function useEvaluationRuns(params: UseEvaluationRunsParams) {
  const { evaluationId, page = 1, pageSize = 50, status, pollingEnabled = false } = params;

  return useQuery({
    queryKey: ['evaluation-runs', evaluationId, { page, pageSize, status }],
    queryFn: async (): Promise<EvaluationRunListResponse> => {
      const searchParams = new URLSearchParams();
      searchParams.append('page', page.toString());
      searchParams.append('page_size', pageSize.toString());
      if (status) searchParams.append('status', status);

      const response = await apiClient.get<EvaluationRunListResponse>(
        `/evaluations/${evaluationId}/runs?${searchParams.toString()}`
      );
      return response.data;
    },
    enabled: !!evaluationId,
    // Poll every 3 seconds when polling is enabled AND any run is active
    refetchInterval: (query) => {
      if (!pollingEnabled) return false;
      const data = query.state.data;
      if (!data) return false;
      // Check if any run is in an active state
      const hasActiveRun = data.runs.some(
        (r) => r.status === 'running' || r.status === 'evaluating' || r.status === 'pending'
      );
      return hasActiveRun ? 3000 : false;
    },
    // Keep previous data during refetch to prevent UI flicker
    placeholderData: (previousData) => previousData,
  });
}

// Get all runs across all evaluations (for global runs list)
interface UseAllEvaluationRunsParams {
  page?: number;
  pageSize?: number;
  agentId?: number;
  status?: EvaluationStatus;
}

export function useAllEvaluationRuns(params: UseAllEvaluationRunsParams = {}) {
  const { page = 1, pageSize = 50, agentId, status } = params;

  return useQuery({
    queryKey: ['all-evaluation-runs', { page, pageSize, agentId, status }],
    queryFn: async (): Promise<EvaluationRunListResponse> => {
      const searchParams = new URLSearchParams();
      searchParams.append('page', page.toString());
      searchParams.append('page_size', pageSize.toString());
      if (agentId) searchParams.append('agent_id', agentId.toString());
      if (status) searchParams.append('status', status);

      const response = await apiClient.get<EvaluationRunListResponse>(
        `/evaluations/runs?${searchParams.toString()}`
      );
      return response.data;
    },
  });
}

export function useEvaluationRun(evaluationId: number | undefined, runId: number | undefined) {
  return useQuery({
    queryKey: ['evaluation-run', evaluationId, runId],
    queryFn: async (): Promise<EvaluationRunDetail> => {
      const response = await apiClient.get<EvaluationRunDetail>(
        `/evaluations/${evaluationId}/runs/${runId}`
      );
      return response.data;
    },
    enabled: !!evaluationId && !!runId,
  });
}

export function useCreateEvaluationRun(evaluationId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: EvaluationRunCreateRequest): Promise<EvaluationRun> => {
      const response = await apiClient.post<EvaluationRun>(
        `/evaluations/${evaluationId}/runs`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evaluation-runs', evaluationId] });
      queryClient.invalidateQueries({ queryKey: ['all-evaluation-runs'] });
      queryClient.invalidateQueries({ queryKey: ['evaluation', evaluationId] });
    },
  });
}

export function useExecuteEvaluationRun(evaluationId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (runId: number): Promise<EvaluationRun> => {
      const response = await apiClient.post<EvaluationRun>(
        `/evaluations/${evaluationId}/runs/${runId}/execute`
      );
      return response.data;
    },
    onSuccess: (data, runId) => {
      // Immediately update the cache with the "running" status from the response
      queryClient.setQueryData(
        ['evaluation-run', evaluationId, runId],
        (old: EvaluationRunDetail | undefined) => {
          if (old) {
            return { ...old, status: data.status, started_at: data.started_at };
          }
          return data as EvaluationRunDetail;
        }
      );
      queryClient.invalidateQueries({ queryKey: ['evaluation-runs', evaluationId] });
      queryClient.invalidateQueries({ queryKey: ['all-evaluation-runs'] });
    },
  });
}

export function useCancelEvaluationRun(evaluationId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (runId: number): Promise<EvaluationRun> => {
      const response = await apiClient.post<EvaluationRun>(
        `/evaluations/${evaluationId}/runs/${runId}/cancel`
      );
      return response.data;
    },
    onSuccess: (_, runId) => {
      queryClient.invalidateQueries({ queryKey: ['evaluation-runs', evaluationId] });
      queryClient.invalidateQueries({ queryKey: ['evaluation-run', evaluationId, runId] });
      queryClient.invalidateQueries({ queryKey: ['all-evaluation-runs'] });
    },
  });
}

export function useDeleteEvaluationRun(evaluationId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (runId: number): Promise<void> => {
      await apiClient.delete(`/evaluations/${evaluationId}/runs/${runId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evaluation-runs', evaluationId] });
      queryClient.invalidateQueries({ queryKey: ['all-evaluation-runs'] });
      queryClient.invalidateQueries({ queryKey: ['evaluation', evaluationId] });
    },
  });
}

// ============================================================================
// Evaluation Results Hooks
// ============================================================================

interface UseEvaluationResultsParams {
  evaluationId: number;
  runId: number;
  page?: number;
  pageSize?: number;
  passed?: boolean;
  includeScores?: boolean;
}

export function useEvaluationResults(params: UseEvaluationResultsParams) {
  const { evaluationId, runId, page = 1, pageSize = 50, passed, includeScores = false } = params;

  return useQuery({
    queryKey: ['evaluation-results', evaluationId, runId, { page, pageSize, passed, includeScores }],
    queryFn: async (): Promise<EvaluationResultListResponse> => {
      const searchParams = new URLSearchParams();
      searchParams.append('page', page.toString());
      searchParams.append('page_size', pageSize.toString());
      if (passed !== undefined) searchParams.append('passed', passed.toString());
      if (includeScores) searchParams.append('include_scores', 'true');

      const response = await apiClient.get<EvaluationResultListResponse>(
        `/evaluations/${evaluationId}/runs/${runId}/results?${searchParams.toString()}`
      );
      return response.data;
    },
    enabled: !!evaluationId && !!runId,
  });
}

export function useEvaluationResult(
  evaluationId: number | undefined,
  runId: number | undefined,
  resultId: number | undefined
) {
  return useQuery({
    queryKey: ['evaluation-result', evaluationId, runId, resultId],
    queryFn: async (): Promise<EvaluationResultDetail> => {
      const response = await apiClient.get<EvaluationResultDetail>(
        `/evaluations/${evaluationId}/runs/${runId}/results/${resultId}`
      );
      return response.data;
    },
    enabled: !!evaluationId && !!runId && !!resultId,
  });
}

// ============================================================================
// Comparison Hooks
// ============================================================================

export function useCompareRuns(runIds: number[]) {
  return useQuery({
    queryKey: ['compare-runs', runIds],
    queryFn: async (): Promise<RunComparisonResponse> => {
      const response = await apiClient.get<RunComparisonResponse>(
        `/evaluations/compare?run_ids=${runIds.join(',')}`
      );
      return response.data;
    },
    enabled: runIds.length >= 2,
  });
}

// ============================================================================
// Polling Hook for Running Evaluations
// ============================================================================

export function useEvaluationRunPolling(
  evaluationId: number | undefined,
  runId: number | undefined,
  enabled: boolean = true
) {
  return useQuery({
    queryKey: ['evaluation-run', evaluationId, runId],
    queryFn: async (): Promise<EvaluationRunDetail> => {
      const response = await apiClient.get<EvaluationRunDetail>(
        `/evaluations/${evaluationId}/runs/${runId}`
      );
      return response.data;
    },
    enabled: !!evaluationId && !!runId && enabled,
    refetchInterval: (query) => {
      const data = query.state.data;
      // Poll every 2 seconds while running or evaluating
      if (data && (data.status === 'pending' || data.status === 'running' || data.status === 'evaluating')) {
        return 2000;
      }
      return false;
    },
  });
}
