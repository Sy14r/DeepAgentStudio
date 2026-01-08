"""
Tests for Span Service (Enhanced Tracing System)

Tests the SpanRecorder and SpanService classes for hierarchical tracing.
"""
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.models.session import Session, SessionStatus, Span, SpanType, SpanStatus
from app.models.agent import Agent
from app.models.agent_type import AgentTypeConfig, ExecutionStrategy, StrategyType
from app.services.span_recorder import SpanRecorder, SpanContext, create_span_recorder
from app.services.span_service import SpanService, create_span_service


@pytest.fixture
def test_agent_type(db, test_user):
    """Create a test agent type configuration."""
    agent_type = AgentTypeConfig(
        user_id=test_user.id,
        name="Test ReAct Type",
        description="A test agent type for spans",
        execution_strategy=ExecutionStrategy.react,
        strategy_type=StrategyType.builtin,
        is_builtin=False,
        is_active=True,
    )
    db.add(agent_type)
    db.commit()
    db.refresh(agent_type)
    return agent_type


class TestSpanRecorder:
    """Test cases for SpanRecorder service"""

    def test_create_span_recorder(self, db, test_user, test_agent_type):
        """Test creating a span recorder instance"""
        # Create a session first
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.RUNNING
        )
        db.add(session)
        db.commit()

        recorder = create_span_recorder(db, session.id)

        assert recorder.session_id == session.id
        assert recorder.trace_id is not None
        assert recorder.current_span is None

    def test_start_span_manually(self, db, test_user, test_agent_type):
        """Test manually starting a span"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.RUNNING
        )
        db.add(session)
        db.commit()

        recorder = SpanRecorder(db, session.id)
        span = recorder.start_span(SpanType.AGENT, "Test Agent Run")

        assert span.id is not None
        assert span.session_id == session.id
        assert span.span_type == SpanType.AGENT
        assert span.name == "Test Agent Run"
        assert span.status == SpanStatus.RUNNING
        assert span.started_at is not None
        assert span.parent_span_id is None
        assert span.depth == 0

    def test_end_span_manually(self, db, test_user, test_agent_type):
        """Test manually ending a span"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.RUNNING
        )
        db.add(session)
        db.commit()

        recorder = SpanRecorder(db, session.id)
        span = recorder.start_span(SpanType.LLM, "GPT-4 Call")

        # End the span with results
        updated_span = recorder.end_span(
            span,
            status=SpanStatus.SUCCESS,
            output={"content": "Hello world"},
            tokens_input=100,
            tokens_output=50,
            cost_usd=0.0015
        )

        assert updated_span.status == SpanStatus.SUCCESS
        assert updated_span.ended_at is not None
        assert updated_span.duration_ms is not None
        assert updated_span.duration_ms >= 0
        assert updated_span.tokens_input == 100
        assert updated_span.tokens_output == 50
        assert updated_span.tokens_total == 150
        assert updated_span.cost_usd == Decimal("0.0015")

    def test_nested_spans(self, db, test_user, test_agent_type):
        """Test creating nested spans with parent-child relationships"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.RUNNING
        )
        db.add(session)
        db.commit()

        recorder = SpanRecorder(db, session.id)

        # Create parent span
        parent = recorder.start_span(SpanType.AGENT, "Agent Run")

        # Create child span
        child = recorder.start_span(
            SpanType.LLM, "LLM Call",
            parent_span_id=parent.id,
            depth=1
        )

        # Create grandchild span
        grandchild = recorder.start_span(
            SpanType.TOOL, "Tool Call",
            parent_span_id=child.id,
            depth=2
        )

        assert parent.parent_span_id is None
        assert parent.depth == 0

        assert child.parent_span_id == parent.id
        assert child.depth == 1

        assert grandchild.parent_span_id == child.id
        assert grandchild.depth == 2

    def test_span_context_manager(self, db, test_user, test_agent_type):
        """Test using span as context manager"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.RUNNING
        )
        db.add(session)
        db.commit()

        recorder = SpanRecorder(db, session.id)

        with recorder.span(SpanType.AGENT, "Agent Execution") as ctx:
            ctx.set_input({"message": "Hello"})

            # Verify span is current
            assert recorder.current_span is not None
            assert recorder.current_span.id == ctx.id

            ctx.set_output({"response": "Hi there"})

        # After context exit, span should be completed
        db.refresh(ctx.span)
        assert ctx.span.status == SpanStatus.SUCCESS
        assert ctx.span.ended_at is not None
        assert ctx.span.duration_ms is not None

        # Current span should be cleared
        assert recorder.current_span is None

    def test_span_context_manager_nested(self, db, test_user, test_agent_type):
        """Test nested context managers"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.RUNNING
        )
        db.add(session)
        db.commit()

        recorder = SpanRecorder(db, session.id)

        with recorder.span(SpanType.AGENT, "Parent") as parent_ctx:
            assert recorder.current_span.id == parent_ctx.id
            assert parent_ctx.span.depth == 0

            with recorder.span(SpanType.LLM, "Child") as child_ctx:
                assert recorder.current_span.id == child_ctx.id
                assert child_ctx.span.parent_span_id == parent_ctx.id
                assert child_ctx.span.depth == 1

            # After child exits, parent should be current again
            assert recorder.current_span.id == parent_ctx.id

    def test_span_context_error_handling(self, db, test_user, test_agent_type):
        """Test span context manager handles exceptions"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.RUNNING
        )
        db.add(session)
        db.commit()

        recorder = SpanRecorder(db, session.id)
        span_id = None

        with pytest.raises(ValueError):
            with recorder.span(SpanType.TOOL, "Failing Tool") as ctx:
                span_id = ctx.id
                raise ValueError("Tool execution failed")

        # Span should be marked as error
        span = db.query(Span).filter(Span.id == span_id).first()
        assert span.status == SpanStatus.ERROR
        assert span.error_message == "Tool execution failed"
        assert span.error_type == "ValueError"

    def test_span_set_tokens(self, db, test_user, test_agent_type):
        """Test setting token usage"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.RUNNING
        )
        db.add(session)
        db.commit()

        recorder = SpanRecorder(db, session.id)

        with recorder.span(SpanType.LLM, "LLM Call") as ctx:
            ctx.set_tokens(input_tokens=200, output_tokens=100)

        db.refresh(ctx.span)
        assert ctx.span.tokens_input == 200
        assert ctx.span.tokens_output == 100
        assert ctx.span.tokens_total == 300

    def test_span_set_model(self, db, test_user, test_agent_type):
        """Test setting model information"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.RUNNING
        )
        db.add(session)
        db.commit()

        recorder = SpanRecorder(db, session.id)

        with recorder.span(SpanType.LLM, "GPT-4o") as ctx:
            ctx.set_model("gpt-4o", provider="openai", parameters={"temperature": 0.7})

        db.refresh(ctx.span)
        assert ctx.span.model_name == "gpt-4o"
        assert ctx.span.model_provider == "openai"

    def test_record_thought(self, db, test_user, test_agent_type):
        """Test recording a thought span"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.RUNNING
        )
        db.add(session)
        db.commit()

        recorder = SpanRecorder(db, session.id)
        span = recorder.record_thought("I need to search the web")

        assert span.span_type == SpanType.THOUGHT
        assert span.status == SpanStatus.SUCCESS  # Thoughts complete immediately

    def test_record_error(self, db, test_user, test_agent_type):
        """Test recording an error span"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.RUNNING
        )
        db.add(session)
        db.commit()

        recorder = SpanRecorder(db, session.id)

        try:
            raise RuntimeError("Something went wrong")
        except Exception as e:
            span = recorder.record_error(e, include_stack=True)

        assert span.span_type == SpanType.ERROR
        assert span.status == SpanStatus.ERROR
        assert span.error_message == "Something went wrong"
        assert span.error_type == "RuntimeError"
        assert span.error_stack is not None

    def test_get_trace_summary(self, db, test_user, test_agent_type):
        """Test getting trace summary"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.RUNNING
        )
        db.add(session)
        db.commit()

        recorder = SpanRecorder(db, session.id)

        with recorder.span(SpanType.AGENT, "Agent") as agent_ctx:
            with recorder.span(SpanType.LLM, "LLM") as llm_ctx:
                llm_ctx.set_tokens(100, 50)
                llm_ctx.set_cost(0.0015)

        summary = recorder.get_trace_summary()

        assert summary["session_id"] == session.id
        assert summary["span_count"] == 2
        assert summary["root_span_name"] == "Agent"
        assert summary["total_tokens"] == 150
        assert summary["total_cost_usd"] == 0.0015


class TestSpanService:
    """Test cases for SpanService CRUD operations"""

    def test_get_span(self, db, test_user, test_agent_type):
        """Test getting a single span"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.RUNNING
        )
        db.add(session)
        db.commit()

        recorder = SpanRecorder(db, session.id)
        span = recorder.start_span(SpanType.AGENT, "Test Span")
        recorder.end_span(span)

        service = SpanService(db)
        retrieved = service.get_span(session.id, span.id)

        assert retrieved is not None
        assert retrieved.id == span.id
        assert retrieved.name == "Test Span"

    def test_get_span_not_found(self, db, test_user, test_agent_type):
        """Test getting non-existent span"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.RUNNING
        )
        db.add(session)
        db.commit()

        service = SpanService(db)
        span = service.get_span(session.id, 99999)

        assert span is None

    def test_list_spans(self, db, test_user, test_agent_type):
        """Test listing spans for a session"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.RUNNING
        )
        db.add(session)
        db.commit()

        recorder = SpanRecorder(db, session.id)

        # Create multiple spans
        for i in range(5):
            span = recorder.start_span(SpanType.TOOL, f"Tool {i}")
            recorder.end_span(span)

        service = SpanService(db)
        spans, total = service.list_spans(session.id)

        assert total == 5
        assert len(spans) == 5

    def test_list_spans_pagination(self, db, test_user, test_agent_type):
        """Test span listing with pagination"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.RUNNING
        )
        db.add(session)
        db.commit()

        recorder = SpanRecorder(db, session.id)

        # Create 10 spans
        for i in range(10):
            span = recorder.start_span(SpanType.TOOL, f"Tool {i}")
            recorder.end_span(span)

        service = SpanService(db)

        # Page 1
        spans, total = service.list_spans(session.id, page=1, page_size=3)
        assert total == 10
        assert len(spans) == 3

        # Page 2
        spans, total = service.list_spans(session.id, page=2, page_size=3)
        assert total == 10
        assert len(spans) == 3

    def test_get_span_tree(self, db, test_user, test_agent_type):
        """Test getting hierarchical span tree"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.RUNNING
        )
        db.add(session)
        db.commit()

        recorder = SpanRecorder(db, session.id)

        with recorder.span(SpanType.AGENT, "Agent") as agent_ctx:
            with recorder.span(SpanType.LLM, "LLM Call") as llm_ctx:
                llm_ctx.set_tokens(100, 50)
            with recorder.span(SpanType.TOOL, "Web Search") as tool_ctx:
                pass

        service = SpanService(db)
        tree = service.get_span_tree(session.id)

        assert tree.trace_id == recorder.trace_id
        assert tree.root_span is not None
        assert tree.root_span.name == "Agent"
        assert len(tree.root_span.children) == 2

        # Check stats
        assert tree.stats.total_spans == 3
        assert tree.stats.total_tokens == 150
        assert tree.stats.span_count_by_type["agent"] == 1
        assert tree.stats.span_count_by_type["llm"] == 1
        assert tree.stats.span_count_by_type["tool"] == 1

    def test_get_span_stats(self, db, test_user, test_agent_type):
        """Test getting span statistics"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.RUNNING
        )
        db.add(session)
        db.commit()

        recorder = SpanRecorder(db, session.id)

        # Create spans with various types
        with recorder.span(SpanType.AGENT, "Agent") as ctx:
            ctx.set_tokens(0, 0)

        with recorder.span(SpanType.LLM, "LLM 1") as ctx:
            ctx.set_tokens(100, 50)
            ctx.set_cost(0.0015)

        with recorder.span(SpanType.LLM, "LLM 2") as ctx:
            ctx.set_tokens(200, 100)
            ctx.set_cost(0.003)

        # Create an error span
        try:
            with recorder.span(SpanType.TOOL, "Failing Tool"):
                raise ValueError("Error")
        except ValueError:
            pass

        service = SpanService(db)
        stats = service.get_span_stats(session.id)

        assert stats.total_spans == 4
        assert stats.total_tokens == 450
        assert stats.total_tokens_input == 300
        assert stats.total_tokens_output == 150
        assert stats.total_cost_usd == Decimal("0.0045")
        assert stats.error_count == 1
        assert stats.span_count_by_type["agent"] == 1
        assert stats.span_count_by_type["llm"] == 2
        assert stats.span_count_by_type["tool"] == 1
        assert stats.span_count_by_status["success"] == 3
        assert stats.span_count_by_status["error"] == 1

    def test_get_traces_for_session(self, db, test_user, test_agent_type):
        """Test listing traces for a session"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.RUNNING
        )
        db.add(session)
        db.commit()

        # Create first trace
        recorder1 = SpanRecorder(db, session.id)
        with recorder1.span(SpanType.AGENT, "Agent Run 1"):
            pass

        # Create second trace (different trace_id)
        recorder2 = SpanRecorder(db, session.id)
        with recorder2.span(SpanType.AGENT, "Agent Run 2"):
            with recorder2.span(SpanType.LLM, "LLM"):
                pass

        service = SpanService(db)
        traces = service.get_traces_for_session(session.id)

        assert len(traces) == 2
        # Should be ordered by started_at desc (newest first)
        assert traces[0]["span_count"] == 2  # Second trace has 2 spans
        assert traces[1]["span_count"] == 1  # First trace has 1 span

    def test_delete_spans_for_session(self, db, test_user, test_agent_type):
        """Test deleting all spans for a session"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.RUNNING
        )
        db.add(session)
        db.commit()

        recorder = SpanRecorder(db, session.id)

        # Create multiple spans
        for i in range(5):
            span = recorder.start_span(SpanType.TOOL, f"Tool {i}")
            recorder.end_span(span)

        service = SpanService(db)

        # Verify spans exist
        spans, total = service.list_spans(session.id)
        assert total == 5

        # Delete
        deleted = service.delete_spans_for_session(session.id)
        assert deleted == 5

        # Verify deleted
        spans, total = service.list_spans(session.id)
        assert total == 0
