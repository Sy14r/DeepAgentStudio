"""Pydantic schemas for evaluation system"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, ConfigDict


# Enums
class EvaluatorCategory(str, Enum):
    OUTPUT = "output"
    RUN_METADATA = "run_metadata"


class EvaluatorType(str, Enum):
    # Output evaluators
    EXACT_MATCH = "exact_match"
    CONTAINS = "contains"
    REGEX_MATCH = "regex_match"
    JSON_MATCH = "json_match"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    LLM_JUDGE = "llm_judge"
    CUSTOM_CODE = "custom_code"
    # Run metadata evaluators
    TOKEN_EFFICIENCY = "token_efficiency"
    LATENCY_THRESHOLD = "latency_threshold"
    COST_THRESHOLD = "cost_threshold"
    CHAIN_LENGTH = "chain_length"
    TOOL_CALL_SUCCESS_RATE = "tool_call_success_rate"
    TOOL_SELECTION = "tool_selection"
    ERROR_RATE = "error_rate"
    SPAN_COUNT = "span_count"
    CUSTOM_METADATA = "custom_metadata"


class EvaluationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    EVALUATING = "evaluating"  # Agent execution done, evaluators running
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ERROR = "error"


class EvaluationScoreStatus(str, Enum):
    """Status of individual evaluator score computation"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DatasetSchemaType(str, Enum):
    TEXT = "text"
    STRUCTURED = "structured"


# ===== Dataset Schemas =====

class DatasetExampleBase(BaseModel):
    """Base schema for dataset examples"""
    name: Optional[str] = None
    input: Any  # Can be string or structured JSON
    expected_output: Any  # Can be string or structured JSON
    context: Optional[Any] = None
    metadata: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None


class DatasetExampleCreate(DatasetExampleBase):
    """Schema for creating a dataset example"""
    pass


class DatasetExampleUpdate(BaseModel):
    """Schema for updating a dataset example"""
    name: Optional[str] = None
    input: Optional[Any] = None
    expected_output: Optional[Any] = None
    context: Optional[Any] = None
    metadata: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None


class DatasetExampleResponse(BaseModel):
    """Schema for dataset example responses"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    dataset_id: int
    name: Optional[str] = None
    input: Any
    expected_output: Any
    context: Optional[Any] = None
    metadata: Optional[dict[str, Any]] = Field(default=None, validation_alias="example_metadata")
    tags: Optional[list[str]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class DatasetExampleBatchCreate(BaseModel):
    """Schema for batch creating examples"""
    examples: list[DatasetExampleCreate]


class EvaluationDatasetBase(BaseModel):
    """Base schema for evaluation datasets"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    schema_type: DatasetSchemaType = DatasetSchemaType.TEXT
    input_schema: Optional[dict[str, Any]] = None
    output_schema: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None


class EvaluationDatasetCreate(EvaluationDatasetBase):
    """Schema for creating an evaluation dataset"""
    pass


class EvaluationDatasetUpdate(BaseModel):
    """Schema for updating an evaluation dataset"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    schema_type: Optional[DatasetSchemaType] = None
    input_schema: Optional[dict[str, Any]] = None
    output_schema: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None


class EvaluationDatasetResponse(EvaluationDatasetBase):
    """Schema for evaluation dataset responses"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    example_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class EvaluationDatasetDetailResponse(EvaluationDatasetResponse):
    """Schema for detailed dataset response with examples"""
    examples: list[DatasetExampleResponse] = []


class EvaluationDatasetListResponse(BaseModel):
    """Schema for paginated dataset list"""
    datasets: list[EvaluationDatasetResponse]
    total: int
    page: int
    page_size: int


# ===== Evaluator Schemas =====

class EvaluatorBase(BaseModel):
    """Base schema for evaluators"""
    name: str = Field(..., min_length=1, max_length=255)
    type: EvaluatorType
    category: EvaluatorCategory = EvaluatorCategory.OUTPUT
    description: Optional[str] = None
    config: dict[str, Any] = Field(default_factory=dict)


class EvaluatorCreate(EvaluatorBase):
    """Schema for creating an evaluator"""
    pass


class EvaluatorUpdate(BaseModel):
    """Schema for updating an evaluator"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    config: Optional[dict[str, Any]] = None


class EvaluatorResponse(EvaluatorBase):
    """Schema for evaluator responses"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int] = None
    is_builtin: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class EvaluatorListResponse(BaseModel):
    """Schema for evaluator list"""
    evaluators: list[EvaluatorResponse]
    total: int


class EvaluatorTestRequest(BaseModel):
    """Schema for testing an evaluator"""
    input: str
    expected_output: str
    actual_output: str
    run_metadata: Optional[dict[str, Any]] = None


class EvaluatorTestResponse(BaseModel):
    """Schema for evaluator test results"""
    score: float
    passed: bool
    feedback: str
    metadata: Optional[dict[str, Any]] = None
    error: Optional[str] = None


# ===== Evaluation Schemas (Reusable Config) =====

class EvaluationConfig(BaseModel):
    """Configuration for an evaluation"""
    concurrency: int = Field(default=3, ge=1, le=10)
    timeout_per_example_ms: int = Field(default=60000, ge=1000, le=600000)
    retry_failed: bool = False
    max_retries: int = Field(default=2, ge=0, le=5)
    sample_size: Optional[int] = Field(None, ge=1)
    sample_seed: Optional[int] = None


class EvaluationCreate(BaseModel):
    """Schema for creating an evaluation configuration"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    dataset_id: int
    evaluator_ids: list[int] = Field(..., min_length=1)
    config: EvaluationConfig = Field(default_factory=EvaluationConfig)


class EvaluationUpdate(BaseModel):
    """Schema for updating an evaluation configuration"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    evaluator_ids: Optional[list[int]] = Field(None, min_length=1)
    config: Optional[EvaluationConfig] = None


class EvaluationResponse(BaseModel):
    """Schema for evaluation responses"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    description: Optional[str] = None
    dataset_id: int
    config: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Nested info (populated separately)
    dataset_name: Optional[str] = None
    evaluator_count: int = 0
    run_count: int = 0


class EvaluationDetailResponse(EvaluationResponse):
    """Schema for detailed evaluation response with evaluators and recent runs"""
    evaluators: list[EvaluatorResponse] = []
    dataset: Optional[EvaluationDatasetResponse] = None


class EvaluationListResponse(BaseModel):
    """Schema for paginated evaluation list"""
    evaluations: list[EvaluationResponse]
    total: int
    page: int
    page_size: int


# ===== Evaluation Run Schemas =====

class EvaluationRunCreate(BaseModel):
    """Schema for creating an evaluation run (within an evaluation)"""
    agent_id: int
    agent_version_id: Optional[int] = None
    name: Optional[str] = Field(None, max_length=255)  # Optional run-specific name
    llm_provider_id: Optional[int] = None  # LLM provider for LLM-based evaluators


class EvaluationRunResponse(BaseModel):
    """Schema for evaluation run responses"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    evaluation_id: int
    name: Optional[str] = None
    agent_id: int
    agent_version_id: Optional[int] = None
    llm_provider_id: Optional[int] = None
    status: EvaluationStatus
    progress: int
    total_examples: int
    completed_examples: int
    passed_examples: int = 0  # Computed from metrics
    failed_examples: int = 0  # Computed from metrics
    metrics: Optional[dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    # Nested info from evaluation (populated separately)
    evaluation_name: Optional[str] = None
    dataset_name: Optional[str] = None
    agent_name: Optional[str] = None


class EvaluationRunDetailResponse(EvaluationRunResponse):
    """Schema for detailed run response with evaluation info"""
    evaluation: Optional[EvaluationResponse] = None
    evaluators: list[EvaluatorResponse] = []  # From evaluation


class EvaluationRunListResponse(BaseModel):
    """Schema for paginated run list"""
    runs: list[EvaluationRunResponse]
    total: int
    page: int
    page_size: int


# ===== Evaluation Result Schemas =====

class EvaluationScoreResponse(BaseModel):
    """Schema for individual evaluator score"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    evaluator_id: int
    evaluator_name: Optional[str] = None
    evaluator_type: Optional[str] = None
    evaluator_category: Optional[str] = None
    score: Optional[Decimal] = None
    passed: Optional[bool] = None
    feedback: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    status: EvaluationScoreStatus = EvaluationScoreStatus.COMPLETED
    session_id: Optional[int] = None
    created_at: datetime


class EvaluationResultResponse(BaseModel):
    """Schema for evaluation result responses"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    example_id: int
    session_id: Optional[int] = None
    agent_output: Optional[Any] = None
    run_metadata: Optional[dict[str, Any]] = None
    status: EvaluationStatus
    latency_ms: Optional[int] = None
    token_usage_input: int = 0
    token_usage_output: int = 0
    cost: Optional[Decimal] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    # Nested info
    example_name: Optional[str] = None
    example_input: Optional[Any] = None
    example_expected_output: Optional[Any] = None

    # Computed aggregates (set from scores)
    passed: Optional[bool] = None
    aggregate_score: Optional[float] = None


class EvaluationResultDetailResponse(EvaluationResultResponse):
    """Schema for detailed result response with scores"""
    scores: list[EvaluationScoreResponse] = []


class EvaluationResultListResponse(BaseModel):
    """Schema for paginated result list"""
    results: list[EvaluationResultResponse]
    total: int
    page: int
    page_size: int


# ===== Run Metrics Schemas =====

class EvaluatorScoreAggregate(BaseModel):
    """Aggregate scores for a single evaluator"""
    evaluator_id: int
    evaluator_name: str
    evaluator_type: str
    category: str
    pass_rate: float
    avg_score: float
    total_evaluated: int


class TagBreakdown(BaseModel):
    """Score breakdown by tag"""
    tag: str
    count: int
    pass_rate: float
    avg_score: float


class RunMetadataAggregates(BaseModel):
    """Aggregated run metadata metrics"""
    avg_chain_length: Optional[float] = None
    avg_tool_calls: Optional[float] = None
    tool_success_rate: Optional[float] = None
    total_tool_calls: int = 0
    failed_tool_calls: int = 0
    tools_used_distribution: dict[str, int] = Field(default_factory=dict)
    avg_llm_calls: Optional[float] = None
    avg_spans_per_run: Optional[float] = None
    error_rate: Optional[float] = None


class EvaluationRunMetrics(BaseModel):
    """Complete metrics for an evaluation run"""
    total_examples: int
    completed: int
    failed: int
    pass_rate: float
    avg_score: float
    avg_latency_ms: Optional[float] = None
    total_tokens: int
    total_cost: Optional[Decimal] = None
    score_distribution: dict[str, int] = Field(default_factory=dict)
    evaluator_scores: list[EvaluatorScoreAggregate] = []
    tag_breakdown: list[TagBreakdown] = []
    run_metadata_aggregates: Optional[RunMetadataAggregates] = None


# ===== Comparison Schemas =====

class RunComparisonItem(BaseModel):
    """Single run info for comparison"""
    run_id: int
    run_name: Optional[str] = None
    agent_name: str
    agent_version_id: Optional[int] = None
    status: EvaluationStatus
    pass_rate: float
    avg_score: float
    total_examples: int
    completed_at: Optional[datetime] = None


class ExampleComparisonResult(BaseModel):
    """Comparison of a single example across runs"""
    example_id: int
    example_name: Optional[str] = None
    example_input: Any
    results: dict[int, EvaluationResultResponse]  # run_id -> result


class EvaluationComparisonResponse(BaseModel):
    """Schema for comparing multiple runs"""
    runs: list[RunComparisonItem]
    metrics_comparison: dict[int, EvaluationRunMetrics]  # run_id -> metrics
    example_comparisons: list[ExampleComparisonResult] = []


# ===== Import/Export Schemas =====

class DatasetImportRequest(BaseModel):
    """Schema for importing dataset examples"""
    format: str = Field(..., pattern="^(csv|json)$")
    data: str  # Base64 encoded file content or JSON string


class DatasetImportResponse(BaseModel):
    """Schema for import results"""
    imported_count: int
    skipped_count: int
    errors: list[str] = []


class DatasetExportRequest(BaseModel):
    """Schema for exporting dataset"""
    format: str = Field(..., pattern="^(csv|json)$")


# ===== WebSocket Event Schemas =====

class EvaluationProgressEvent(BaseModel):
    """WebSocket event for evaluation progress"""
    event_type: str = "evaluation_progress"
    run_id: int
    status: EvaluationStatus
    progress: int
    completed_examples: int
    total_examples: int
    current_example_id: Optional[int] = None
    current_example_name: Optional[str] = None


class EvaluationResultEvent(BaseModel):
    """WebSocket event for individual result completion"""
    event_type: str = "evaluation_result"
    run_id: int
    result_id: int
    example_id: int
    status: EvaluationStatus
    passed: Optional[bool] = None
    score: Optional[float] = None


class EvaluationCompleteEvent(BaseModel):
    """WebSocket event for evaluation completion"""
    event_type: str = "evaluation_complete"
    run_id: int
    status: EvaluationStatus
    metrics: Optional[EvaluationRunMetrics] = None
