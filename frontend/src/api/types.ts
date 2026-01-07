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

// Invoke types
export interface InvokeRequest {
  message: string;
  session_id?: number;
  config_override?: Partial<AgentConfig>;
  timeout_seconds?: number;
}

export interface TokenUsage {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
}

export interface InvokeResponse {
  success: boolean;
  output: string | null;
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
export type PromptUseCase = 'research' | 'coding' | 'analysis' | 'writing' | 'general' | 'custom';
export type MessageType = 'system' | 'user' | 'assistant';

export interface Prompt {
  id: number;
  user_id: number;
  name: string;
  description: string | null;
  use_case: PromptUseCase;
  message_type: MessageType;
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
  content: string;
  variables: string[];
  is_active: boolean;
  usage_count: number;
  created_at: string;
}

export interface PromptDetail extends Prompt {
  current_version: PromptVersion | null;
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
