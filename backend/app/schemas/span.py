"""
Pydantic schemas for Span model (Enhanced Tracing System).

These schemas handle validation and serialization for hierarchical
trace spans used in observability and debugging.

Implements Phase 1 of ENHANCED_TRACING_SPEC.md.
"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID


class SpanType(str, Enum):
    """Type of span in hierarchical trace"""
    AGENT = "agent"          # Top-level agent execution
    CHAIN = "chain"          # Chain/sequence execution
    LLM = "llm"              # LLM API call
    TOOL = "tool"            # Tool invocation
    RETRIEVER = "retriever"  # Document retrieval
    EMBEDDING = "embedding"  # Embedding generation
    PARSER = "parser"        # Output parsing
    PROMPT = "prompt"        # Prompt formatting
    MEMORY = "memory"        # Memory read/write
    THOUGHT = "thought"      # Agent reasoning
    ERROR = "error"          # Error occurrence


class SpanStatus(str, Enum):
    """Status of a span execution"""
    RUNNING = "running"      # Currently executing
    SUCCESS = "success"      # Completed successfully
    ERROR = "error"          # Failed with error


# ============================================================================
# Base Schemas
# ============================================================================

class SpanBase(BaseModel):
    """Base schema for Span with common fields"""
    span_type: SpanType = Field(..., description="Type of span (agent, llm, tool, etc.)")
    name: str = Field(..., max_length=255, description="Human-readable span name")
    tags: Optional[List[str]] = Field(None, description="Tags for filtering")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")


class SpanCreate(SpanBase):
    """
    Schema for creating a new span.

    Used internally by SpanRecorder to create spans during execution.
    """
    session_id: int = Field(..., description="Session this span belongs to")
    trace_id: UUID = Field(..., description="UUID grouping spans in a single execution")
    parent_span_id: Optional[int] = Field(None, description="Parent span ID for hierarchy")
    span_order: int = Field(..., ge=0, description="Order among sibling spans")
    depth: int = Field(default=0, ge=0, description="Nesting depth for UI")
    started_at: datetime = Field(..., description="When the span started")

    # Optional fields that can be set during span creation
    input: Optional[Union[Dict[str, Any], List[Any]]] = Field(None, description="Operation input")
    status: SpanStatus = Field(default=SpanStatus.RUNNING, description="Span status")

    # LLM-specific (optional)
    model_name: Optional[str] = Field(None, max_length=100, description="LLM model name")
    model_provider: Optional[str] = Field(None, max_length=50, description="LLM provider")
    model_parameters: Optional[Dict[str, Any]] = Field(None, description="Model parameters")

    # Tool-specific (optional)
    tool_name: Optional[str] = Field(None, max_length=255, description="Tool name for tool spans")


class SpanUpdate(BaseModel):
    """
    Schema for updating a span.

    Used to set output, end time, status, tokens, and cost after span completion.
    """
    ended_at: Optional[datetime] = Field(None, description="When the span ended")
    duration_ms: Optional[int] = Field(None, ge=0, description="Duration in milliseconds")
    status: Optional[SpanStatus] = Field(None, description="Final status")
    status_message: Optional[str] = Field(None, description="Status message")

    # Data - can be dict or list depending on the chain output format
    input: Optional[Union[Dict[str, Any], List[Any]]] = Field(None, description="Operation input")
    output: Optional[Union[Dict[str, Any], List[Any]]] = Field(None, description="Operation output")

    # LLM-specific
    model_name: Optional[str] = Field(None, max_length=100)
    model_provider: Optional[str] = Field(None, max_length=50)
    model_parameters: Optional[Dict[str, Any]] = Field(None)
    tokens_input: Optional[int] = Field(None, ge=0, description="Input tokens")
    tokens_output: Optional[int] = Field(None, ge=0, description="Output tokens")
    tokens_total: Optional[int] = Field(None, ge=0, description="Total tokens")
    cost_usd: Optional[Decimal] = Field(None, ge=0, description="Cost in USD")

    # Tool-specific
    tool_name: Optional[str] = Field(None, max_length=255)

    # Error details
    error_type: Optional[str] = Field(None, max_length=255, description="Error type")
    error_message: Optional[str] = Field(None, description="Error message")
    error_stack: Optional[str] = Field(None, description="Error stack trace")

    # Metadata
    tags: Optional[List[str]] = Field(None, description="Tags for filtering")
    meta: Optional[Dict[str, Any]] = Field(None, description="Custom metadata")


# ============================================================================
# Response Schemas
# ============================================================================

class SpanResponse(SpanBase):
    """Schema for span response (flat representation)"""
    id: int
    session_id: int
    trace_id: UUID
    parent_span_id: Optional[int]
    span_order: int
    depth: int

    # Timing
    started_at: datetime
    ended_at: Optional[datetime]
    duration_ms: Optional[int]

    # Status
    status: SpanStatus
    status_message: Optional[str]

    # Data - can be dict or list depending on the chain output format
    input: Optional[Union[Dict[str, Any], List[Any]]]
    output: Optional[Union[Dict[str, Any], List[Any]]]

    # LLM-specific
    model_name: Optional[str]
    model_provider: Optional[str]
    model_parameters: Optional[Dict[str, Any]]
    tokens_input: Optional[int]
    tokens_output: Optional[int]
    tokens_total: Optional[int]
    cost_usd: Optional[Decimal]

    # Tool-specific
    tool_name: Optional[str]

    # Error details
    error_type: Optional[str]
    error_message: Optional[str]
    error_stack: Optional[str]

    # Timestamps
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator('cost_usd', mode='before')
    @classmethod
    def convert_decimal(cls, v):
        """Convert Decimal to float-serializable format"""
        if v is not None:
            return Decimal(str(v))
        return v


class SpanTreeNode(BaseModel):
    """Schema for a span in the tree representation (with children)"""
    id: int
    span_type: SpanType
    name: str
    status: SpanStatus
    started_at: datetime
    ended_at: Optional[datetime]
    duration_ms: Optional[int]
    depth: int

    # Quick stats for tree view
    tokens_total: Optional[int]
    cost_usd: Optional[Decimal]
    tool_name: Optional[str]
    error_message: Optional[str]

    # Children (recursive)
    children: List["SpanTreeNode"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    @field_validator('cost_usd', mode='before')
    @classmethod
    def convert_decimal(cls, v):
        if v is not None:
            return Decimal(str(v))
        return v


# Update forward reference for recursive type
SpanTreeNode.model_rebuild()


class SpanTreeResponse(BaseModel):
    """Schema for hierarchical span tree response"""
    trace_id: UUID
    root_span: Optional[SpanTreeNode] = Field(None, description="Root span with nested children")
    stats: "SpanStatsResponse" = Field(..., description="Aggregated statistics")


class SpanStatsResponse(BaseModel):
    """Schema for aggregated span statistics"""
    total_spans: int = Field(..., description="Total number of spans")
    total_duration_ms: Optional[int] = Field(None, description="Total trace duration")
    total_tokens: int = Field(default=0, description="Total tokens across all LLM spans")
    total_tokens_input: int = Field(default=0, description="Total input tokens")
    total_tokens_output: int = Field(default=0, description="Total output tokens")
    total_cost_usd: Decimal = Field(default=Decimal("0"), description="Total cost in USD")
    span_count_by_type: Dict[str, int] = Field(default_factory=dict, description="Count per span type")
    span_count_by_status: Dict[str, int] = Field(default_factory=dict, description="Count per status")
    error_count: int = Field(default=0, description="Number of error spans")
    average_duration_ms: Optional[float] = Field(None, description="Average span duration")


# Update forward reference
SpanTreeResponse.model_rebuild()


# ============================================================================
# List Response Schema
# ============================================================================

class SpanListResponse(BaseModel):
    """Schema for paginated span list"""
    spans: List[SpanResponse]
    total: int = Field(..., description="Total number of spans matching filters")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")


# ============================================================================
# Filter Schema
# ============================================================================

class SpanFilterParams(BaseModel):
    """Schema for span filtering parameters"""
    span_type: Optional[List[SpanType]] = Field(None, description="Filter by span type(s)")
    status: Optional[List[SpanStatus]] = Field(None, description="Filter by status(es)")
    min_duration_ms: Optional[int] = Field(None, ge=0, description="Minimum duration")
    max_duration_ms: Optional[int] = Field(None, ge=0, description="Maximum duration")
    has_error: Optional[bool] = Field(None, description="Filter by error presence")
    tags: Optional[List[str]] = Field(None, description="Filter by tags (AND logic)")
    search: Optional[str] = Field(None, description="Search in name, input, output")
    tool_name: Optional[str] = Field(None, description="Filter by tool name")
    model_name: Optional[str] = Field(None, description="Filter by model name")
