"""
Tests for Session API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from app.models.session import Session, Message, TraceStep, SessionStatus, MessageRole, TraceStepType
from app.models.agent import Agent, AgentVersion, AgentType


class TestSessionAPIEndpoints:
    """Test cases for Session CRUD API endpoints"""

    def test_create_session(self, client, auth_headers, test_user, db):
        """Test creating a session via API"""
        # Create agent first
        agent = Agent(
            user_id=test_user.id,
            name="API Test Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.commit()

        session_data = {
            "agent_id": agent.id,
            "title": "Test Session",
            "meta": {"source": "api_test"}
        }

        response = client.post(
            "/api/v1/sessions",
            json=session_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["agent_id"] == agent.id
        assert data["title"] == "Test Session"
        assert data["status"] == "pending"
        assert data["meta"]["source"] == "api_test"
        assert data["messages"] == []
        assert data["trace_steps"] == []

    def test_create_session_minimal(self, client, auth_headers, test_user, db):
        """Test creating session with minimal data"""
        agent = Agent(
            user_id=test_user.id,
            name="Minimal Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.commit()

        session_data = {"agent_id": agent.id}

        response = client.post(
            "/api/v1/sessions",
            json=session_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] is None
        assert data["meta"] == {}

    def test_create_session_with_agent_version(self, client, auth_headers, test_user, db):
        """Test creating session with specific agent version"""
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
            config={},
            created_by=test_user.id
        )
        db.add(version)
        db.commit()

        session_data = {
            "agent_id": agent.id,
            "agent_version_id": version.id
        }

        response = client.post(
            "/api/v1/sessions",
            json=session_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["agent_version_id"] == version.id

    def test_create_session_invalid_agent(self, client, auth_headers):
        """Test creating session with non-existent agent"""
        session_data = {"agent_id": 99999}

        response = client.post(
            "/api/v1/sessions",
            json=session_data,
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_list_sessions(self, client, auth_headers, test_user, db):
        """Test listing sessions"""
        agent = Agent(
            user_id=test_user.id,
            name="List Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.flush()

        # Create test sessions
        for i in range(3):
            session = Session(
                user_id=test_user.id,
                agent_id=agent.id,
                title=f"Session {i}"
            )
            db.add(session)
        db.commit()

        response = client.get("/api/v1/sessions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "total" in data
        assert data["total"] >= 3
        assert len(data["sessions"]) >= 3

    def test_list_sessions_filter_by_status(self, client, auth_headers, test_user, db):
        """Test filtering sessions by status"""
        agent = Agent(
            user_id=test_user.id,
            name="Filter Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.flush()

        # Create sessions with different statuses
        completed_session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.COMPLETED
        )
        failed_session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.FAILED
        )
        db.add_all([completed_session, failed_session])
        db.commit()

        response = client.get(
            "/api/v1/sessions?status_filter=completed",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        for session in data["sessions"]:
            assert session["status"] == "completed"

    def test_list_sessions_filter_by_agent(self, client, auth_headers, test_user, db):
        """Test filtering sessions by agent"""
        agent1 = Agent(
            user_id=test_user.id,
            name="Agent 1",
            agent_type=AgentType.REACT
        )
        agent2 = Agent(
            user_id=test_user.id,
            name="Agent 2",
            agent_type=AgentType.CONVERSATIONAL
        )
        db.add_all([agent1, agent2])
        db.flush()

        session1 = Session(user_id=test_user.id, agent_id=agent1.id)
        session2 = Session(user_id=test_user.id, agent_id=agent2.id)
        db.add_all([session1, session2])
        db.commit()

        response = client.get(
            f"/api/v1/sessions?agent_id={agent1.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        for session in data["sessions"]:
            assert session["agent_id"] == agent1.id

    def test_list_sessions_pagination(self, client, auth_headers, test_user, db):
        """Test session list pagination"""
        agent = Agent(
            user_id=test_user.id,
            name="Pagination Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.flush()

        # Create multiple sessions
        for i in range(5):
            session = Session(user_id=test_user.id, agent_id=agent.id)
            db.add(session)
        db.commit()

        response = client.get(
            "/api/v1/sessions?skip=0&limit=2",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2

    def test_get_session_by_id(self, client, auth_headers, test_user, db):
        """Test getting session by ID"""
        agent = Agent(
            user_id=test_user.id,
            name="Get Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.flush()

        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            title="Get Test Session"
        )
        db.add(session)
        db.commit()

        response = client.get(
            f"/api/v1/sessions/{session.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session.id
        assert data["title"] == "Get Test Session"
        assert "messages" in data
        assert "trace_steps" in data

    def test_get_session_not_found(self, client, auth_headers):
        """Test getting non-existent session returns 404"""
        response = client.get(
            "/api/v1/sessions/99999",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_update_session(self, client, auth_headers, test_user, db):
        """Test updating session metadata"""
        session = Session(
            user_id=test_user.id,
            title="Original Title",
            status=SessionStatus.PENDING
        )
        db.add(session)
        db.commit()

        update_data = {
            "title": "Updated Title",
            "status": "completed",
            "total_latency_ms": 1500,
            "token_usage_input": 100,
            "token_usage_output": 50,
            "total_cost": 0.05
        }

        response = client.put(
            f"/api/v1/sessions/{session.id}",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["status"] == "completed"
        assert data["total_latency_ms"] == 1500
        assert data["token_usage_input"] == 100
        assert data["token_usage_output"] == 50
        assert data["total_cost"] == 0.05

    def test_update_session_partial(self, client, auth_headers, test_user, db):
        """Test partial update of session"""
        session = Session(
            user_id=test_user.id,
            title="Original"
        )
        db.add(session)
        db.commit()

        # Only update status
        update_data = {"status": "running"}

        response = client.put(
            f"/api/v1/sessions/{session.id}",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["title"] == "Original"  # Unchanged

    def test_delete_session(self, client, auth_headers, test_user, db):
        """Test deleting a session"""
        session = Session(
            user_id=test_user.id,
            title="Delete Me"
        )
        db.add(session)
        db.commit()
        session_id = session.id

        response = client.delete(
            f"/api/v1/sessions/{session_id}",
            headers=auth_headers
        )

        assert response.status_code == 204

        # Verify deletion
        deleted = db.query(Session).filter(Session.id == session_id).first()
        assert deleted is None

    def test_unauthorized_access(self, client):
        """Test that endpoints require authentication"""
        response = client.get("/api/v1/sessions")
        assert response.status_code == 401


class TestMessageAPI:
    """Test cases for Message API endpoints"""

    def test_list_session_messages(self, client, auth_headers, test_user, db):
        """Test listing messages for a session"""
        session = Session(user_id=test_user.id)
        db.add(session)
        db.flush()

        # Create messages
        for i in range(3):
            message = Message(
                session_id=session.id,
                role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
                content=f"Message {i}",
                sequence_number=i
            )
            db.add(message)
        db.commit()

        response = client.get(
            f"/api/v1/sessions/{session.id}/messages",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        # Check ordering by sequence_number
        assert data[0]["sequence_number"] == 0
        assert data[1]["sequence_number"] == 1
        assert data[2]["sequence_number"] == 2

    def test_create_message(self, client, auth_headers, test_user, db):
        """Test creating a message"""
        session = Session(user_id=test_user.id)
        db.add(session)
        db.commit()

        message_data = {
            "role": "user",
            "content": "Hello, agent!",
            "meta": {"source": "test"}
        }

        response = client.post(
            f"/api/v1/sessions/{session.id}/messages",
            json=message_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "user"
        assert data["content"] == "Hello, agent!"
        assert data["sequence_number"] == 0  # Auto-assigned
        assert data["meta"]["source"] == "test"

    def test_create_message_auto_sequence(self, client, auth_headers, test_user, db):
        """Test auto-incrementing sequence number"""
        session = Session(user_id=test_user.id)
        db.add(session)
        db.commit()

        # Create first message
        response1 = client.post(
            f"/api/v1/sessions/{session.id}/messages",
            json={"role": "user", "content": "First"},
            headers=auth_headers
        )
        assert response1.json()["sequence_number"] == 0

        # Create second message
        response2 = client.post(
            f"/api/v1/sessions/{session.id}/messages",
            json={"role": "assistant", "content": "Second"},
            headers=auth_headers
        )
        assert response2.json()["sequence_number"] == 1

    def test_create_message_with_tool_calls(self, client, auth_headers, test_user, db):
        """Test creating message with tool calls"""
        session = Session(user_id=test_user.id)
        db.add(session)
        db.commit()

        message_data = {
            "role": "assistant",
            "content": "Let me search for that.",
            "tool_calls": [
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {"name": "search", "arguments": '{"query": "test"}'}
                }
            ]
        }

        response = client.post(
            f"/api/v1/sessions/{session.id}/messages",
            json=message_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["tool_calls"]) == 1
        assert data["tool_calls"][0]["id"] == "call_123"

    def test_create_message_invalid_session(self, client, auth_headers):
        """Test creating message for non-existent session"""
        message_data = {
            "role": "user",
            "content": "Test"
        }

        response = client.post(
            "/api/v1/sessions/99999/messages",
            json=message_data,
            headers=auth_headers
        )

        assert response.status_code == 404


class TestTraceStepAPI:
    """Test cases for TraceStep API endpoints"""

    def test_list_session_traces(self, client, auth_headers, test_user, db):
        """Test listing trace steps for a session"""
        session = Session(user_id=test_user.id)
        db.add(session)
        db.flush()

        # Create trace steps
        for i in range(3):
            step = TraceStep(
                session_id=session.id,
                step_number=i,
                step_type=TraceStepType.THOUGHT,
                content=f"Step {i}"
            )
            db.add(step)
        db.commit()

        response = client.get(
            f"/api/v1/sessions/{session.id}/traces",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        # Check ordering by step_number
        assert data[0]["step_number"] == 0
        assert data[1]["step_number"] == 1
        assert data[2]["step_number"] == 2

    def test_create_trace_step(self, client, auth_headers, test_user, db):
        """Test creating a trace step"""
        session = Session(user_id=test_user.id)
        db.add(session)
        db.commit()

        trace_data = {
            "step_type": "thought",
            "content": "I need to search for information",
            "meta": {"confidence": 0.9}
        }

        response = client.post(
            f"/api/v1/sessions/{session.id}/traces",
            json=trace_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["step_type"] == "thought"
        assert data["content"] == "I need to search for information"
        assert data["step_number"] == 0  # Auto-assigned
        assert data["meta"]["confidence"] == 0.9

    def test_create_trace_step_auto_step_number(self, client, auth_headers, test_user, db):
        """Test auto-incrementing step number"""
        session = Session(user_id=test_user.id)
        db.add(session)
        db.commit()

        # Create first step
        response1 = client.post(
            f"/api/v1/sessions/{session.id}/traces",
            json={"step_type": "thought", "content": "First"},
            headers=auth_headers
        )
        assert response1.json()["step_number"] == 0

        # Create second step
        response2 = client.post(
            f"/api/v1/sessions/{session.id}/traces",
            json={"step_type": "tool_call", "tool_name": "search"},
            headers=auth_headers
        )
        assert response2.json()["step_number"] == 1

    def test_create_trace_step_tool_call(self, client, auth_headers, test_user, db):
        """Test creating tool call trace step"""
        session = Session(user_id=test_user.id)
        db.add(session)
        db.commit()

        trace_data = {
            "step_type": "tool_call",
            "tool_name": "search_web",
            "tool_input": {"query": "LangChain", "num_results": 5},
            "latency_ms": 150
        }

        response = client.post(
            f"/api/v1/sessions/{session.id}/traces",
            json=trace_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["step_type"] == "tool_call"
        assert data["tool_name"] == "search_web"
        assert data["tool_input"]["query"] == "LangChain"
        assert data["latency_ms"] == 150

    def test_create_trace_step_invalid_session(self, client, auth_headers):
        """Test creating trace for non-existent session"""
        trace_data = {
            "step_type": "thought",
            "content": "Test"
        }

        response = client.post(
            "/api/v1/sessions/99999/traces",
            json=trace_data,
            headers=auth_headers
        )

        assert response.status_code == 404


class TestSessionStatistics:
    """Test cases for session statistics endpoints"""

    def test_get_session_statistics(self, client, auth_headers, test_user, db):
        """Test getting overall session statistics"""
        agent = Agent(
            user_id=test_user.id,
            name="Stats Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.flush()

        # Create sessions with different statuses and metrics
        completed1 = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.COMPLETED,
            total_latency_ms=1000,
            token_usage_input=50,
            token_usage_output=30,
            total_cost=0.02
        )
        completed2 = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.COMPLETED,
            total_latency_ms=1500,
            token_usage_input=60,
            token_usage_output=40,
            total_cost=0.03
        )
        failed = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.FAILED
        )
        db.add_all([completed1, completed2, failed])
        db.commit()

        response = client.get(
            "/api/v1/sessions/statistics/overview",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_sessions"] >= 3
        assert data["completed_sessions"] >= 2
        assert data["failed_sessions"] >= 1
        assert data["average_latency_ms"] == 1250.0  # Average of 1000 and 1500
        assert data["total_tokens_used"] >= 180  # 50+30+60+40
        assert data["total_cost"] >= 0.05
        assert data["success_rate"] > 0

    def test_get_agent_session_summary(self, client, auth_headers, test_user, db):
        """Test getting agent-specific session summary"""
        agent = Agent(
            user_id=test_user.id,
            name="Summary Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.flush()

        # Create sessions for this agent
        session1 = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.COMPLETED,
            total_latency_ms=1000,
            token_usage_input=50,
            token_usage_output=30,
            total_cost=0.02
        )
        session2 = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.FAILED
        )
        db.add_all([session1, session2])
        db.commit()

        response = client.get(
            f"/api/v1/sessions/agents/{agent.id}/summary",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == agent.id
        assert data["agent_name"] == "Summary Agent"
        assert data["session_count"] == 2
        assert data["success_count"] == 1
        assert data["failure_count"] == 1
        assert data["average_latency_ms"] == 1000.0
        assert data["total_tokens"] == 80
        assert data["total_cost"] == 0.02

    def test_get_agent_summary_invalid_agent(self, client, auth_headers):
        """Test getting summary for non-existent agent"""
        response = client.get(
            "/api/v1/sessions/agents/99999/summary",
            headers=auth_headers
        )

        assert response.status_code == 404


class TestSessionAccessControl:
    """Test cases for session access control"""

    def test_cannot_access_other_users_session(self, client, auth_headers, second_test_user, db):
        """Test that users cannot access other users' sessions"""
        # Create session for different user
        other_session = Session(
            user_id=second_test_user.id,
            title="Other User Session"
        )
        db.add(other_session)
        db.commit()

        response = client.get(
            f"/api/v1/sessions/{other_session.id}",
            headers=auth_headers
        )

        assert response.status_code == 404  # 404 for security

    def test_cannot_update_other_users_session(self, client, auth_headers, second_test_user, db):
        """Test that users cannot update other users' sessions"""
        other_session = Session(
            user_id=second_test_user.id,
            title="Other User Session"
        )
        db.add(other_session)
        db.commit()

        response = client.put(
            f"/api/v1/sessions/{other_session.id}",
            json={"title": "Hacked Title"},
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_cannot_delete_other_users_session(self, client, auth_headers, second_test_user, db):
        """Test that users cannot delete other users' sessions"""
        other_session = Session(
            user_id=second_test_user.id,
            title="Other User Session"
        )
        db.add(other_session)
        db.commit()

        response = client.delete(
            f"/api/v1/sessions/{other_session.id}",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_cannot_add_message_to_other_users_session(self, client, auth_headers, second_test_user, db):
        """Test that users cannot add messages to other users' sessions"""
        other_session = Session(user_id=second_test_user.id)
        db.add(other_session)
        db.commit()

        response = client.post(
            f"/api/v1/sessions/{other_session.id}/messages",
            json={"role": "user", "content": "Test"},
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_cannot_add_trace_to_other_users_session(self, client, auth_headers, second_test_user, db):
        """Test that users cannot add traces to other users' sessions"""
        other_session = Session(user_id=second_test_user.id)
        db.add(other_session)
        db.commit()

        response = client.post(
            f"/api/v1/sessions/{other_session.id}/traces",
            json={"step_type": "thought", "content": "Test"},
            headers=auth_headers
        )

        assert response.status_code == 404


class TestCompleteSessionWorkflow:
    """Test cases for complete session workflow"""

    def test_full_session_lifecycle(self, client, auth_headers, test_user, db):
        """Test complete session from creation to completion"""
        # Create agent
        agent = Agent(
            user_id=test_user.id,
            name="Lifecycle Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.commit()

        # 1. Create session
        session_response = client.post(
            "/api/v1/sessions",
            json={"agent_id": agent.id, "title": "Full Lifecycle Test"},
            headers=auth_headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["id"]

        # 2. Update status to running
        client.put(
            f"/api/v1/sessions/{session_id}",
            json={"status": "running"},
            headers=auth_headers
        )

        # 3. Add user message
        user_msg_response = client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"role": "user", "content": "What is the weather?"},
            headers=auth_headers
        )
        assert user_msg_response.status_code == 201

        # 4. Add thought trace
        client.post(
            f"/api/v1/sessions/{session_id}/traces",
            json={"step_type": "thought", "content": "I need to use weather tool"},
            headers=auth_headers
        )

        # 5. Add tool call trace
        client.post(
            f"/api/v1/sessions/{session_id}/traces",
            json={
                "step_type": "tool_call",
                "tool_name": "get_weather",
                "tool_input": {"location": "SF"}
            },
            headers=auth_headers
        )

        # 6. Add assistant message
        assistant_msg_response = client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"role": "assistant", "content": "The weather is sunny!"},
            headers=auth_headers
        )
        assert assistant_msg_response.status_code == 201

        # 7. Complete session with metrics
        complete_response = client.put(
            f"/api/v1/sessions/{session_id}",
            json={
                "status": "completed",
                "total_latency_ms": 1500,
                "token_usage_input": 50,
                "token_usage_output": 30
            },
            headers=auth_headers
        )
        assert complete_response.status_code == 200

        # 8. Verify final state
        final_response = client.get(
            f"/api/v1/sessions/{session_id}",
            headers=auth_headers
        )
        final_data = final_response.json()
        assert final_data["status"] == "completed"
        assert len(final_data["messages"]) == 2
        assert len(final_data["trace_steps"]) == 2
        assert final_data["total_latency_ms"] == 1500
