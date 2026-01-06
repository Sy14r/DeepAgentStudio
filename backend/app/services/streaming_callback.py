"""
LangChain Callback Handler for WebSocket Streaming.

Captures agent execution events and streams them to connected WebSocket clients
in real-time while the agent is executing.
"""
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone
import asyncio
import json
import logging
import time

from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import AgentAction, AgentFinish, LLMResult

logger = logging.getLogger(__name__)


class StreamingWebSocketCallbackHandler(BaseCallbackHandler):
    """
    LangChain callback handler that streams events to WebSocket.

    This handler captures execution events and sends them via WebSocket
    while the agent is running, enabling real-time UI updates.

    Events emitted:
    - tool_call: When agent decides to use a tool
    - tool_result: After tool completes with result
    - error: When an error occurs

    Usage:
        callback = StreamingWebSocketCallbackHandler(
            websocket=websocket,
            session_id=123,
            loop=asyncio.get_event_loop()
        )
        executor = AgentExecutor(..., callbacks=[callback])
    """

    def __init__(
        self,
        websocket,
        session_id: int,
        loop: asyncio.AbstractEventLoop
    ):
        """
        Initialize streaming callback handler.

        Args:
            websocket: FastAPI WebSocket connection
            session_id: Session ID for event tracking
            loop: Event loop for async operations from sync callbacks
        """
        super().__init__()
        self.websocket = websocket
        self.session_id = session_id
        self.loop = loop
        self.step_number = 0
        self._tool_start_times: Dict[str, float] = {}
        self._current_tool: Optional[str] = None

    async def _send_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """
        Send an event through the WebSocket.

        Args:
            event_type: Type of event (tool_call, tool_result, error, etc.)
            payload: Event-specific data
        """
        event = {
            "type": event_type,
            "session_id": self.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload
        }
        try:
            await self.websocket.send_json(event)
            logger.debug(f"Sent WebSocket event: {event_type}")
        except Exception as e:
            logger.error(f"Failed to send WebSocket event: {e}")

    def _send_event_sync(self, event_type: str, payload: Dict[str, Any]) -> None:
        """
        Synchronous wrapper to send events from sync callbacks.

        LangChain callbacks are synchronous, but WebSocket send is async.
        This bridges the gap using run_coroutine_threadsafe.

        Args:
            event_type: Type of event
            payload: Event-specific data
        """
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._send_event(event_type, payload),
                self.loop
            )
            # Wait briefly for send to complete (non-blocking for caller)
            future.result(timeout=5.0)
        except Exception as e:
            logger.error(f"Failed to send sync event: {e}")

    def on_agent_action(
        self,
        action: AgentAction,
        *,
        run_id=None,
        parent_run_id=None,
        **kwargs
    ) -> None:
        """
        Called when agent decides to use a tool.

        Emits a 'tool_call' event with tool name and input.
        """
        self._tool_start_times[action.tool] = time.time()
        self._current_tool = action.tool

        # Normalize tool input to dict
        tool_input = action.tool_input
        if not isinstance(tool_input, dict):
            tool_input = {"input": str(tool_input)}

        self._send_event_sync("tool_call", {
            "step_number": self.step_number,
            "tool_name": action.tool,
            "tool_input": tool_input
        })
        self.step_number += 1

        logger.info(f"Tool call: {action.tool}")

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id=None,
        parent_run_id=None,
        tags=None,
        metadata=None,
        inputs=None,
        **kwargs
    ) -> None:
        """
        Called when tool execution starts.

        We track timing here but don't emit a separate event
        (tool_call already sent in on_agent_action).
        """
        tool_name = serialized.get("name", "unknown")
        if tool_name not in self._tool_start_times:
            self._tool_start_times[tool_name] = time.time()
            self._current_tool = tool_name

    def on_tool_end(
        self,
        output: str,
        *,
        run_id=None,
        parent_run_id=None,
        **kwargs
    ) -> None:
        """
        Called when tool execution completes.

        Emits a 'tool_result' event with output and latency.
        """
        # Get tool name - try kwargs first, then fall back to tracked current tool
        tool_name = kwargs.get("name", self._current_tool or "unknown")

        # Calculate latency
        start_time = self._tool_start_times.pop(tool_name, None)
        if start_time is None:
            start_time = self._tool_start_times.pop(self._current_tool, time.time()) if self._current_tool else time.time()
        latency_ms = int((time.time() - start_time) * 1000)

        # Parse output if it looks like JSON
        tool_output: Union[str, Dict] = output
        if isinstance(output, str):
            try:
                parsed = json.loads(output)
                if isinstance(parsed, (dict, list)):
                    tool_output = parsed
            except (json.JSONDecodeError, TypeError):
                pass

        self._send_event_sync("tool_result", {
            "step_number": self.step_number,
            "tool_name": tool_name,
            "tool_output": tool_output,
            "latency_ms": latency_ms
        })
        self.step_number += 1
        self._current_tool = None

        logger.info(f"Tool result: {tool_name} ({latency_ms}ms)")

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id=None,
        parent_run_id=None,
        **kwargs
    ) -> None:
        """
        Called when tool execution fails.

        Emits an 'error' event with error details.
        """
        tool_name = kwargs.get("name", self._current_tool or "unknown")

        self._send_event_sync("error", {
            "step_number": self.step_number,
            "error": str(error),
            "error_type": type(error).__name__,
            "tool_name": tool_name
        })
        self.step_number += 1

        logger.error(f"Tool error in {tool_name}: {error}")

    def on_agent_finish(
        self,
        finish: AgentFinish,
        *,
        run_id=None,
        parent_run_id=None,
        **kwargs
    ) -> None:
        """
        Called when agent completes execution.

        We don't emit final_answer here - it's sent separately
        by the streaming executor with full metrics.
        """
        logger.info("Agent finished")

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id=None,
        parent_run_id=None,
        **kwargs
    ) -> None:
        """
        Called when an error occurs in the chain.

        Emits an 'error' event.
        """
        self._send_event_sync("error", {
            "error": str(error),
            "error_type": type(error).__name__
        })

        logger.error(f"Chain error: {error}")

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id=None,
        parent_run_id=None,
        **kwargs
    ) -> None:
        """
        Called when LLM starts processing.

        Could emit a 'thinking' event here for future enhancement.
        Currently not emitting to keep events focused on tool calls.
        """
        pass

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id=None,
        parent_run_id=None,
        **kwargs
    ) -> None:
        """
        Called when LLM finishes processing.

        Could emit token usage here for future enhancement.
        """
        pass

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id=None,
        parent_run_id=None,
        **kwargs
    ) -> None:
        """
        Called when LLM encounters an error.
        """
        self._send_event_sync("error", {
            "error": str(error),
            "error_type": type(error).__name__,
            "source": "llm"
        })

        logger.error(f"LLM error: {error}")
