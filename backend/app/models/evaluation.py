"""Evaluation models for agent testing and performance measurement"""

from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Numeric, Table
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class EvaluatorCategory(str, Enum):
    """Category of evaluator"""
    OUTPUT = "output"
    RUN_METADATA = "run_metadata"


class EvaluatorType(str, Enum):
    """Built-in evaluator types"""
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
    """Status of evaluation runs and results"""
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
    """Type of dataset schema"""
    TEXT = "text"
    STRUCTURED = "structured"


# Many-to-many association table for evaluations and evaluators
evaluation_evaluators = Table(
    'evaluation_evaluators',
    Base.metadata,
    Column('evaluation_id', Integer, ForeignKey('evaluations.id', ondelete='CASCADE'), primary_key=True),
    Column('evaluator_id', Integer, ForeignKey('evaluators.id', ondelete='CASCADE'), primary_key=True)
)


class EvaluationDataset(Base):
    """Dataset containing test examples for agent evaluation"""

    __tablename__ = "evaluation_datasets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    schema_type = Column(String(20), nullable=False, default=DatasetSchemaType.TEXT.value)
    input_schema = Column(JSONB, nullable=True)
    output_schema = Column(JSONB, nullable=True)
    tags = Column(ARRAY(String(255)), nullable=True)
    example_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="evaluation_datasets")
    examples = relationship(
        "DatasetExample",
        back_populates="dataset",
        cascade="all, delete-orphan",
        order_by="DatasetExample.id"
    )
    evaluations = relationship("Evaluation", back_populates="dataset")

    def __repr__(self):
        return f"<EvaluationDataset(id={self.id}, name='{self.name}', examples={self.example_count})>"


class DatasetExample(Base):
    """Individual test case within a dataset"""

    __tablename__ = "dataset_examples"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("evaluation_datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    input = Column(JSONB, nullable=False)
    expected_output = Column(JSONB, nullable=False)
    context = Column(JSONB, nullable=True)
    example_metadata = Column(JSONB, nullable=True)
    tags = Column(ARRAY(String(255)), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    dataset = relationship("EvaluationDataset", back_populates="examples")
    results = relationship("EvaluationResult", back_populates="example")

    def __repr__(self):
        return f"<DatasetExample(id={self.id}, name='{self.name}', dataset_id={self.dataset_id})>"


class Evaluation(Base):
    """Reusable evaluation configuration - defines what to test and how to judge"""

    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    dataset_id = Column(Integer, ForeignKey("evaluation_datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    config = Column(JSONB, nullable=False, default=dict)  # concurrency, timeout, sampling config
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="evaluations")
    dataset = relationship("EvaluationDataset", back_populates="evaluations")
    evaluators = relationship(
        "Evaluator",
        secondary=evaluation_evaluators,
        back_populates="evaluations"
    )
    runs = relationship(
        "EvaluationRun",
        back_populates="evaluation",
        cascade="all, delete-orphan",
        order_by="EvaluationRun.id.desc()"
    )

    def __repr__(self):
        return f"<Evaluation(id={self.id}, name='{self.name}', dataset_id={self.dataset_id})>"


class Evaluator(Base):
    """Evaluator definition for judging agent outputs or run metadata"""

    __tablename__ = "evaluators"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)  # NULL for built-in
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False, index=True)
    category = Column(String(20), nullable=False, default=EvaluatorCategory.OUTPUT.value, index=True)
    description = Column(Text, nullable=True)
    config = Column(JSONB, nullable=False, default=dict)
    is_builtin = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="evaluators")
    evaluations = relationship(
        "Evaluation",
        secondary=evaluation_evaluators,
        back_populates="evaluators"
    )
    scores = relationship("EvaluationScore", back_populates="evaluator")

    def __repr__(self):
        return f"<Evaluator(id={self.id}, name='{self.name}', type='{self.type}', category='{self.category}')>"


class EvaluationRun(Base):
    """An execution of an evaluation against a specific agent"""

    __tablename__ = "evaluation_runs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=True)  # Optional run-specific name
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_version_id = Column(Integer, ForeignKey("agent_versions.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), nullable=False, default=EvaluationStatus.PENDING.value, index=True)
    progress = Column(Integer, nullable=False, default=0)
    total_examples = Column(Integer, nullable=False, default=0)
    completed_examples = Column(Integer, nullable=False, default=0)
    metrics = Column(JSONB, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="evaluation_runs")
    evaluation = relationship("Evaluation", back_populates="runs")
    agent = relationship("Agent", back_populates="evaluation_runs")
    agent_version = relationship("AgentVersion")
    results = relationship(
        "EvaluationResult",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="EvaluationResult.id"
    )

    # Convenience properties to access evaluation's config and dataset
    @property
    def config(self):
        """Get config from the parent evaluation"""
        return self.evaluation.config if self.evaluation else {}

    @property
    def dataset(self):
        """Get dataset from the parent evaluation"""
        return self.evaluation.dataset if self.evaluation else None

    @property
    def dataset_id(self):
        """Get dataset_id from the parent evaluation"""
        return self.evaluation.dataset_id if self.evaluation else None

    @property
    def evaluators(self):
        """Get evaluators from the parent evaluation"""
        return self.evaluation.evaluators if self.evaluation else []

    def __repr__(self):
        return f"<EvaluationRun(id={self.id}, evaluation_id={self.evaluation_id}, status='{self.status}', progress={self.progress}%)>"


class EvaluationResult(Base):
    """Result for a single example in an evaluation run"""

    __tablename__ = "evaluation_results"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    example_id = Column(Integer, ForeignKey("dataset_examples.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True)
    agent_output = Column(JSONB, nullable=True)
    run_metadata = Column(JSONB, nullable=True)
    status = Column(String(20), nullable=False, default=EvaluationStatus.PENDING.value, index=True)
    latency_ms = Column(Integer, nullable=True)
    token_usage_input = Column(Integer, nullable=False, default=0)
    token_usage_output = Column(Integer, nullable=False, default=0)
    cost = Column(Numeric(precision=10, scale=6), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    run = relationship("EvaluationRun", back_populates="results")
    example = relationship("DatasetExample", back_populates="results")
    session = relationship("Session")
    scores = relationship(
        "EvaluationScore",
        back_populates="result",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<EvaluationResult(id={self.id}, status='{self.status}', example_id={self.example_id})>"


class EvaluationScore(Base):
    """Individual evaluator score for a result"""

    __tablename__ = "evaluation_scores"

    id = Column(Integer, primary_key=True, index=True)
    result_id = Column(Integer, ForeignKey("evaluation_results.id", ondelete="CASCADE"), nullable=False, index=True)
    evaluator_id = Column(Integer, ForeignKey("evaluators.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Numeric(precision=5, scale=4), nullable=True)
    passed = Column(Boolean, nullable=True)
    feedback = Column(Text, nullable=True)
    score_metadata = Column(JSONB, nullable=True)
    status = Column(String(20), nullable=False, default=EvaluationScoreStatus.PENDING.value, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    result = relationship("EvaluationResult", back_populates="scores")
    evaluator = relationship("Evaluator", back_populates="scores")
    session = relationship("Session")

    def __repr__(self):
        return f"<EvaluationScore(id={self.id}, score={self.score}, passed={self.passed})>"
