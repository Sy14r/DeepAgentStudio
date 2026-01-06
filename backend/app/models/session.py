"""
Session, Message, and TraceStep models for agent execution tracking.

This module implements the observability layer for DeepAgentStudio:
- Session: Records agent interactions with performance metrics
- Message: Stores conversation history (user/assistant/system messages)
- TraceStep: Captures detailed execution traces for debugging
"""
from enum import Enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import Enum as SQLEnum

from ..database import Base


class SessionStatus(str, Enum):
    """Session execution status"""
    PENDING = "pending"      # Created but not started
    RUNNING = "running"      # Currently executing
    COMPLETED = "completed"  # Finished successfully
    FAILED = "failed"        # Execution failed with error


class MessageRole(str, Enum):
    """Message role in conversation"""
    USER = "user"            # User input message
    ASSISTANT = "assistant"  # Agent/LLM response
    SYSTEM = "system"        # System prompt or instruction
    TOOL = "tool"            # Tool execution result


class TraceStepType(str, Enum):
    """Type of trace step in agent execution"""
    THOUGHT = "thought"          # Agent reasoning/thinking
    TOOL_CALL = "tool_call"      # Tool invocation
    TOOL_RESULT = "tool_result"  # Tool output
    REFLECTION = "reflection"    # Self-critique iteration
    ERROR = "error"              # Error during execution
    OBSERVATION = "observation"  # Agent observation
    FINAL_ANSWER = "final_answer"  # Agent's final response


class Session(Base):
    """
    Session model - Records agent execution instances.

    A session represents a single interaction with an agent, tracking:
    - Which agent/version was used
    - Conversation messages
    - Execution traces
    - Performance metrics (latency, tokens, cost)
    - Success/failure status
    """
    __tablename__ = "sessions"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True)
    agent_version_id = Column(Integer, ForeignKey("agent_versions.id", ondelete="SET NULL"), nullable=True)

    # Session metadata
    title = Column(String(255), nullable=True)  # Optional user-defined title
    status = Column(SQLEnum(SessionStatus), nullable=False, default=SessionStatus.PENDING, index=True)

    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Performance metrics
    total_latency_ms = Column(Integer, nullable=True)  # Total execution time in milliseconds
    token_usage_input = Column(Integer, nullable=True, default=0)  # Input tokens
    token_usage_output = Column(Integer, nullable=True, default=0)  # Output tokens
    total_cost = Column(Float, nullable=True)  # Estimated cost in USD

    # Error handling
    error_message = Column(Text, nullable=True)  # Error details if failed
    error_type = Column(String(255), nullable=True)  # Error classification

    # Additional metadata (renamed to meta to avoid SQLAlchemy reserved word)
    meta = Column(JSON, default=dict, nullable=False)  # Flexible metadata storage

    # Relationships
    user = relationship("User", back_populates="sessions")
    agent = relationship("Agent")  # No back_populates to avoid circular
    agent_version = relationship("AgentVersion")  # Snapshot of agent config used
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan", order_by="Message.sequence_number")
    trace_steps = relationship("TraceStep", back_populates="session", cascade="all, delete-orphan", order_by="TraceStep.step_number")

    def __repr__(self):
        return f"<Session(id={self.id}, agent_id={self.agent_id}, status={self.status.value}, started_at={self.started_at})>"


class Message(Base):
    """
    Message model - Stores conversation history within a session.

    Messages represent the conversational flow:
    - User inputs
    - Agent responses
    - System prompts
    - Tool results
    """
    __tablename__ = "messages"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)

    # Message data
    role = Column(SQLEnum(MessageRole), nullable=False, index=True)
    content = Column(Text, nullable=False)  # Message text content

    # Ordering
    sequence_number = Column(Integer, nullable=False)  # Order within session (0, 1, 2, ...)

    # Tool-related fields (for tool messages)
    tool_calls = Column(JSON, nullable=True)  # Tool calls made by assistant
    tool_call_id = Column(String(255), nullable=True)  # Reference to specific tool call

    # Metadata (renamed to meta to avoid SQLAlchemy reserved word)
    meta = Column(JSON, default=dict, nullable=False)  # Additional message metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    session = relationship("Session", back_populates="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, session_id={self.session_id}, role={self.role.value}, seq={self.sequence_number})>"


class TraceStep(Base):
    """
    TraceStep model - Captures detailed execution trace for debugging.

    Trace steps provide observability into agent reasoning:
    - Agent thoughts and reasoning
    - Tool calls with inputs/outputs
    - Reflection iterations
    - Errors and observations
    """
    __tablename__ = "trace_steps"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)

    # Step metadata
    step_number = Column(Integer, nullable=False)  # Sequential step number (0, 1, 2, ...)
    step_type = Column(SQLEnum(TraceStepType), nullable=False, index=True)

    # Step content
    content = Column(Text, nullable=True)  # Thought, observation, or result text

    # Tool-specific fields (for tool_call and tool_result types)
    tool_name = Column(String(255), nullable=True, index=True)
    tool_input = Column(JSON, nullable=True)  # Tool call parameters
    tool_output = Column(JSON, nullable=True)  # Tool execution result

    # Performance
    latency_ms = Column(Integer, nullable=True)  # Step execution time

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Metadata (renamed to meta to avoid SQLAlchemy reserved word)
    meta = Column(JSON, default=dict, nullable=False)  # Additional step metadata

    # Relationships
    session = relationship("Session", back_populates="trace_steps")

    def __repr__(self):
        return f"<TraceStep(id={self.id}, session_id={self.session_id}, step={self.step_number}, type={self.step_type.value})>"
