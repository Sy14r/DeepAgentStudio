"""
Tests for Agent Execution Services.

Tests for:
- SandboxService (tool code execution)
- SessionRecorder (session/message/trace recording)
- ToolLoader (tool wrapping)
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from app.services.sandbox import (
    SandboxService,
    SandboxResult,
    NoOpSandbox,
    get_sandbox_service,
    execute_tool_code
)
from app.services.session_recorder import (
    SessionRecorder,
    SessionRecorderError,
    create_session_recorder
)
from app.services.tool_wrapper import (
    ToolLoader,
    CustomToolWrapper,
    BUILTIN_TOOL_REGISTRY
)
from app.models.session import Session, SessionStatus, Message, MessageRole, TraceStep, TraceStepType
from app.models.agent import Agent, AgentVersion, AgentType
from app.models.tool import Tool, ToolType, ToolCategory


class TestSandboxService:
    """Test cases for SandboxService"""

    def test_create_sandbox_service(self):
        """Test creating sandbox service"""
        service = SandboxService()
        assert service.sandbox_type == "noop"
        assert isinstance(service.sandbox, NoOpSandbox)

    def test_sandbox_is_available(self):
        """Test sandbox availability check"""
        service = SandboxService()
        assert service.is_sandbox_available() is True

    def test_get_sandbox_info(self):
        """Test getting sandbox info"""
        service = SandboxService()
        info = service.get_sandbox_info()
        assert info["type"] == "noop"
        assert info["available"] is True
        assert info["class"] == "NoOpSandbox"
        assert info["security_level"] == "none"

    def test_execute_simple_code(self):
        """Test executing simple code"""
        service = SandboxService()
        result = service.execute_tool(
            code="result = x + y",
            inputs={"x": 2, "y": 3}
        )
        assert result.success is True
        assert result.output == 5
        assert result.error is None

    def test_execute_code_with_string_output(self):
        """Test executing code that returns string"""
        service = SandboxService()
        result = service.execute_tool(
            code="result = f'Hello, {name}!'",
            inputs={"name": "World"}
        )
        assert result.success is True
        assert result.output == "Hello, World!"

    def test_execute_code_without_result(self):
        """Test executing code without result variable"""
        service = SandboxService()
        result = service.execute_tool(
            code="x = 1 + 1",
            inputs={}
        )
        assert result.success is True
        assert result.output is None

    def test_execute_code_with_error(self):
        """Test executing code that raises exception"""
        service = SandboxService()
        result = service.execute_tool(
            code="result = 1 / 0",
            inputs={}
        )
        assert result.success is False
        assert result.output is None
        assert "ZeroDivisionError" in result.error

    def test_execute_code_with_syntax_error(self):
        """Test executing code with syntax error"""
        service = SandboxService()
        result = service.execute_tool(
            code="result = def bad syntax",
            inputs={}
        )
        assert result.success is False
        assert "SyntaxError" in result.error

    def test_execute_empty_code(self):
        """Test executing empty code"""
        service = SandboxService()
        result = service.execute_tool(
            code="",
            inputs={}
        )
        assert result.success is False
        assert "No code provided" in result.error

    def test_execute_function(self):
        """Test executing function code"""
        service = SandboxService()
        func_code = """
def add(a, b):
    return a + b
"""
        result = service.execute_function(
            func_code=func_code,
            func_name="add",
            args={"a": 5, "b": 3}
        )
        assert result.success is True
        assert result.output == 8

    def test_validate_code_valid(self):
        """Test validating valid code"""
        service = SandboxService()
        is_valid, error = service.validate_code("x = 1 + 1")
        assert is_valid is True
        assert error is None

    def test_validate_code_invalid(self):
        """Test validating invalid code"""
        service = SandboxService()
        is_valid, error = service.validate_code("def bad(")
        assert is_valid is False
        assert error is not None

    def test_execution_time_measured(self):
        """Test that execution time is measured"""
        service = SandboxService()
        result = service.execute_tool(
            code="result = sum(range(1000))",
            inputs={}
        )
        assert result.success is True
        assert result.execution_time_ms is not None
        assert result.execution_time_ms >= 0

    def test_singleton_sandbox_service(self):
        """Test singleton sandbox service"""
        service1 = get_sandbox_service()
        service2 = get_sandbox_service()
        assert service1 is service2

    def test_convenience_function(self):
        """Test convenience execute_tool_code function"""
        result = execute_tool_code(
            code="result = a * b",
            inputs={"a": 4, "b": 5}
        )
        assert result.success is True
        assert result.output == 20


class TestSessionRecorder:
    """Test cases for SessionRecorder"""

    def test_create_session_recorder(self, db, test_user):
        """Test creating session recorder"""
        # Create agent first
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.commit()

        recorder = SessionRecorder(
            db=db,
            agent_id=agent.id,
            user_id=test_user.id
        )
        assert recorder.agent_id == agent.id
        assert recorder.user_id == test_user.id
        assert recorder._session is None

    def test_start_new_session(self, db, test_user):
        """Test starting a new session"""
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.commit()

        recorder = SessionRecorder(db, agent.id, test_user.id)
        session = recorder.start_session(title="Test Session")

        assert session.id is not None
        assert session.agent_id == agent.id
        assert session.user_id == test_user.id
        assert session.title == "Test Session"
        assert session.status == SessionStatus.RUNNING

    def test_record_user_message(self, db, test_user):
        """Test recording user message"""
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.commit()

        recorder = SessionRecorder(db, agent.id, test_user.id)
        recorder.start_session()

        message = recorder.record_user_message("Hello, agent!")

        assert message.id is not None
        assert message.role == MessageRole.USER
        assert message.content == "Hello, agent!"
        assert message.sequence_number == 0

    def test_record_assistant_message(self, db, test_user):
        """Test recording assistant message"""
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.commit()

        recorder = SessionRecorder(db, agent.id, test_user.id)
        recorder.start_session()
        recorder.record_user_message("Hi")

        message = recorder.record_assistant_message("Hello! How can I help?")

        assert message.role == MessageRole.ASSISTANT
        assert message.content == "Hello! How can I help?"
        assert message.sequence_number == 1

    def test_record_trace_step(self, db, test_user):
        """Test recording trace step"""
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.commit()

        recorder = SessionRecorder(db, agent.id, test_user.id)
        recorder.start_session()

        step = recorder.record_trace_step(
            TraceStepType.THOUGHT,
            content="I need to think about this"
        )

        assert step.id is not None
        assert step.step_type == TraceStepType.THOUGHT
        assert step.content == "I need to think about this"
        assert step.step_number == 0

    def test_record_tool_call(self, db, test_user):
        """Test recording tool call trace step"""
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.commit()

        recorder = SessionRecorder(db, agent.id, test_user.id)
        recorder.start_session()

        step = recorder.record_tool_call(
            tool_name="Calculator",
            tool_input={"expression": "2 + 2"}
        )

        assert step.step_type == TraceStepType.TOOL_CALL
        assert step.tool_name == "Calculator"
        assert step.tool_input == {"expression": "2 + 2"}

    def test_record_tool_result(self, db, test_user):
        """Test recording tool result trace step"""
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.commit()

        recorder = SessionRecorder(db, agent.id, test_user.id)
        recorder.start_session()

        step = recorder.record_tool_result(
            tool_name="Calculator",
            tool_output={"result": "4"},
            latency_ms=10
        )

        assert step.step_type == TraceStepType.TOOL_RESULT
        assert step.tool_name == "Calculator"
        assert step.tool_output == {"result": "4"}
        assert step.latency_ms == 10

    def test_finish_session_completed(self, db, test_user):
        """Test finishing session with completed status"""
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.commit()

        recorder = SessionRecorder(db, agent.id, test_user.id)
        recorder.start_session()
        recorder.record_user_message("Test")
        recorder.record_assistant_message("Response")

        session = recorder.finish_session(
            status=SessionStatus.COMPLETED,
            output="Response",
            tokens_input=50,
            tokens_output=20
        )

        assert session.status == SessionStatus.COMPLETED
        assert session.completed_at is not None
        assert session.token_usage_input == 50
        assert session.token_usage_output == 20
        assert session.total_latency_ms is not None

    def test_fail_session(self, db, test_user):
        """Test failing a session"""
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.commit()

        recorder = SessionRecorder(db, agent.id, test_user.id)
        recorder.start_session()

        session = recorder.fail_session(
            error="Something went wrong",
            error_type="RuntimeError"
        )

        assert session.status == SessionStatus.FAILED
        assert session.error_message == "Something went wrong"
        assert session.error_type == "RuntimeError"

    def test_get_session_summary(self, db, test_user):
        """Test getting session summary"""
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.commit()

        recorder = SessionRecorder(db, agent.id, test_user.id)
        recorder.start_session()
        recorder.record_user_message("Test")
        recorder.record_thought("Thinking...")

        summary = recorder.get_session_summary()

        assert summary["agent_id"] == agent.id
        assert summary["status"] == "running"
        assert summary["message_count"] == 1
        assert summary["trace_step_count"] == 1

    def test_resume_session(self, db, test_user):
        """Test resuming an existing session"""
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.commit()

        # Create initial session
        session = Session(
            user_id=test_user.id,
            agent_id=agent.id,
            status=SessionStatus.PENDING
        )
        db.add(session)
        db.commit()

        # Resume the session
        recorder = SessionRecorder(
            db, agent.id, test_user.id,
            session_id=session.id
        )
        resumed = recorder.start_session()

        assert resumed.id == session.id
        assert resumed.status == SessionStatus.RUNNING

    def test_session_not_started_error(self, db, test_user):
        """Test error when session not started"""
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.commit()

        recorder = SessionRecorder(db, agent.id, test_user.id)

        with pytest.raises(SessionRecorderError, match="Session not started"):
            recorder.record_user_message("Test")


class TestToolLoader:
    """Test cases for ToolLoader"""

    def test_get_available_builtin_tools(self):
        """Test getting list of available built-in tools"""
        tools = ToolLoader.get_available_builtin_tools()
        assert "PythonCodeExecution" in tools
        assert "HTTPRequest" in tools

    def test_is_builtin_tool_supported(self):
        """Test checking if built-in tool is supported"""
        assert ToolLoader.is_builtin_tool_supported("PythonCodeExecution") is True
        assert ToolLoader.is_builtin_tool_supported("HTTPRequest") is True
        assert ToolLoader.is_builtin_tool_supported("NonExistentTool") is False

    def test_create_python_execution_tool(self):
        """Test creating Python code execution tool"""
        tool = BUILTIN_TOOL_REGISTRY["PythonCodeExecution"]()
        assert tool.name == "python_code_execution"
        assert "python" in tool.description.lower() or "code" in tool.description.lower()

    def test_create_http_request_tool(self):
        """Test creating HTTP request tool"""
        tool = BUILTIN_TOOL_REGISTRY["HTTPRequest"]()
        assert tool.name == "http_request"
        assert "http" in tool.description.lower() or "request" in tool.description.lower()


class TestCustomToolWrapper:
    """Test cases for CustomToolWrapper"""

    def test_create_custom_tool_wrapper(self):
        """Test creating custom tool wrapper"""
        wrapper = CustomToolWrapper(
            name="test_tool",
            description="A test tool",
            tool_id=1,
            function_code="def test_tool(x):\n    return x * 2"
        )
        assert wrapper.name == "test_tool"
        assert wrapper.description == "A test tool"
        assert wrapper.tool_id == 1

    def test_execute_custom_tool(self):
        """Test executing custom tool"""
        wrapper = CustomToolWrapper(
            name="doubler",
            description="Doubles a number",
            tool_id=1,
            function_code="def doubler(value):\n    return value * 2"
        )
        result = wrapper._run(value=5)
        assert result == "10"

    def test_execute_custom_tool_with_error(self):
        """Test executing custom tool that raises error"""
        wrapper = CustomToolWrapper(
            name="bad_tool",
            description="A bad tool",
            tool_id=1,
            function_code="def bad_tool():\n    return 1 / 0"
        )
        result = wrapper._run()
        assert "Tool error:" in result
        assert "ZeroDivisionError" in result

    def test_execute_custom_tool_no_result(self):
        """Test executing custom tool with no result"""
        wrapper = CustomToolWrapper(
            name="no_result",
            description="No result tool",
            tool_id=1,
            function_code="def no_result():\n    x = 1"
        )
        result = wrapper._run()
        assert "no result" in result.lower()
