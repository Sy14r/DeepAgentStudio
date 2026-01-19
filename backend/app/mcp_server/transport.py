"""SSE Transport Handler for MCP Server."""
import json
import logging
import asyncio
from typing import Optional, AsyncIterator, Dict, Any

from fastapi import Request, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from mcp.types import (
    JSONRPCMessage,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
    InitializeRequest,
    InitializeResult,
    ListToolsRequest,
    ListToolsResult,
    CallToolRequest,
    CallToolResult,
    ServerCapabilities,
    Implementation,
)

from .context import MCPContext, create_context, set_context, reset_context
from .auth import get_agent_permissions
from .server import get_registered_tools, get_tools_for_permissions
from .errors import MCPError, PermissionDenied

logger = logging.getLogger(__name__)


class MCPSSEHandler:
    """
    Server-Sent Events (SSE) handler for MCP protocol.

    Handles the MCP protocol over SSE transport, managing:
    - Session initialization
    - Tool listing (filtered by permissions)
    - Tool invocation with permission checking
    """

    def __init__(self, db: Session, user: Any, agent_id: Optional[int] = None, session_id: Optional[int] = None):
        """
        Initialize the SSE handler.

        Args:
            db: Database session
            user: Authenticated user
            agent_id: Optional agent ID (for agent-initiated calls)
            session_id: Optional session ID for tracing
        """
        self.db = db
        self.user = user
        self.agent_id = agent_id
        self.session_id = session_id
        self._context: Optional[MCPContext] = None
        self._initialized = False

    def _get_context(self) -> MCPContext:
        """Get or create the MCP context."""
        if self._context is None:
            permissions = None
            if self.agent_id:
                # Pre-resolve permissions for agent
                ctx = MCPContext(
                    user_id=self.user.id,
                    agent_id=self.agent_id,
                    db=self.db,
                    session_id=self.session_id
                )
                permissions = get_agent_permissions(ctx)

            self._context = create_context(
                user=self.user,
                db=self.db,
                agent_id=self.agent_id,
                session_id=self.session_id,
                permissions=permissions
            )
        return self._context

    async def handle_message(self, message: JSONRPCMessage) -> JSONRPCMessage:
        """
        Handle an incoming JSON-RPC message.

        Args:
            message: The incoming JSON-RPC message

        Returns:
            The response message
        """
        if not isinstance(message, JSONRPCRequest):
            return JSONRPCError(
                id=getattr(message, 'id', None),
                error={"code": -32600, "message": "Invalid Request"}
            )

        method = message.method
        params = message.params or {}
        request_id = message.id

        try:
            if method == "initialize":
                result = await self._handle_initialize(params)
            elif method == "tools/list":
                result = await self._handle_list_tools()
            elif method == "tools/call":
                result = await self._handle_call_tool(params)
            else:
                return JSONRPCResponse(
                    id=request_id,
                    error={"code": -32601, "message": f"Method not found: {method}"}
                )

            return JSONRPCResponse(id=request_id, result=result)

        except PermissionDenied as e:
            logger.warning(f"Permission denied: {e.message}")
            return JSONRPCResponse(
                id=request_id,
                error={"code": -32000, "message": e.message, "data": e.details}
            )
        except MCPError as e:
            logger.warning(f"MCP error: {e.message}")
            return JSONRPCResponse(
                id=request_id,
                error={"code": -32001, "message": e.message, "data": e.details}
            )
        except Exception as e:
            logger.exception(f"Internal error handling {method}: {e}")
            return JSONRPCResponse(
                id=request_id,
                error={"code": -32603, "message": "Internal error"}
            )

    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the initialize request."""
        self._initialized = True

        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": False}
            },
            "serverInfo": {
                "name": "deepagent-studio",
                "version": "1.0.0"
            }
        }

    async def _handle_list_tools(self) -> Dict[str, Any]:
        """Handle the tools/list request."""
        ctx = self._get_context()
        permissions = get_agent_permissions(ctx)
        tools = get_tools_for_permissions(permissions)

        return {
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "inputSchema": t.inputSchema
                }
                for t in tools
            ]
        }

    async def _handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            raise MCPError(code="invalid_params", message="Missing tool name")

        # Get registered tools
        registered_tools = get_registered_tools()

        if tool_name not in registered_tools:
            raise MCPError(code="not_found", message=f"Tool not found: {tool_name}")

        tool_metadata = registered_tools[tool_name]
        handler = tool_metadata["handler"]

        # Set context for the tool execution
        ctx = self._get_context()
        token = set_context(ctx)

        try:
            # Execute the tool
            result = await handler(**arguments)

            # Convert result to serializable format
            content = []
            for item in result:
                if hasattr(item, 'text'):
                    content.append({"type": "text", "text": item.text})
                else:
                    content.append({"type": "text", "text": str(item)})

            return {"content": content, "isError": False}

        except MCPError as e:
            return {
                "content": [{"type": "text", "text": e.message}],
                "isError": True
            }
        finally:
            reset_context(token)


async def create_sse_stream(
    handler: MCPSSEHandler,
    request: Request
) -> AsyncIterator[str]:
    """
    Create an SSE stream for MCP communication.

    Args:
        handler: The MCP SSE handler
        request: The FastAPI request

    Yields:
        SSE-formatted messages
    """
    # Send initial connection established event
    yield f"event: open\ndata: {json.dumps({'status': 'connected'})}\n\n"

    try:
        # Read messages from the request body (if any)
        # For SSE, we typically use a separate endpoint for sending messages
        # This stream is for receiving server events

        # Keep connection alive with periodic pings
        while True:
            if await request.is_disconnected():
                break

            # Send keepalive ping every 30 seconds
            yield f"event: ping\ndata: {json.dumps({'type': 'keepalive'})}\n\n"
            await asyncio.sleep(30)

    except asyncio.CancelledError:
        logger.info("SSE connection cancelled")
    except Exception as e:
        logger.exception(f"SSE stream error: {e}")
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"


def create_sse_response(
    handler: MCPSSEHandler,
    request: Request
) -> StreamingResponse:
    """
    Create a StreamingResponse for SSE.

    Args:
        handler: The MCP SSE handler
        request: The FastAPI request

    Returns:
        StreamingResponse configured for SSE
    """
    return StreamingResponse(
        create_sse_stream(handler, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )
