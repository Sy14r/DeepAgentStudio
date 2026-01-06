"""
Tests for Session, Message, and TraceStep models
"""
import pytest
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from app.models.session import Session, Message, TraceStep, SessionStatus, MessageRole, TraceStepType
from app.models.user import User
from app.models.agent import Agent, AgentVersion, AgentType
from app.security import hash_password


class TestSessionModel:
    """Test cases for Session model"""

    def test_create_session(self, db, test_user):
        """Test creating a session"""
        # Create agent first
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.commit()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            title="Test Session",
            status=SessionStatus.PENDING
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        assert session.id is not None
        assert session.user_id == test_user.id
        assert session.agent_id == agent.id
        assert session.title == "Test Session"
        assert session.status == SessionStatus.PENDING
        assert session.started_at is not None
        assert session.completed_at is None
        assert session.meta == {}

    def test_create_session_minimal(self, db, test_user):
        """Test creating session with minimal fields"""
        session = Session(
            user_id=test_user.id
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        assert session.id is not None
        assert session.agent_id is None
        assert session.title is None
        assert session.status == SessionStatus.PENDING
        assert session.total_latency_ms is None
        assert session.token_usage_input == 0  # Default value
        assert session.token_usage_output == 0  # Default value

    def test_session_without_user_fails(self, db):
        """Test that session without user_id fails"""
        session = Session(
            title="No User Session"
        )
        db.add(session)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_session_status_values(self, db, test_user):
        """Test all session status values"""
        statuses = [
            SessionStatus.PENDING,
            SessionStatus.RUNNING,
            SessionStatus.COMPLETED,
            SessionStatus.FAILED
        ]

        for status in statuses:
            session = Session(
                user_id=test_user.id,
                status=status
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            assert session.status == status
            db.delete(session)
            db.commit()

    def test_session_with_performance_metrics(self, db, test_user):
        """Test session with performance metrics"""
        session = Session(
            user_id=test_user.id,
            total_latency_ms=1234,
            token_usage_input=100,
            token_usage_output=200,
            total_cost=0.05
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        assert session.total_latency_ms == 1234
        assert session.token_usage_input == 100
        assert session.token_usage_output == 200
        assert session.total_cost == 0.05

    def test_session_with_error(self, db, test_user):
        """Test session with error details"""
        session = Session(
            user_id=test_user.id,
            status=SessionStatus.FAILED,
            error_message="Test error occurred",
            error_type="ValueError"
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        assert session.status == SessionStatus.FAILED
        assert session.error_message == "Test error occurred"
        assert session.error_type == "ValueError"

    def test_session_with_metadata(self, db, test_user):
        """Test session with custom metadata"""
        session = Session(
            user_id=test_user.id,
            meta={"key1": "value1", "key2": 123, "nested": {"key3": "value3"}}
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        assert session.meta["key1"] == "value1"
        assert session.meta["key2"] == 123
        assert session.meta["nested"]["key3"] == "value3"

    def test_session_cascade_delete_with_user(self, db):
        """Test that deleting user cascades to sessions"""
        user = User(
            username="sessionuser",
            email="session@example.com",
            hashed_password=hash_password("password123")
        )
        db.add(user)
        db.commit()

        session = Session(
            user_id=user.id,
            title="Cascade Test"
        )
        db.add(session)
        db.commit()
        session_id = session.id

        db.delete(user)
        db.commit()

        deleted_session = db.query(Session).filter(Session.id == session_id).first()
        assert deleted_session is None

    def test_session_agent_set_null_on_delete(self, db, test_user):
        """Test that deleting agent sets agent_id to NULL"""
        agent = Agent(
            user_id=test_user.id,
            name="Delete Test Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.commit()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id
        )
        db.add(session)
        db.commit()
        session_id = session.id
        agent_id = agent.id

        # Delete agent
        db.delete(agent)
        db.commit()

        # Session should still exist with agent_id = None
        session = db.query(Session).filter(Session.id == session_id).first()
        assert session is not None
        assert session.agent_id is None

    def test_session_with_agent_version(self, db, test_user):
        """Test session with agent version reference"""
        agent = Agent(
            user_id=test_user.id,
            name="Versioned Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.flush()

        version = AgentVersion(
            agent_id=agent.id,
            version_number=1,
            config={
                "llm_config": {},
                "reflection_config": {},
                "memory_config": {}
            },
            created_by=test_user.id
        )
        db.add(version)
        db.commit()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            agent_version_id=version.id
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        assert session.agent_version_id == version.id

    def test_update_session_status(self, db, test_user):
        """Test updating session status"""
        session = Session(
            user_id=test_user.id,
            status=SessionStatus.PENDING
        )
        db.add(session)
        db.commit()

        session.status = SessionStatus.RUNNING
        db.commit()
        db.refresh(session)
        assert session.status == SessionStatus.RUNNING

        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(session)
        assert session.status == SessionStatus.COMPLETED
        assert session.completed_at is not None

    def test_session_repr(self, db, test_user):
        """Test session string representation"""
        session = Session(
            user_id=test_user.id,
            title="Test Session",
            status=SessionStatus.RUNNING
        )
        db.add(session)
        db.commit()

        repr_str = repr(session)
        assert "Session" in repr_str
        assert str(session.id) in repr_str
        assert "running" in repr_str


class TestMessageModel:
    """Test cases for Message model"""

    def test_create_message(self, db, test_user):
        """Test creating a message"""
        session = Session(user_id=test_user.id)
        db.add(session)
        db.flush()

        message = Message(
            session_id=session.id,
            role=MessageRole.USER,
            content="Hello, agent!",
            sequence_number=0
        )
        db.add(message)
        db.commit()
        db.refresh(message)

        assert message.id is not None
        assert message.session_id == session.id
        assert message.role == MessageRole.USER
        assert message.content == "Hello, agent!"
        assert message.sequence_number == 0
        assert message.meta == {}
        assert message.created_at is not None

    def test_message_roles(self, db, test_user):
        """Test all message role types"""
        session = Session(user_id=test_user.id)
        db.add(session)
        db.flush()

        roles = [
            MessageRole.USER,
            MessageRole.ASSISTANT,
            MessageRole.SYSTEM,
            MessageRole.TOOL
        ]

        for idx, role in enumerate(roles):
            message = Message(
                session_id=session.id,
                role=role,
                content=f"Message with role {role.value}",
                sequence_number=idx
            )
            db.add(message)

        db.commit()

        messages = db.query(Message).filter(Message.session_id == session.id).order_by(Message.sequence_number).all()
        assert len(messages) == 4
        for idx, role in enumerate(roles):
            assert messages[idx].role == role

    def test_message_with_tool_calls(self, db, test_user):
        """Test message with tool calls"""
        session = Session(user_id=test_user.id)
        db.add(session)
        db.flush()

        tool_calls = [
            {
                "id": "call_123",
                "type": "function",
                "function": {"name": "search_web", "arguments": '{"query": "test"}'}
            }
        ]

        message = Message(
            session_id=session.id,
            role=MessageRole.ASSISTANT,
            content="Let me search for that.",
            sequence_number=0,
            tool_calls=tool_calls
        )
        db.add(message)
        db.commit()
        db.refresh(message)

        assert message.tool_calls is not None
        assert len(message.tool_calls) == 1
        assert message.tool_calls[0]["id"] == "call_123"
        assert message.tool_calls[0]["function"]["name"] == "search_web"

    def test_message_with_tool_call_id(self, db, test_user):
        """Test tool message with tool_call_id"""
        session = Session(user_id=test_user.id)
        db.add(session)
        db.flush()

        message = Message(
            session_id=session.id,
            role=MessageRole.TOOL,
            content="Search results: ...",
            sequence_number=0,
            tool_call_id="call_123"
        )
        db.add(message)
        db.commit()
        db.refresh(message)

        assert message.role == MessageRole.TOOL
        assert message.tool_call_id == "call_123"

    def test_message_sequence_ordering(self, db, test_user):
        """Test messages ordered by sequence_number"""
        session = Session(user_id=test_user.id)
        db.add(session)
        db.flush()

        # Add messages out of order
        for seq in [2, 0, 1, 3]:
            message = Message(
                session_id=session.id,
                role=MessageRole.USER,
                content=f"Message {seq}",
                sequence_number=seq
            )
            db.add(message)

        db.commit()

        # Query messages - should be ordered by sequence_number via relationship
        session = db.query(Session).filter(Session.id == session.id).first()
        messages = session.messages

        assert len(messages) == 4
        for idx in range(4):
            assert messages[idx].sequence_number == idx

    def test_message_cascade_delete_with_session(self, db, test_user):
        """Test that deleting session cascades to messages"""
        session = Session(user_id=test_user.id)
        db.add(session)
        db.flush()

        message = Message(
            session_id=session.id,
            role=MessageRole.USER,
            content="Test message",
            sequence_number=0
        )
        db.add(message)
        db.commit()
        message_id = message.id

        db.delete(session)
        db.commit()

        deleted_message = db.query(Message).filter(Message.id == message_id).first()
        assert deleted_message is None

    def test_message_with_metadata(self, db, test_user):
        """Test message with custom metadata"""
        session = Session(user_id=test_user.id)
        db.add(session)
        db.flush()

        message = Message(
            session_id=session.id,
            role=MessageRole.USER,
            content="Test",
            sequence_number=0,
            meta={"source": "web", "confidence": 0.95}
        )
        db.add(message)
        db.commit()
        db.refresh(message)

        assert message.meta["source"] == "web"
        assert message.meta["confidence"] == 0.95

    def test_message_repr(self, db, test_user):
        """Test message string representation"""
        session = Session(user_id=test_user.id)
        db.add(session)
        db.flush()

        message = Message(
            session_id=session.id,
            role=MessageRole.ASSISTANT,
            content="Test content",
            sequence_number=0
        )
        db.add(message)
        db.commit()

        repr_str = repr(message)
        assert "Message" in repr_str
        assert str(message.id) in repr_str
        assert "assistant" in repr_str


class TestTraceStepModel:
    """Test cases for TraceStep model"""

    def test_create_trace_step(self, db, test_user):
        """Test creating a trace step"""
        session = Session(user_id=test_user.id)
        db.add(session)
        db.flush()

        step = TraceStep(
            session_id=session.id,
            step_number=0,
            step_type=TraceStepType.THOUGHT,
            content="I need to search for information"
        )
        db.add(step)
        db.commit()
        db.refresh(step)

        assert step.id is not None
        assert step.session_id == session.id
        assert step.step_number == 0
        assert step.step_type == TraceStepType.THOUGHT
        assert step.content == "I need to search for information"
        assert step.meta == {}

    def test_trace_step_types(self, db, test_user):
        """Test all trace step types"""
        session = Session(user_id=test_user.id)
        db.add(session)
        db.flush()

        step_types = [
            TraceStepType.THOUGHT,
            TraceStepType.TOOL_CALL,
            TraceStepType.TOOL_RESULT,
            TraceStepType.REFLECTION,
            TraceStepType.ERROR,
            TraceStepType.OBSERVATION,
            TraceStepType.FINAL_ANSWER
        ]

        for idx, step_type in enumerate(step_types):
            step = TraceStep(
                session_id=session.id,
                step_number=idx,
                step_type=step_type,
                content=f"Step of type {step_type.value}"
            )
            db.add(step)

        db.commit()

        steps = db.query(TraceStep).filter(TraceStep.session_id == session.id).order_by(TraceStep.step_number).all()
        assert len(steps) == 7
        for idx, step_type in enumerate(step_types):
            assert steps[idx].step_type == step_type

    def test_trace_step_tool_call(self, db, test_user):
        """Test trace step for tool call"""
        session = Session(user_id=test_user.id)
        db.add(session)
        db.flush()

        step = TraceStep(
            session_id=session.id,
            step_number=0,
            step_type=TraceStepType.TOOL_CALL,
            tool_name="search_web",
            tool_input={"query": "LangChain documentation", "num_results": 5},
            latency_ms=150
        )
        db.add(step)
        db.commit()
        db.refresh(step)

        assert step.tool_name == "search_web"
        assert step.tool_input["query"] == "LangChain documentation"
        assert step.tool_input["num_results"] == 5
        assert step.latency_ms == 150

    def test_trace_step_tool_result(self, db, test_user):
        """Test trace step for tool result"""
        session = Session(user_id=test_user.id)
        db.add(session)
        db.flush()

        step = TraceStep(
            session_id=session.id,
            step_number=0,
            step_type=TraceStepType.TOOL_RESULT,
            tool_name="search_web",
            tool_output={"results": ["Result 1", "Result 2"], "count": 2},
            latency_ms=200
        )
        db.add(step)
        db.commit()
        db.refresh(step)

        assert step.tool_output["results"] == ["Result 1", "Result 2"]
        assert step.tool_output["count"] == 2

    def test_trace_step_ordering(self, db, test_user):
        """Test trace steps ordered by step_number"""
        session = Session(user_id=test_user.id)
        db.add(session)
        db.flush()

        # Add steps out of order
        for step_num in [2, 0, 3, 1]:
            step = TraceStep(
                session_id=session.id,
                step_number=step_num,
                step_type=TraceStepType.THOUGHT,
                content=f"Step {step_num}"
            )
            db.add(step)

        db.commit()

        # Query steps - should be ordered by step_number via relationship
        session = db.query(Session).filter(Session.id == session.id).first()
        steps = session.trace_steps

        assert len(steps) == 4
        for idx in range(4):
            assert steps[idx].step_number == idx

    def test_trace_step_cascade_delete_with_session(self, db, test_user):
        """Test that deleting session cascades to trace steps"""
        session = Session(user_id=test_user.id)
        db.add(session)
        db.flush()

        step = TraceStep(
            session_id=session.id,
            step_number=0,
            step_type=TraceStepType.THOUGHT,
            content="Test step"
        )
        db.add(step)
        db.commit()
        step_id = step.id

        db.delete(session)
        db.commit()

        deleted_step = db.query(TraceStep).filter(TraceStep.id == step_id).first()
        assert deleted_step is None

    def test_trace_step_with_metadata(self, db, test_user):
        """Test trace step with custom metadata"""
        session = Session(user_id=test_user.id)
        db.add(session)
        db.flush()

        step = TraceStep(
            session_id=session.id,
            step_number=0,
            step_type=TraceStepType.REFLECTION,
            content="Analyzing previous results",
            meta={"iteration": 2, "confidence": 0.8}
        )
        db.add(step)
        db.commit()
        db.refresh(step)

        assert step.meta["iteration"] == 2
        assert step.meta["confidence"] == 0.8

    def test_trace_step_repr(self, db, test_user):
        """Test trace step string representation"""
        session = Session(user_id=test_user.id)
        db.add(session)
        db.flush()

        step = TraceStep(
            session_id=session.id,
            step_number=0,
            step_type=TraceStepType.TOOL_CALL,
            tool_name="test_tool"
        )
        db.add(step)
        db.commit()

        repr_str = repr(step)
        assert "TraceStep" in repr_str
        assert str(step.id) in repr_str
        assert "tool_call" in repr_str


class TestSessionRelationships:
    """Test cases for Session relationships with messages and trace steps"""

    def test_session_with_messages_and_traces(self, db, test_user):
        """Test session with both messages and trace steps"""
        session = Session(user_id=test_user.id, title="Full Test Session")
        db.add(session)
        db.flush()

        # Add messages
        for i in range(3):
            message = Message(
                session_id=session.id,
                role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
                content=f"Message {i}",
                sequence_number=i
            )
            db.add(message)

        # Add trace steps
        for i in range(5):
            step = TraceStep(
                session_id=session.id,
                step_number=i,
                step_type=TraceStepType.THOUGHT,
                content=f"Step {i}"
            )
            db.add(step)

        db.commit()
        db.refresh(session)

        assert len(session.messages) == 3
        assert len(session.trace_steps) == 5

    def test_complete_session_lifecycle(self, db, test_user):
        """Test a complete session lifecycle"""
        # Create agent
        agent = Agent(
            user_id=test_user.id,
            name="Lifecycle Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.flush()

        # Create session
        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            title="Lifecycle Test",
            status=SessionStatus.PENDING
        )
        db.add(session)
        db.flush()

        # Start session
        session.status = SessionStatus.RUNNING

        # Add user message
        user_msg = Message(
            session_id=session.id,
            role=MessageRole.USER,
            content="What is the weather?",
            sequence_number=0
        )
        db.add(user_msg)

        # Add thought trace
        thought = TraceStep(
            session_id=session.id,
            step_number=0,
            step_type=TraceStepType.THOUGHT,
            content="I need to use the weather tool"
        )
        db.add(thought)

        # Add tool call trace
        tool_call = TraceStep(
            session_id=session.id,
            step_number=1,
            step_type=TraceStepType.TOOL_CALL,
            tool_name="get_weather",
            tool_input={"location": "San Francisco"}
        )
        db.add(tool_call)

        # Add assistant response
        assistant_msg = Message(
            session_id=session.id,
            role=MessageRole.ASSISTANT,
            content="The weather in San Francisco is sunny.",
            sequence_number=1
        )
        db.add(assistant_msg)

        # Complete session
        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        session.total_latency_ms = 1500
        session.token_usage_input = 50
        session.token_usage_output = 30

        db.commit()
        db.refresh(session)

        assert session.status == SessionStatus.COMPLETED
        assert len(session.messages) == 2
        assert len(session.trace_steps) == 2
        assert session.total_latency_ms == 1500
