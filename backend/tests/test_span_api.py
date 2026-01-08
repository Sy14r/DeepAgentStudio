"""
Tests for Span API endpoints (Enhanced Tracing System)

Tests the REST API endpoints for span management.
"""
import pytest
from fastapi.testclient import TestClient

from app.models.session import Session, SessionStatus, Span, SpanType, SpanStatus
from app.models.agent import Agent
from app.models.agent_type import AgentTypeConfig, ExecutionStrategy, StrategyType
from app.services.span_recorder import SpanRecorder


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


class TestSpanAPIEndpoints:
    """Test cases for Span API endpoints"""

    def test_list_spans(self, client, auth_headers, test_user, db, test_agent_type):
        """Test listing spans for a session"""
        # Create agent and session
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.COMPLETED
        )
        db.add(session)
        db.commit()

        # Create spans using recorder
        recorder = SpanRecorder(db, session.id)
        span1 = recorder.start_span(SpanType.AGENT, "Agent Run")
        recorder.end_span(span1)

        span2 = recorder.start_span(SpanType.LLM, "LLM Call", parent_span_id=span1.id, depth=1)
        recorder.end_span(span2, tokens_input=100, tokens_output=50)

        response = client.get(
            f"/api/v1/sessions/{session.id}/spans",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["spans"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 50

    def test_list_spans_pagination(self, client, auth_headers, test_user, db, test_agent_type):
        """Test span listing with pagination"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.COMPLETED
        )
        db.add(session)
        db.commit()

        # Create 10 spans
        recorder = SpanRecorder(db, session.id)
        for i in range(10):
            span = recorder.start_span(SpanType.TOOL, f"Tool {i}")
            recorder.end_span(span)

        response = client.get(
            f"/api/v1/sessions/{session.id}/spans?page=1&page_size=3",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert len(data["spans"]) == 3
        assert data["page"] == 1
        assert data["page_size"] == 3

    def test_list_spans_filter_by_type(self, client, auth_headers, test_user, db, test_agent_type):
        """Test filtering spans by type"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.COMPLETED
        )
        db.add(session)
        db.commit()

        recorder = SpanRecorder(db, session.id)

        # Create different span types
        span1 = recorder.start_span(SpanType.AGENT, "Agent")
        recorder.end_span(span1)

        span2 = recorder.start_span(SpanType.LLM, "LLM")
        recorder.end_span(span2)

        span3 = recorder.start_span(SpanType.TOOL, "Tool")
        recorder.end_span(span3)

        response = client.get(
            f"/api/v1/sessions/{session.id}/spans?span_type=llm",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["spans"][0]["span_type"] == "llm"

    def test_list_spans_filter_by_status(self, client, auth_headers, test_user, db, test_agent_type):
        """Test filtering spans by status"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.COMPLETED
        )
        db.add(session)
        db.commit()

        recorder = SpanRecorder(db, session.id)

        # Create success span
        span1 = recorder.start_span(SpanType.TOOL, "Success Tool")
        recorder.end_span(span1, status=SpanStatus.SUCCESS)

        # Create error span
        span2 = recorder.start_span(SpanType.TOOL, "Error Tool")
        recorder.end_span(span2, status=SpanStatus.ERROR, error_message="Failed")

        response = client.get(
            f"/api/v1/sessions/{session.id}/spans?status=error",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["spans"][0]["status"] == "error"

    def test_list_spans_session_not_found(self, client, auth_headers):
        """Test listing spans for non-existent session"""
        response = client.get(
            "/api/v1/sessions/99999/spans",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_list_spans_unauthorized(self, client, test_user, db, second_test_user, test_agent_type):
        """Test listing spans for another user's session"""
        # Create session for second user
        agent = Agent(user_id=second_test_user.id, name="Other Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=second_test_user.id,
            agent_id=agent.id,
            status=SessionStatus.COMPLETED
        )
        db.add(session)
        db.commit()

        # Login as first user
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "testpassword123"}
        )
        token = response.json()["access_token"]

        # Try to access second user's session
        response = client.get(
            f"/api/v1/sessions/{session.id}/spans",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404

    def test_get_span(self, client, auth_headers, test_user, db, test_agent_type):
        """Test getting a single span"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.COMPLETED
        )
        db.add(session)
        db.commit()

        recorder = SpanRecorder(db, session.id)
        span = recorder.start_span(SpanType.LLM, "GPT-4o Call")
        recorder.end_span(span, tokens_input=100, tokens_output=50)

        response = client.get(
            f"/api/v1/sessions/{session.id}/spans/{span.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == span.id
        assert data["name"] == "GPT-4o Call"
        assert data["span_type"] == "llm"
        assert data["tokens_input"] == 100
        assert data["tokens_output"] == 50

    def test_get_span_not_found(self, client, auth_headers, test_user, db, test_agent_type):
        """Test getting non-existent span"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.COMPLETED
        )
        db.add(session)
        db.commit()

        response = client.get(
            f"/api/v1/sessions/{session.id}/spans/99999",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_get_span_tree(self, client, auth_headers, test_user, db, test_agent_type):
        """Test getting span tree"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.COMPLETED
        )
        db.add(session)
        db.commit()

        recorder = SpanRecorder(db, session.id)

        with recorder.span(SpanType.AGENT, "Agent Run") as agent_ctx:
            with recorder.span(SpanType.LLM, "LLM Call") as llm_ctx:
                llm_ctx.set_tokens(100, 50)
            with recorder.span(SpanType.TOOL, "Web Search") as tool_ctx:
                pass

        response = client.get(
            f"/api/v1/sessions/{session.id}/spans/tree",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "trace_id" in data
        assert "root_span" in data
        assert "stats" in data

        # Check root span
        root = data["root_span"]
        assert root["name"] == "Agent Run"
        assert root["span_type"] == "agent"
        assert len(root["children"]) == 2

        # Check stats
        stats = data["stats"]
        assert stats["total_spans"] == 3
        assert stats["total_tokens"] == 150

    def test_get_span_tree_empty(self, client, auth_headers, test_user, db, test_agent_type):
        """Test getting span tree for session with no spans"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.COMPLETED
        )
        db.add(session)
        db.commit()

        response = client.get(
            f"/api/v1/sessions/{session.id}/spans/tree",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["root_span"] is None
        assert data["stats"]["total_spans"] == 0

    def test_get_span_stats(self, client, auth_headers, test_user, db, test_agent_type):
        """Test getting span statistics"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.COMPLETED
        )
        db.add(session)
        db.commit()

        recorder = SpanRecorder(db, session.id)

        # Create success span
        with recorder.span(SpanType.LLM, "LLM 1") as ctx:
            ctx.set_tokens(100, 50)
            ctx.set_cost(0.0015)

        # Create another success span
        with recorder.span(SpanType.LLM, "LLM 2") as ctx:
            ctx.set_tokens(200, 100)
            ctx.set_cost(0.003)

        # Create error span
        try:
            with recorder.span(SpanType.TOOL, "Error Tool"):
                raise ValueError("Test error")
        except ValueError:
            pass

        response = client.get(
            f"/api/v1/sessions/{session.id}/spans/stats",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_spans"] == 3
        assert data["total_tokens"] == 450
        assert data["total_tokens_input"] == 300
        assert data["total_tokens_output"] == 150
        assert data["error_count"] == 1
        assert data["span_count_by_type"]["llm"] == 2
        assert data["span_count_by_type"]["tool"] == 1
        assert data["span_count_by_status"]["success"] == 2
        assert data["span_count_by_status"]["error"] == 1

    def test_list_traces(self, client, auth_headers, test_user, db, test_agent_type):
        """Test listing traces for a session"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.COMPLETED
        )
        db.add(session)
        db.commit()

        # Create first trace
        recorder1 = SpanRecorder(db, session.id)
        with recorder1.span(SpanType.AGENT, "Agent Run 1"):
            pass

        # Create second trace
        recorder2 = SpanRecorder(db, session.id)
        with recorder2.span(SpanType.AGENT, "Agent Run 2"):
            with recorder2.span(SpanType.LLM, "LLM"):
                pass

        response = client.get(
            f"/api/v1/sessions/{session.id}/spans/traces",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        # Most recent first
        trace_counts = [t["span_count"] for t in data]
        assert 1 in trace_counts
        assert 2 in trace_counts

    def test_unauthenticated_access(self, client, test_user, db, test_agent_type):
        """Test accessing span endpoints without authentication"""
        agent = Agent(user_id=test_user.id, name="Test Agent", agent_type_id=test_agent_type.id)
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.COMPLETED
        )
        db.add(session)
        db.commit()

        # No auth headers
        response = client.get(f"/api/v1/sessions/{session.id}/spans")
        assert response.status_code == 401

        response = client.get(f"/api/v1/sessions/{session.id}/spans/tree")
        assert response.status_code == 401

        response = client.get(f"/api/v1/sessions/{session.id}/spans/stats")
        assert response.status_code == 401

        response = client.get(f"/api/v1/sessions/{session.id}/spans/traces")
        assert response.status_code == 401
