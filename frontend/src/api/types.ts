// Auth types
export interface User {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

// Agent types
// Legacy type - kept for backward compatibility
export type AgentType = 'ReAct' | 'Plan-and-Execute' | 'Conversational' | 'Custom';

// Agent Type Config types (new entity)
export type ExecutionStrategy = 'react' | 'plan_and_execute' | 'conversational';
export type StrategyType = 'builtin' | 'custom_code';

export interface DefaultLLMConfig {
  provider?: string;
  model?: string;
  temperature?: number;
  max_tokens?: number;
}

export interface DefaultMemoryConfig {
  type?: string;
  context_window?: number;
  retrieval_strategy?: string;
}

export interface RecommendedToolInfo {
  id: number;
  name: string;
  category: string;
}

export interface AgentTypeConfig {
  id: number;
  user_id: number | null;
  name: string;
  description: string | null;
  icon: string | null;
  execution_strategy: ExecutionStrategy;
  system_prompt_template: string | null;
  default_llm_config: DefaultLLMConfig;
  default_memory_config: DefaultMemoryConfig;
  max_iterations: number;
  strategy_type: StrategyType;
  custom_strategy_code: string | null;
  code_template_version: number;
  is_builtin: boolean;
  is_active: boolean;
  recommended_tools: RecommendedToolInfo[];
  created_at: string;
  updated_at: string | null;
}

export interface AgentTypeConfigCreateRequest {
  name: string;
  description?: string;
  icon?: string;
  execution_strategy?: ExecutionStrategy;
  system_prompt_template?: string;
  default_llm_config?: DefaultLLMConfig;
  default_memory_config?: DefaultMemoryConfig;
  max_iterations?: number;
  strategy_type?: StrategyType;
  custom_strategy_code?: string;
  code_template_version?: number;
  recommended_tool_ids?: number[];
}

export interface AgentTypeConfigUpdateRequest {
  name?: string;
  description?: string;
  icon?: string;
  execution_strategy?: ExecutionStrategy;
  system_prompt_template?: string;
  default_llm_config?: DefaultLLMConfig;
  default_memory_config?: DefaultMemoryConfig;
  max_iterations?: number;
  strategy_type?: StrategyType;
  custom_strategy_code?: string;
  code_template_version?: number;
  recommended_tool_ids?: number[];
  is_active?: boolean;
}

export interface AgentTypeConfigListResponse {
  agent_types: AgentTypeConfig[];
  total: number;
  page: number;
  page_size: number;
}

// Compact agent type config embedded in agent responses
export interface AgentTypeConfigCompact {
  id: number;
  name: string;
  description: string | null;
  icon: string | null;
  execution_strategy: ExecutionStrategy;
  strategy_type: StrategyType;
  is_builtin: boolean;
}

export interface Agent {
  id: number;
  user_id: number | null;
  name: string;
  description: string | null;
  agent_type_id: number;
  agent_type_config: AgentTypeConfigCompact | null;
  tags: string[];
  is_active: boolean;
  is_builtin: boolean;
  current_version_id: number | null;
  created_at: string;
  updated_at: string | null;
}

export interface LLMConfig {
  provider: string;
  provider_id: number;
  model: string;
  temperature: number;
  max_tokens: number;
  stop_sequences?: string[];
}

export interface ReflectionConfig {
  enabled: boolean;
  depth: number;
  iteration_limit: number;
}

export interface MemoryConfig {
  type: string;
  context_window: number;
  retrieval_strategy?: string;
}

export interface AgentConfig {
  llm_config: LLMConfig;
  reflection_config?: ReflectionConfig;
  memory_config?: MemoryConfig;
  tool_ids: number[];
  prompt_id: number | null;
  prompt_variables?: Record<string, string>;
  system_prompt: string | null;
  timeout_seconds?: number;
}

export interface AgentVersion {
  id: number;
  agent_id: number;
  version_number: number;
  config: AgentConfig;
  created_at: string;
  created_by: number;
}

export interface AgentDetail extends Agent {
  current_version: AgentVersion | null;
}

export interface AgentCreateRequest {
  name: string;
  description?: string;
  agent_type_id: number;
  tags?: string[];
  config: AgentConfig;
}

export interface AgentUpdateRequest {
  name?: string;
  description?: string;
  agent_type_id?: number;
  tags?: string[];
  config?: AgentConfig;
}

// Attachment type for message context
export interface MessageAttachment {
  name: string;
  type: 'text' | 'image' | 'code' | 'other';
  mimeType: string;
  content?: string; // Text/code content or base64 for images
}

// Invoke types
export interface InvokeRequest {
  message: string;
  session_id?: number;
  config_override?: Partial<AgentConfig>;
  timeout_seconds?: number;
  attachments?: MessageAttachment[];
}

export interface TokenUsage {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
}

export interface InvokeResponse {
  success: boolean;
  output: string | null;
  content_blocks?: ContentBlock[] | null;  // Multimodal content blocks
  error: string | null;
  error_type: string | null;
  session_id: number;
  token_usage: TokenUsage;
  latency_ms: number;
  steps: TraceStep[];
}

// Tool types
export type ToolType = 'builtin' | 'custom';
export type ToolCategory = 'search' | 'calculator' | 'filesystem' | 'api' | 'database' | 'retrieval' | 'python' | 'other';

export interface Tool {
  id: number;
  user_id: number | null;
  name: string;
  description: string;
  tool_type: ToolType;
  category: ToolCategory;
  langchain_class: string | null;
  function_code: string | null;
  input_schema: Record<string, unknown> | null;
  output_schema: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
}

export interface ToolCreateRequest {
  name: string;
  description: string;
  category: ToolCategory;
  function_code: string;
  input_schema?: Record<string, unknown>;
  output_schema?: Record<string, unknown>;
}

// Prompt types
export type PromptUseCase = 'research' | 'coding' | 'analysis' | 'writing' | 'conversation' | 'planning' | 'other';
export type MessageType = 'system' | 'user' | 'assistant';

export interface Prompt {
  id: number;
  user_id: number;
  name: string;
  description: string | null;
  use_case: PromptUseCase;
  current_version_id: number | null;
  tags: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface PromptVersion {
  id: number;
  prompt_id: number;
  version_number: number;
  template: string;
  variables: string[];
  message_type: MessageType;
  is_active: boolean;
  usage_count: number;
  created_by: number | null;
  created_at: string;
}

export interface PromptDetail extends Prompt {
  current_version: PromptVersion | null;
}

// Multimodal Content Block types (for agent outputs)
export type ContentBlockType = 'text' | 'image' | 'audio' | 'video' | 'file';
export type MediaFileType = 'image' | 'audio' | 'video' | 'file';

export interface ContentBlock {
  type: ContentBlockType;
  text?: string;           // For text blocks
  url?: string;            // API URL to fetch the media file
  file_name?: string;      // Display name
  mime_type?: string;      // MIME type (e.g., 'image/png')
  file_size?: number;      // File size in bytes
  metadata?: {
    width?: number;        // Image/video width
    height?: number;       // Image/video height
    duration?: number;     // Audio/video duration in seconds
    prompt?: string;       // Generation prompt (for AI-generated media)
    revised_prompt?: string; // DALL-E revised prompt
    [key: string]: unknown;
  };
}

export interface MediaFile {
  id: number;
  session_id: number;
  message_id?: number;
  file_name: string;
  file_path: string;
  media_type: MediaFileType;
  mime_type: string;
  file_size_bytes?: number;
  url: string;
  file_metadata: Record<string, unknown>;
  created_at: string;
}

// Session types
export type SessionStatus = 'pending' | 'running' | 'completed' | 'failed';
export type MessageRole = 'user' | 'assistant' | 'system' | 'tool';
export type TraceStepType = 'thought' | 'tool_call' | 'tool_result' | 'reflection' | 'error' | 'observation' | 'final_answer';

export interface Session {
  id: number;
  user_id: number;
  agent_id: number | null;
  agent_version_id: number | null;
  title: string | null;
  status: SessionStatus;
  started_at: string;
  completed_at: string | null;
  total_latency_ms: number | null;
  token_usage_input: number;
  token_usage_output: number;
  total_cost: number | null;
  error_message: string | null;
  error_type: string | null;
}

export interface Message {
  id: number;
  session_id: number;
  role: MessageRole;
  content: string;
  content_blocks?: ContentBlock[] | null;  // Multimodal content blocks
  sequence_number: number;
  tool_calls: Record<string, unknown>[] | null;
  tool_call_id: string | null;
  created_at: string;
}

export interface TraceStep {
  id: number;
  session_id: number;
  step_number: number;
  step_type: TraceStepType;
  content: string | null;
  tool_name: string | null;
  tool_input: Record<string, unknown> | null;
  tool_output: Record<string, unknown> | null;
  latency_ms: number | null;
  created_at: string;
}

export interface SessionDetail extends Session {
  messages: Message[];
  trace_steps: TraceStep[];
}

// LLM Provider types
export type LLMProviderType = 'openai' | 'anthropic' | 'google' | 'azure_openai' | 'ollama' | 'llamacpp';

export interface LLMProvider {
  id: number;
  user_id: number;
  name: string;
  provider_type: LLMProviderType;
  is_active: boolean;
  config: Record<string, unknown>;
  last_used_at: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface LLMProviderCreateRequest {
  name: string;
  provider_type: LLMProviderType;
  api_key: string;
  config?: Record<string, unknown>;
}

// Custom Model Configuration types
export interface ParameterConstraints {
  min: number;
  max: number;
  default: number;
}

export interface CustomModelConfig {
  id: string;                    // Model ID sent to API (e.g., "gpt-4o-mini")
  name: string;                  // Display name in UI
  usesMaxCompletionTokens?: boolean;  // For OpenAI newer models
  maxContextTokens?: number;     // Context window size
  parameters?: {
    temperature?: ParameterConstraints;
    max_tokens?: ParameterConstraints;
    top_p?: ParameterConstraints;
    top_k?: ParameterConstraints;
    frequency_penalty?: ParameterConstraints;
    presence_penalty?: ParameterConstraints;
  };
  notes?: string;
}

export interface LLMProviderConfig {
  base_url?: string;
  custom_models?: CustomModelConfig[];
  [key: string]: unknown;        // Allow other provider-specific config
}

// Pagination
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface AgentListResponse {
  agents: Agent[];
  total: number;
  page: number;
  page_size: number;
}

export interface ToolListResponse {
  tools: Tool[];
  total: number;
  page: number;
  page_size: number;
}

export interface PromptListResponse {
  prompts: Prompt[];
  total: number;
  page: number;
  page_size: number;
}

export interface SessionListResponse {
  sessions: Session[];
  total: number;
  page: number;
  page_size: number;
}

// Statistics
export interface SessionStatistics {
  total_sessions: number;
  completed_sessions: number;
  failed_sessions: number;
  average_latency_ms: number | null;
  total_tokens_used: number;
  total_cost: number;
  success_rate: number;
}

// MCP Server types
export type MCPTransportType = 'stdio' | 'sse' | 'streamable_http';

export interface MCPStdioConfig {
  command: string;
  args?: string[];
}

export interface MCPHttpConfig {
  url: string;
  headers?: Record<string, string>;
}

export interface MCPServer {
  id: number;
  user_id: number;
  name: string;
  description: string | null;
  transport_type: MCPTransportType;
  stdio_config: MCPStdioConfig | null;
  http_config: MCPHttpConfig | null;
  config: Record<string, unknown>;
  has_env_vars: boolean;
  cached_tools_count: number;
  tools_last_discovered_at: string | null;
  is_active: boolean;
  last_connected_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface MCPServerCreateRequest {
  name: string;
  description?: string;
  transport_type: MCPTransportType;
  stdio_config?: MCPStdioConfig;
  http_config?: MCPHttpConfig;
  env_vars?: Record<string, string>;
  config?: Record<string, unknown>;
}

export interface MCPServerUpdateRequest {
  name?: string;
  description?: string;
  stdio_config?: MCPStdioConfig;
  http_config?: MCPHttpConfig;
  config?: Record<string, unknown>;
  env_vars?: Record<string, string>;
  is_active?: boolean;
}

export interface MCPServerListResponse {
  servers: MCPServer[];
  total: number;
  page: number;
  page_size: number;
}

export interface MCPTool {
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
}

export interface MCPServerToolsResponse {
  server_id: number;
  server_name: string;
  tools: MCPTool[];
  cached: boolean;
  last_discovered_at: string | null;
}

export interface MCPServerTestResponse {
  success: boolean;
  message: string;
  tools_count: number;
  latency_ms: number | null;
  tools?: MCPTool[];  // Optionally includes discovered tools
}

// Strategy Validation types
export interface StrategyValidateRequest {
  code: string;
}

export interface StrategyValidateResponse {
  is_valid: boolean;
  error: string | null;
  warnings: string[];
}

export interface StrategyTestRequest {
  code: string;
  input_message?: string;
  config?: Record<string, unknown>;
}

export interface StrategyTestResponse {
  success: boolean;
  output: string | null;
  error: string | null;
  error_type: string | null;
  execution_time_ms: number;
  steps: Record<string, unknown>[];
  tokens_input: number;
  tokens_output: number;
}

export interface StrategyTemplateInfo {
  name: string;
  description: string;
}

export interface StrategyTemplatesResponse {
  templates: StrategyTemplateInfo[];
}

export interface StrategyTemplateResponse {
  name: string;
  code: string;
}

// ============================================================================
// Span Types (Enhanced Tracing System - Phase 4)
// ============================================================================

export type SpanType =
  | 'agent'      // Top-level agent execution
  | 'chain'      // Chain/sequence execution
  | 'llm'        // LLM API call
  | 'tool'       // Tool invocation
  | 'retriever'  // Document retrieval
  | 'embedding'  // Embedding generation
  | 'parser'     // Output parsing
  | 'prompt'     // Prompt formatting
  | 'memory'     // Memory read/write
  | 'thought'    // Agent reasoning
  | 'error';     // Error occurrence

export type SpanStatus = 'running' | 'success' | 'error';

export interface Span {
  id: number;
  session_id: number;
  trace_id: string;
  parent_span_id: number | null;
  span_type: SpanType;
  name: string;
  span_order: number;
  depth: number;

  // Timing
  started_at: string;
  ended_at: string | null;
  duration_ms: number | null;

  // Status
  status: SpanStatus;
  status_message: string | null;

  // Data
  input: Record<string, unknown> | null;
  output: Record<string, unknown> | null;

  // LLM-specific
  model_name: string | null;
  model_provider: string | null;
  model_parameters: Record<string, unknown> | null;
  tokens_input: number | null;
  tokens_output: number | null;
  tokens_total: number | null;
  cost_usd: number | null;

  // Tool-specific
  tool_name: string | null;

  // Error details
  error_type: string | null;
  error_message: string | null;
  error_stack: string | null;

  // Metadata
  tags: string[] | null;
  meta: Record<string, unknown>;

  created_at: string;
}

export interface SpanTreeNode {
  id: number;
  span_type: SpanType;
  name: string;
  status: SpanStatus;
  started_at: string;
  ended_at: string | null;
  duration_ms: number | null;
  depth: number;

  // Quick stats for tree view
  tokens_total: number | null;
  cost_usd: number | null;
  tool_name: string | null;
  error_message: string | null;

  // Children (recursive)
  children: SpanTreeNode[];
}

export interface SpanStats {
  total_spans: number;
  total_duration_ms: number | null;
  total_tokens: number;
  total_tokens_input: number;
  total_tokens_output: number;
  total_cost_usd: number;
  span_count_by_type: Record<string, number>;
  span_count_by_status: Record<string, number>;
  error_count: number;
  average_duration_ms: number | null;
}

export interface SpanTreeResponse {
  trace_id: string;
  root_span: SpanTreeNode | null;
  stats: SpanStats;
}

export interface SpanListResponse {
  spans: Span[];
  total: number;
  page: number;
  page_size: number;
}

// ============================================================================
// Evaluation System Types (Phase 5)
// ============================================================================

// Enums
export type EvaluatorCategory = 'output' | 'run_metadata';

export type EvaluatorType =
  // Output evaluators
  | 'exact_match'
  | 'contains'
  | 'regex_match'
  | 'json_match'
  | 'semantic_similarity'
  | 'llm_judge'
  | 'custom_code'
  // Run metadata evaluators
  | 'token_efficiency'
  | 'latency_threshold'
  | 'cost_threshold'
  | 'chain_length'
  | 'tool_call_success_rate'
  | 'tool_selection'
  | 'error_rate'
  | 'span_count'
  | 'custom_metadata';

export type EvaluationStatus = 'pending' | 'running' | 'evaluating' | 'completed' | 'failed' | 'cancelled' | 'error';

export type EvaluationScoreStatus = 'pending' | 'running' | 'completed' | 'failed';

export type DatasetSchemaType = 'text' | 'structured';

// Dataset Types
export interface EvaluationDataset {
  id: number;
  user_id: number;
  name: string;
  description: string | null;
  schema_type: DatasetSchemaType;
  input_schema: Record<string, unknown> | null;
  output_schema: Record<string, unknown> | null;
  tags: string[] | null;
  example_count: number;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface DatasetExample {
  id: number;
  dataset_id: number;
  name: string | null;
  input: unknown;
  expected_output: unknown;
  context: unknown | null;
  metadata: Record<string, unknown> | null;
  tags: string[] | null;
  created_at: string;
  updated_at: string | null;
}

export interface DatasetCreateRequest {
  name: string;
  description?: string;
  schema_type?: DatasetSchemaType;
  input_schema?: Record<string, unknown>;
  output_schema?: Record<string, unknown>;
  tags?: string[];
}

export interface DatasetUpdateRequest {
  name?: string;
  description?: string;
  schema_type?: DatasetSchemaType;
  input_schema?: Record<string, unknown>;
  output_schema?: Record<string, unknown>;
  tags?: string[];
  is_active?: boolean;
}

export interface DatasetExampleCreateRequest {
  name?: string;
  input: unknown;
  expected_output: unknown;
  context?: unknown;
  metadata?: Record<string, unknown>;
  tags?: string[];
}

export interface DatasetExampleUpdateRequest {
  name?: string;
  input?: unknown;
  expected_output?: unknown;
  context?: unknown;
  metadata?: Record<string, unknown>;
  tags?: string[];
}

export interface DatasetListResponse {
  datasets: EvaluationDataset[];
  total: number;
  page: number;
  page_size: number;
}

export interface DatasetExampleListResponse {
  examples: DatasetExample[];
  total: number;
  page: number;
  page_size: number;
}

// Evaluator Types
export interface Evaluator {
  id: number;
  user_id: number | null;
  name: string;
  type: EvaluatorType;
  category: EvaluatorCategory;
  description: string | null;
  config: Record<string, unknown>;
  is_builtin: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface EvaluatorCreateRequest {
  name: string;
  type: EvaluatorType;
  category: EvaluatorCategory;
  description?: string;
  config?: Record<string, unknown>;
}

export interface EvaluatorUpdateRequest {
  name?: string;
  description?: string;
  config?: Record<string, unknown>;
}

export interface EvaluatorListResponse {
  evaluators: Evaluator[];
  total: number;
  page: number;
  page_size: number;
}

export interface EvaluatorTestRequest {
  input: string;
  expected_output: string;
  actual_output: string;
  run_metadata?: Record<string, unknown>;
}

export interface EvaluatorTestResult {
  passed: boolean;
  score: number;
  message: string | null;
  details: Record<string, unknown> | null;
}

// Evaluation Config (reusable configuration)
export interface EvaluationConfig {
  concurrency?: number;
  timeout_per_example_ms?: number;
  retry_failed?: boolean;
  max_retries?: number;
  sample_size?: number;
  sample_seed?: number;
}

export interface Evaluation {
  id: number;
  user_id: number;
  name: string;
  description: string | null;
  dataset_id: number;
  config: EvaluationConfig;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
  // Computed/nested fields
  dataset_name: string | null;
  evaluator_count: number;
  run_count: number;
}

export interface EvaluationDetail extends Evaluation {
  evaluators: Evaluator[];
  dataset: EvaluationDataset | null;
}

export interface EvaluationCreateRequest {
  name: string;
  description?: string;
  dataset_id: number;
  evaluator_ids: number[];
  config?: EvaluationConfig;
}

export interface EvaluationUpdateRequest {
  name?: string;
  description?: string;
  evaluator_ids?: number[];
  config?: EvaluationConfig;
}

export interface EvaluationListResponse {
  evaluations: Evaluation[];
  total: number;
  page: number;
  page_size: number;
}

// Evaluation Run Types (execution instance within an Evaluation)
export interface EvaluationRun {
  id: number;
  user_id: number;
  evaluation_id: number;
  name: string | null;
  agent_id: number;
  agent_name: string | null;
  agent_version_id: number | null;
  llm_provider_id: number | null;
  status: EvaluationStatus;
  progress: number;
  metrics: Record<string, unknown> | null;
  total_examples: number;
  completed_examples: number;
  passed_examples: number;
  failed_examples: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  // Computed/nested fields
  evaluation_name: string | null;
  dataset_name: string | null;
}

export interface EvaluationRunDetail extends EvaluationRun {
  evaluation: Evaluation | null;
  evaluators: Evaluator[];
}

export interface EvaluationRunCreateRequest {
  agent_id: number;
  agent_version_id?: number;
  name?: string;
  llm_provider_id?: number;
}

// Evaluator types that require an LLM provider at run time
export const LLM_EVALUATOR_TYPES: EvaluatorType[] = ['llm_judge', 'semantic_similarity'];

export interface EvaluationRunListResponse {
  runs: EvaluationRun[];
  total: number;
  page: number;
  page_size: number;
}

// Evaluation Result Types
export interface EvaluationScore {
  id: number;
  result_id: number;
  evaluator_id: number;
  evaluator_name: string;
  passed: boolean | null;
  score: number | null;
  message: string | null;
  details: Record<string, unknown> | null;
  score_metadata: Record<string, unknown> | null;
  status: EvaluationScoreStatus;
  session_id: number | null;
}

export interface EvaluationResult {
  id: number;
  run_id: number;
  example_id: number;
  example_name: string | null;
  // These fields match the backend response schema
  example_input: unknown;
  example_expected_output: unknown;
  agent_output: unknown;
  // Computed fields (can be null if scores not yet computed)
  passed: boolean | null;
  aggregate_score: number | null;
  run_metadata: Record<string, unknown> | null;
  latency_ms: number | null;
  token_usage_input: number;
  token_usage_output: number;
  cost: number | null;
  status: EvaluationStatus;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
  // Optional scores (included when requested via include_scores=true)
  scores?: EvaluationScore[];
}

export interface EvaluationResultDetail extends EvaluationResult {
  scores: EvaluationScore[];
}

export interface EvaluationResultListResponse {
  results: EvaluationResult[];
  total: number;
  page: number;
  page_size: number;
}

// Run Comparison Types
export interface RunComparisonMetrics {
  run_id: number;
  run_name: string;
  agent_name: string | null;
  agent_version_id: number | null;
  status: EvaluationStatus;
  pass_rate: number;
  avg_score: number;
  total_examples: number;
  completed_at: string | null;
}

export interface RunComparisonResponse {
  runs: RunComparisonMetrics[];
  metrics_comparison: Record<number, Record<string, unknown>>;
}
