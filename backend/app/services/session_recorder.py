"""
Session Recorder Service for Agent Execution Tracking.

This service provides a clean interface for recording agent execution
sessions, messages, and trace steps. It handles:
- Session lifecycle management (create, resume, complete, fail)
- Message recording (user, assistant, system, tool)
- Trace step recording (thoughts, tool calls, observations)
- Performance metrics tracking (tokens, latency, cost)
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session as DBSession
import logging
import time

from ..models.session import (
    Session, SessionStatus,
    Message, MessageRole,
    TraceStep, TraceStepType
)
from ..models.agent import Agent

logger = logging.getLogger(__name__)


class SessionRecorderError(Exception):
    """Exception raised when session recording fails"""
    pass


class SessionRecorder:
    """
    Service for recording agent execution sessions.

    This class provides a stateful interface for recording all aspects
    of an agent execution session, including messages, trace steps,
    and performance metrics.

    Usage:
        recorder = SessionRecorder(db, agent_id=1, user_id=1)
        recorder.start_session()

        recorder.record_user_message("What is 2 + 2?")
        recorder.record_trace_step(TraceStepType.THOUGHT, "I need to calculate this")
        recorder.record_trace_step(
            TraceStepType.TOOL_CALL,
            "Using calculator",
            tool_name="Calculator",
            tool_input={"expression": "2 + 2"}
        )
        recorder.record_trace_step(
            TraceStepType.TOOL_RESULT,
            "4",
            tool_name="Calculator",
            tool_output={"result": "4"}
        )
        recorder.record_assistant_message("The answer is 4")

        recorder.finish_session(
            status=SessionStatus.COMPLETED,
            output="The answer is 4",
            tokens_input=50,
            tokens_output=20
        )
    """

    def __init__(
        self,
        db: DBSession,
        agent_id: int,
        user_id: int,
        agent_version_id: Optional[int] = None,
        session_id: Optional[int] = None
    ):
        """
        Initialize session recorder.

        Args:
            db: Database session
            agent_id: Agent ID being executed
            user_id: User ID who owns the session
            agent_version_id: Optional specific agent version ID
            session_id: Optional existing session ID to resume
        """
        self.db = db
        self.agent_id = agent_id
        self.user_id = user_id
        self.agent_version_id = agent_version_id
        self.session_id = session_id

        self._session: Optional[Session] = None
        self._message_sequence = 0
        self._step_number = 0
        self._start_time: Optional[float] = None

    @property
    def session(self) -> Session:
        """Get the current session, raising error if not started"""
        if self._session is None:
            raise SessionRecorderError("Session not started. Call start_session() first.")
        return self._session

    def start_session(self, title: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Session:
        """
        Start a new session or resume an existing one.

        Args:
            title: Optional session title
            metadata: Optional additional metadata

        Returns:
            Session object

        Raises:
            SessionRecorderError: If session creation fails
        """
        self._start_time = time.time()

        if self.session_id:
            # Resume existing session
            self._session = self.db.query(Session).filter(
                Session.id == self.session_id,
                Session.user_id == self.user_id
            ).first()

            if not self._session:
                raise SessionRecorderError(f"Session {self.session_id} not found")

            # Get current sequence numbers
            self._message_sequence = len(self._session.messages)
            self._step_number = len(self._session.trace_steps)

            # Update status to running if it was pending
            if self._session.status == SessionStatus.PENDING:
                self._session.status = SessionStatus.RUNNING
                self.db.commit()

            logger.debug(f"Resumed session {self.session_id}")
        else:
            # Create new session
            self._session = Session(
                user_id=self.user_id,
                agent_id=self.agent_id,
                agent_version_id=self.agent_version_id,
                title=title,
                status=SessionStatus.RUNNING,
                meta=metadata or {}
            )
            self.db.add(self._session)
            self.db.commit()
            self.db.refresh(self._session)

            self.session_id = self._session.id
            self._message_sequence = 0
            self._step_number = 0

            logger.debug(f"Created new session {self.session_id}")

        return self._session

    def record_user_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> Message:
        """
        Record a user message.

        Args:
            content: Message content
            metadata: Optional additional metadata

        Returns:
            Created Message object
        """
        return self._record_message(MessageRole.USER, content, metadata=metadata)

    def record_assistant_message(
        self,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Record an assistant (agent) message.

        Args:
            content: Message content
            tool_calls: Optional list of tool calls made
            metadata: Optional additional metadata

        Returns:
            Created Message object
        """
        return self._record_message(
            MessageRole.ASSISTANT,
            content,
            tool_calls=tool_calls,
            metadata=metadata
        )

    def record_system_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> Message:
        """
        Record a system message.

        Args:
            content: Message content
            metadata: Optional additional metadata

        Returns:
            Created Message object
        """
        return self._record_message(MessageRole.SYSTEM, content, metadata=metadata)

    def record_tool_message(
        self,
        content: str,
        tool_call_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Record a tool result message.

        Args:
            content: Tool output content
            tool_call_id: ID of the tool call this responds to
            metadata: Optional additional metadata

        Returns:
            Created Message object
        """
        return self._record_message(
            MessageRole.TOOL,
            content,
            tool_call_id=tool_call_id,
            metadata=metadata
        )

    def _record_message(
        self,
        role: MessageRole,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_call_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Internal method to record a message.

        Args:
            role: Message role
            content: Message content
            tool_calls: Tool calls (for assistant messages)
            tool_call_id: Tool call ID (for tool messages)
            metadata: Additional metadata

        Returns:
            Created Message object
        """
        message = Message(
            session_id=self.session.id,
            role=role,
            content=content,
            sequence_number=self._message_sequence,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            meta=metadata or {}
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)

        self._message_sequence += 1

        logger.debug(f"Recorded {role.value} message (seq={message.sequence_number})")
        return message

    def record_trace_step(
        self,
        step_type: TraceStepType,
        content: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_input: Optional[Dict[str, Any]] = None,
        tool_output: Optional[Any] = None,
        latency_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TraceStep:
        """
        Record a trace step.

        Args:
            step_type: Type of trace step
            content: Step content/description
            tool_name: Tool name (for tool-related steps)
            tool_input: Tool input parameters
            tool_output: Tool output result
            latency_ms: Step execution time in milliseconds
            metadata: Additional metadata

        Returns:
            Created TraceStep object
        """
        trace_step = TraceStep(
            session_id=self.session.id,
            step_number=self._step_number,
            step_type=step_type,
            content=content,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            latency_ms=latency_ms,
            meta=metadata or {}
        )
        self.db.add(trace_step)
        self.db.commit()
        self.db.refresh(trace_step)

        self._step_number += 1

        logger.debug(f"Recorded trace step {step_type.value} (step={trace_step.step_number})")
        return trace_step

    def record_thought(self, thought: str, metadata: Optional[Dict[str, Any]] = None) -> TraceStep:
        """Convenience method to record a thought step"""
        return self.record_trace_step(TraceStepType.THOUGHT, content=thought, metadata=metadata)

    def record_tool_call(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TraceStep:
        """Convenience method to record a tool call step"""
        return self.record_trace_step(
            TraceStepType.TOOL_CALL,
            content=description or f"Calling {tool_name}",
            tool_name=tool_name,
            tool_input=tool_input,
            metadata=metadata
        )

    def record_tool_result(
        self,
        tool_name: str,
        tool_output: Any,
        latency_ms: Optional[int] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TraceStep:
        """Convenience method to record a tool result step"""
        return self.record_trace_step(
            TraceStepType.TOOL_RESULT,
            content=description or f"Result from {tool_name}",
            tool_name=tool_name,
            tool_output=tool_output,
            latency_ms=latency_ms,
            metadata=metadata
        )

    def record_observation(self, observation: str, metadata: Optional[Dict[str, Any]] = None) -> TraceStep:
        """Convenience method to record an observation step"""
        return self.record_trace_step(TraceStepType.OBSERVATION, content=observation, metadata=metadata)

    def record_reflection(self, reflection: str, metadata: Optional[Dict[str, Any]] = None) -> TraceStep:
        """Convenience method to record a reflection step"""
        return self.record_trace_step(TraceStepType.REFLECTION, content=reflection, metadata=metadata)

    def record_error(
        self,
        error: str,
        error_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TraceStep:
        """Convenience method to record an error step"""
        meta = metadata or {}
        if error_type:
            meta["error_type"] = error_type
        return self.record_trace_step(TraceStepType.ERROR, content=error, metadata=meta)

    def record_final_answer(self, answer: str, metadata: Optional[Dict[str, Any]] = None) -> TraceStep:
        """Convenience method to record the final answer step"""
        return self.record_trace_step(TraceStepType.FINAL_ANSWER, content=answer, metadata=metadata)

    def update_token_usage(self, tokens_input: int, tokens_output: int) -> None:
        """
        Update token usage for the session.

        Args:
            tokens_input: Number of input tokens to add
            tokens_output: Number of output tokens to add
        """
        session = self.session
        session.token_usage_input = (session.token_usage_input or 0) + tokens_input
        session.token_usage_output = (session.token_usage_output or 0) + tokens_output
        self.db.commit()

    def finish_session(
        self,
        status: SessionStatus,
        output: Optional[str] = None,
        tokens_input: Optional[int] = None,
        tokens_output: Optional[int] = None,
        cost: Optional[float] = None,
        error: Optional[str] = None,
        error_type: Optional[str] = None
    ) -> Session:
        """
        Finish the session with final status and metrics.

        Args:
            status: Final session status (COMPLETED or FAILED)
            output: Final output/answer (for completed sessions)
            tokens_input: Total input tokens used
            tokens_output: Total output tokens used
            cost: Estimated total cost
            error: Error message (for failed sessions)
            error_type: Error classification

        Returns:
            Updated Session object
        """
        session = self.session

        # Calculate total latency
        if self._start_time:
            total_latency_ms = int((time.time() - self._start_time) * 1000)
            session.total_latency_ms = total_latency_ms

        session.status = status
        session.completed_at = datetime.now(timezone.utc)

        if tokens_input is not None:
            session.token_usage_input = tokens_input
        if tokens_output is not None:
            session.token_usage_output = tokens_output
        if cost is not None:
            session.total_cost = cost

        if error:
            session.error_message = error
            session.error_type = error_type

        # Record final answer as trace step if output provided and completed
        if status == SessionStatus.COMPLETED and output:
            self.record_final_answer(output)

        self.db.commit()
        self.db.refresh(session)

        logger.info(
            f"Session {session.id} finished with status={status.value}, "
            f"latency={session.total_latency_ms}ms, "
            f"tokens_in={session.token_usage_input}, tokens_out={session.token_usage_output}"
        )

        return session

    def fail_session(
        self,
        error: str,
        error_type: Optional[str] = None,
        tokens_input: Optional[int] = None,
        tokens_output: Optional[int] = None
    ) -> Session:
        """
        Convenience method to mark session as failed.

        Args:
            error: Error message
            error_type: Error classification
            tokens_input: Tokens used before failure
            tokens_output: Tokens used before failure

        Returns:
            Updated Session object
        """
        # Record error as trace step
        self.record_error(error, error_type=error_type)

        return self.finish_session(
            status=SessionStatus.FAILED,
            error=error,
            error_type=error_type,
            tokens_input=tokens_input,
            tokens_output=tokens_output
        )

    def get_messages(self) -> List[Message]:
        """Get all messages in the session, ordered by sequence"""
        return self.session.messages

    def get_trace_steps(self) -> List[TraceStep]:
        """Get all trace steps in the session, ordered by step number"""
        return self.session.trace_steps

    def get_session_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current session.

        Returns:
            Dictionary with session summary
        """
        session = self.session
        return {
            "session_id": session.id,
            "agent_id": session.agent_id,
            "status": session.status.value,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "total_latency_ms": session.total_latency_ms,
            "token_usage": {
                "input": session.token_usage_input or 0,
                "output": session.token_usage_output or 0,
                "total": (session.token_usage_input or 0) + (session.token_usage_output or 0)
            },
            "total_cost": session.total_cost,
            "message_count": len(session.messages),
            "trace_step_count": len(session.trace_steps),
            "error": session.error_message
        }


def create_session_recorder(
    db: DBSession,
    agent_id: int,
    user_id: int,
    agent_version_id: Optional[int] = None,
    session_id: Optional[int] = None
) -> SessionRecorder:
    """
    Convenience function to create a session recorder.

    Args:
        db: Database session
        agent_id: Agent ID
        user_id: User ID
        agent_version_id: Optional agent version ID
        session_id: Optional existing session ID to resume

    Returns:
        SessionRecorder instance
    """
    return SessionRecorder(
        db=db,
        agent_id=agent_id,
        user_id=user_id,
        agent_version_id=agent_version_id,
        session_id=session_id
    )
