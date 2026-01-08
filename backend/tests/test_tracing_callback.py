"""
Tests for Tracing Callback and Model Pricing (Enhanced Tracing System Phase 2)

Tests the DeepAgentTracingCallback and model pricing utilities.
"""
import pytest
from decimal import Decimal
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4

from app.models.session import Session, SessionStatus, Span, SpanType, SpanStatus
from app.models.agent import Agent
from app.models.agent_type import AgentTypeConfig, ExecutionStrategy, StrategyType
from app.services.span_recorder import SpanRecorder
from app.services.tracing_callback import DeepAgentTracingCallback, create_tracing_callback
from app.utils.model_pricing import (
    get_model_pricing,
    calculate_cost,
    get_provider_from_model,
    MODEL_PRICING,
    DEFAULT_PRICING
)


@pytest.fixture
def test_agent_type(db, test_user):
    """Create a test agent type configuration."""
    agent_type = AgentTypeConfig(
        user_id=test_user.id,
        name="Test ReAct Type",
        description="A test agent type for tracing tests",
        execution_strategy=ExecutionStrategy.react,
        strategy_type=StrategyType.builtin,
        is_builtin=False,
        is_active=True,
    )
    db.add(agent_type)
    db.commit()
    db.refresh(agent_type)
    return agent_type


class TestModelPricing:
    """Test cases for model pricing utilities"""

    def test_get_pricing_known_model(self):
        """Test getting pricing for known models"""
        # OpenAI GPT-4o
        input_price, output_price = get_model_pricing("gpt-4o")
        assert input_price == Decimal("0.0025")
        assert output_price == Decimal("0.01")

        # Anthropic Claude
        input_price, output_price = get_model_pricing("claude-3-5-sonnet-20241022")
        assert input_price == Decimal("0.003")
        assert output_price == Decimal("0.015")

    def test_get_pricing_unknown_model(self):
        """Test getting pricing for unknown models returns default"""
        input_price, output_price = get_model_pricing("unknown-model-xyz")
        assert input_price == DEFAULT_PRICING[0]
        assert output_price == DEFAULT_PRICING[1]

    def test_get_pricing_prefix_match(self):
        """Test prefix matching for versioned models"""
        # Should match gpt-4o pricing
        input_price, output_price = get_model_pricing("gpt-4o-custom")
        assert input_price == Decimal("0.0025")
        assert output_price == Decimal("0.01")

    def test_calculate_cost(self):
        """Test cost calculation"""
        # GPT-4o: $0.0025/1K input, $0.01/1K output
        cost = calculate_cost("gpt-4o", input_tokens=1000, output_tokens=500)
        expected = Decimal("0.0025") + (Decimal("500") / Decimal("1000")) * Decimal("0.01")
        assert cost == expected

    def test_calculate_cost_zero_tokens(self):
        """Test cost calculation with zero tokens"""
        cost = calculate_cost("gpt-4o", input_tokens=0, output_tokens=0)
        assert cost == Decimal("0")

    def test_calculate_cost_large_token_count(self):
        """Test cost calculation with large token counts"""
        cost = calculate_cost("gpt-4o", input_tokens=100000, output_tokens=50000)
        # 100K input * $0.0025/1K = $0.25
        # 50K output * $0.01/1K = $0.50
        expected = Decimal("0.25") + Decimal("0.50")
        assert cost == expected

    def test_get_provider_from_model(self):
        """Test provider inference from model name"""
        assert get_provider_from_model("gpt-4o") == "openai"
        assert get_provider_from_model("gpt-3.5-turbo") == "openai"
        assert get_provider_from_model("claude-3-opus-20240229") == "anthropic"
        assert get_provider_from_model("gemini-1.5-pro") == "google"
        assert get_provider_from_model("text-embedding-ada-002") == "openai"
        assert get_provider_from_model("unknown-model") == "unknown"

    def test_all_models_have_valid_pricing(self):
        """Test that all configured models have valid pricing"""
        for model, pricing in MODEL_PRICING.items():
            assert len(pricing) == 2
            assert pricing[0] >= 0  # input price
            assert pricing[1] >= 0  # output price


class TestDeepAgentTracingCallback:
    """Test cases for DeepAgentTracingCallback"""

    def test_create_callback(self, db, test_user, test_agent_type):
        """Test creating a tracing callback"""
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

        callback = create_tracing_callback(
            db=db,
            session_id=session.id,
            capture_inputs=True,
            capture_outputs=True
        )

        assert callback is not None
        assert callback.recorder is not None
        assert callback.capture_inputs is True
        assert callback.capture_outputs is True

    def test_on_llm_start_end(self, db, test_user, test_agent_type):
        """Test LLM start and end callbacks create spans"""
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
        callback = DeepAgentTracingCallback(recorder)

        run_id = uuid4()

        # Simulate LLM start
        callback.on_llm_start(
            serialized={"name": "gpt-4o"},
            prompts=["Hello, how are you?"],
            run_id=run_id,
            invocation_params={"model": "gpt-4o", "temperature": 0.7}
        )

        # Create mock LLM response
        from langchain_core.outputs import LLMResult, Generation
        mock_response = LLMResult(
            generations=[[Generation(text="I'm doing well, thank you!")]],
            llm_output={"token_usage": {"prompt_tokens": 10, "completion_tokens": 8}}
        )

        # Simulate LLM end
        callback.on_llm_end(response=mock_response, run_id=run_id)

        # Verify span was created
        spans = db.query(Span).filter(Span.session_id == session.id).all()
        assert len(spans) >= 1

        llm_span = next((s for s in spans if s.span_type == SpanType.LLM), None)
        assert llm_span is not None
        assert llm_span.model_name == "gpt-4o"
        assert llm_span.tokens_input == 10
        assert llm_span.tokens_output == 8

    def test_on_tool_start_end(self, db, test_user, test_agent_type):
        """Test tool start and end callbacks create spans"""
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
        callback = DeepAgentTracingCallback(recorder)

        run_id = uuid4()

        # Simulate tool start
        callback.on_tool_start(
            serialized={"name": "web_search"},
            input_str='{"query": "latest AI news"}',
            run_id=run_id
        )

        # Simulate tool end
        callback.on_tool_end(
            output='{"results": ["Result 1", "Result 2"]}',
            run_id=run_id
        )

        # Verify span was created
        spans = db.query(Span).filter(Span.session_id == session.id).all()
        tool_span = next((s for s in spans if s.span_type == SpanType.TOOL), None)

        assert tool_span is not None
        assert tool_span.tool_name == "web_search"
        assert tool_span.status == SpanStatus.SUCCESS

    def test_on_chain_start_end(self, db, test_user, test_agent_type):
        """Test chain start and end callbacks create spans"""
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
        callback = DeepAgentTracingCallback(recorder)

        run_id = uuid4()

        # Simulate chain start
        callback.on_chain_start(
            serialized={"name": "AgentExecutor", "id": ["langchain", "agents", "AgentExecutor"]},
            inputs={"input": "Hello"},
            run_id=run_id
        )

        # Simulate chain end
        callback.on_chain_end(
            outputs={"output": "Hi there!"},
            run_id=run_id
        )

        # Verify span was created
        spans = db.query(Span).filter(Span.session_id == session.id).all()
        assert len(spans) >= 1

    def test_on_error_records_error_span(self, db, test_user, test_agent_type):
        """Test error callbacks create error spans"""
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
        callback = DeepAgentTracingCallback(recorder)

        run_id = uuid4()

        # Start a tool
        callback.on_tool_start(
            serialized={"name": "failing_tool"},
            input_str="test",
            run_id=run_id
        )

        # Simulate tool error
        callback.on_tool_error(
            error=ValueError("Tool execution failed"),
            run_id=run_id
        )

        # Verify error span was created
        spans = db.query(Span).filter(Span.session_id == session.id).all()
        error_span = next((s for s in spans if s.status == SpanStatus.ERROR), None)

        assert error_span is not None
        assert "Tool execution failed" in (error_span.error_message or "")

    def test_agent_action_records_thought(self, db, test_user, test_agent_type):
        """Test agent action records thought span"""
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
        callback = DeepAgentTracingCallback(recorder)

        # Create mock agent action
        from langchain.schema import AgentAction
        action = AgentAction(
            tool="web_search",
            tool_input={"query": "test"},
            log="I need to search the web for this information."
        )

        callback.on_agent_action(action=action)

        # Verify thought span was created
        spans = db.query(Span).filter(Span.session_id == session.id).all()
        thought_span = next((s for s in spans if s.span_type == SpanType.THOUGHT), None)

        assert thought_span is not None

    def test_capture_inputs_disabled(self, db, test_user, test_agent_type):
        """Test that inputs are not captured when disabled"""
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
        callback = DeepAgentTracingCallback(recorder, capture_inputs=False)

        run_id = uuid4()

        callback.on_tool_start(
            serialized={"name": "test_tool"},
            input_str="sensitive data",
            run_id=run_id
        )
        callback.on_tool_end(output="result", run_id=run_id)

        # Verify input was not captured
        spans = db.query(Span).filter(Span.session_id == session.id).all()
        tool_span = next((s for s in spans if s.span_type == SpanType.TOOL), None)

        assert tool_span is not None
        assert tool_span.input is None

    def test_capture_outputs_disabled(self, db, test_user, test_agent_type):
        """Test that outputs are not captured when disabled"""
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
        callback = DeepAgentTracingCallback(recorder, capture_outputs=False)

        run_id = uuid4()

        callback.on_tool_start(
            serialized={"name": "test_tool"},
            input_str="input",
            run_id=run_id
        )
        callback.on_tool_end(output="sensitive output", run_id=run_id)

        # Verify output was not captured
        spans = db.query(Span).filter(Span.session_id == session.id).all()
        tool_span = next((s for s in spans if s.span_type == SpanType.TOOL), None)

        assert tool_span is not None
        assert tool_span.output is None


class TestTracingIntegration:
    """Integration tests for tracing callback with full span lifecycle"""

    def test_nested_spans_from_callbacks(self, db, test_user, test_agent_type):
        """Test that nested callbacks create hierarchical spans"""
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
        callback = DeepAgentTracingCallback(recorder)

        chain_run_id = uuid4()
        llm_run_id = uuid4()
        tool_run_id = uuid4()

        # Simulate: Chain -> LLM -> Tool
        callback.on_chain_start(
            serialized={"name": "AgentExecutor"},
            inputs={"input": "test"},
            run_id=chain_run_id
        )

        callback.on_llm_start(
            serialized={"name": "gpt-4o"},
            prompts=["test prompt"],
            run_id=llm_run_id,
            parent_run_id=chain_run_id,
            invocation_params={"model": "gpt-4o"}
        )

        from langchain_core.outputs import LLMResult, Generation
        callback.on_llm_end(
            response=LLMResult(
                generations=[[Generation(text="Use tool")]],
                llm_output={"token_usage": {"prompt_tokens": 5, "completion_tokens": 3}}
            ),
            run_id=llm_run_id
        )

        callback.on_tool_start(
            serialized={"name": "web_search"},
            input_str="query",
            run_id=tool_run_id,
            parent_run_id=chain_run_id
        )
        callback.on_tool_end(output="results", run_id=tool_run_id)

        callback.on_chain_end(outputs={"output": "done"}, run_id=chain_run_id)

        # Verify all spans were created
        spans = db.query(Span).filter(Span.session_id == session.id).all()
        assert len(spans) >= 3  # Chain, LLM, Tool

        # Verify span types
        span_types = {s.span_type for s in spans}
        assert SpanType.LLM in span_types
        assert SpanType.TOOL in span_types

    def test_cost_calculation_in_span(self, db, test_user, test_agent_type):
        """Test that cost is calculated and stored in LLM spans"""
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
        callback = DeepAgentTracingCallback(recorder)

        run_id = uuid4()

        callback.on_llm_start(
            serialized={"name": "gpt-4o"},
            prompts=["test"],
            run_id=run_id,
            invocation_params={"model": "gpt-4o"}
        )

        from langchain_core.outputs import LLMResult, Generation
        callback.on_llm_end(
            response=LLMResult(
                generations=[[Generation(text="response")]],
                llm_output={"token_usage": {"prompt_tokens": 1000, "completion_tokens": 500}}
            ),
            run_id=run_id
        )

        # Verify cost was calculated
        spans = db.query(Span).filter(Span.session_id == session.id).all()
        llm_span = next((s for s in spans if s.span_type == SpanType.LLM), None)

        assert llm_span is not None
        assert llm_span.cost_usd is not None
        assert llm_span.cost_usd > 0

        # Verify correct cost (GPT-4o: $0.0025/1K input + $0.01/1K output)
        expected_cost = calculate_cost("gpt-4o", 1000, 500)
        assert llm_span.cost_usd == expected_cost


class TestWebSocketSpanEvents:
    """Tests for Phase 3 WebSocket span events"""

    @pytest.mark.asyncio
    async def test_callback_with_websocket_emits_span_start(self, db, test_user, test_agent_type):
        """Test that callback emits span_start WebSocket event"""
        import asyncio
        from unittest.mock import AsyncMock

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

        # Create mock websocket
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()

        # Get the current event loop
        loop = asyncio.get_event_loop()

        recorder = SpanRecorder(db, session.id)
        callback = DeepAgentTracingCallback(
            recorder,
            websocket=mock_ws,
            loop=loop
        )

        run_id = uuid4()

        # Trigger chain start in a thread (simulating how LangChain calls callbacks)
        def run_callback():
            callback.on_chain_start(
                serialized={"name": "TestChain"},
                inputs={"input": "test"},
                run_id=run_id
            )

        await asyncio.get_event_loop().run_in_executor(None, run_callback)

        # Give async tasks time to complete
        await asyncio.sleep(0.1)

        # Verify WebSocket was called
        assert mock_ws.send_json.called
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "span_start"
        assert call_args["payload"]["name"] == "TestChain"
        assert call_args["payload"]["span_type"] == "chain"

    @pytest.mark.asyncio
    async def test_callback_with_websocket_emits_span_end(self, db, test_user, test_agent_type):
        """Test that callback emits span_end WebSocket event"""
        import asyncio
        from unittest.mock import AsyncMock

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

        # Create mock websocket
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()

        # Get the current event loop
        loop = asyncio.get_event_loop()

        recorder = SpanRecorder(db, session.id)
        callback = DeepAgentTracingCallback(
            recorder,
            websocket=mock_ws,
            loop=loop
        )

        run_id = uuid4()

        # Start and end a chain in a thread
        def run_callback():
            callback.on_chain_start(
                serialized={"name": "TestChain"},
                inputs={"input": "test"},
                run_id=run_id
            )
            callback.on_chain_end(
                outputs={"output": "done"},
                run_id=run_id
            )

        await asyncio.get_event_loop().run_in_executor(None, run_callback)

        # Give async tasks time to complete
        await asyncio.sleep(0.1)

        # Verify span_end was called
        calls = mock_ws.send_json.call_args_list
        assert len(calls) == 2  # span_start + span_end

        end_call = calls[1][0][0]
        assert end_call["type"] == "span_end"
        assert end_call["payload"]["status"] == "success"

    def test_callback_without_websocket_still_records_spans(self, db, test_user, test_agent_type):
        """Test that callback works without websocket (no errors)"""
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
        # No websocket or loop provided
        callback = DeepAgentTracingCallback(recorder)

        run_id = uuid4()

        # Should work without errors
        callback.on_tool_start(
            serialized={"name": "test_tool"},
            input_str="test",
            run_id=run_id
        )
        callback.on_tool_end(output="result", run_id=run_id)

        # Verify span was created
        spans = db.query(Span).filter(Span.session_id == session.id).all()
        assert len(spans) == 1
        assert spans[0].span_type == SpanType.TOOL

    @pytest.mark.asyncio
    async def test_websocket_emits_error_on_span_error(self, db, test_user, test_agent_type):
        """Test that callback emits span_end with error status"""
        import asyncio
        from unittest.mock import AsyncMock

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

        # Create mock websocket
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()

        loop = asyncio.get_event_loop()

        recorder = SpanRecorder(db, session.id)
        callback = DeepAgentTracingCallback(
            recorder,
            websocket=mock_ws,
            loop=loop
        )

        run_id = uuid4()

        # Start tool and trigger error in a thread
        def run_callback():
            callback.on_tool_start(
                serialized={"name": "failing_tool"},
                input_str="test",
                run_id=run_id
            )
            callback.on_tool_error(
                error=ValueError("Tool failed"),
                run_id=run_id
            )

        await asyncio.get_event_loop().run_in_executor(None, run_callback)

        # Give async tasks time to complete
        await asyncio.sleep(0.1)

        # Verify span_end with error was called
        calls = mock_ws.send_json.call_args_list
        assert len(calls) == 2

        end_call = calls[1][0][0]
        assert end_call["type"] == "span_end"
        assert end_call["payload"]["status"] == "error"
        assert "Tool failed" in end_call["payload"]["error_message"]

    def test_create_tracing_callback_with_websocket(self, db, test_user, test_agent_type):
        """Test factory function accepts websocket parameters"""
        import asyncio
        from unittest.mock import AsyncMock

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

        mock_ws = AsyncMock()
        loop = asyncio.new_event_loop()

        callback = create_tracing_callback(
            db=db,
            session_id=session.id,
            websocket=mock_ws,
            loop=loop
        )

        assert callback.websocket is mock_ws
        assert callback.loop is loop

        loop.close()
