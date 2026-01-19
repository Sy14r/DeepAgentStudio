"""MCP Server API endpoints."""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ...database import get_db
from ...models.user import User
from ...models.agent import Agent
from ...models.agent_permission import AgentPermission, PermissionPreset
from ..deps import get_current_user
from ...mcp_server.transport import MCPSSEHandler, create_sse_response
from ...mcp_server.context import MCPContext, create_context, set_context, reset_context
from ...mcp_server.auth import get_agent_permissions
from ...mcp_server.server import get_registered_tools, get_tools_for_permissions
from ...mcp_server.permissions import resolve_permissions
from ...mcp_server.errors import MCPError

logger = logging.getLogger(__name__)

router = APIRouter()


class MCPCallRequest(BaseModel):
    """Request body for MCP tool calls."""
    method: str
    params: Optional[dict] = None
    id: Optional[int] = 1


class MCPToolCallRequest(BaseModel):
    """Request body for direct tool calls."""
    name: str
    arguments: Optional[dict] = None


@router.get("/sse")
async def mcp_sse_endpoint(
    request: Request,
    agent_id: Optional[int] = None,
    session_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    MCP Server-Sent Events endpoint.

    Establishes an SSE connection for MCP protocol communication.
    Use this endpoint for real-time tool discovery and invocation.

    Query Parameters:
        - agent_id: Optional agent ID to scope permissions
        - session_id: Optional session ID for tracing

    Returns SSE stream with MCP protocol messages.
    """
    # Validate agent_id if provided
    if agent_id:
        agent = db.query(Agent).filter(
            Agent.id == agent_id,
            Agent.user_id == current_user.id
        ).first()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )

    handler = MCPSSEHandler(
        db=db,
        user=current_user,
        agent_id=agent_id,
        session_id=session_id
    )

    return create_sse_response(handler, request)


@router.post("/call")
async def mcp_call_endpoint(
    request_body: MCPCallRequest,
    agent_id: Optional[int] = None,
    session_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    MCP JSON-RPC call endpoint.

    Handles MCP protocol calls via HTTP POST.
    Supports initialize, tools/list, and tools/call methods.

    Query Parameters:
        - agent_id: Optional agent ID to scope permissions
        - session_id: Optional session ID for tracing

    Request Body:
        - method: JSON-RPC method name
        - params: Method parameters
        - id: Request ID
    """
    # Validate agent_id if provided
    if agent_id:
        agent = db.query(Agent).filter(
            Agent.id == agent_id,
            Agent.user_id == current_user.id
        ).first()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )

    handler = MCPSSEHandler(
        db=db,
        user=current_user,
        agent_id=agent_id,
        session_id=session_id
    )

    # Create a mock JSONRPCRequest
    class MockRequest:
        def __init__(self, method, params, id):
            self.method = method
            self.params = params
            self.id = id

    mock_msg = MockRequest(
        method=request_body.method,
        params=request_body.params,
        id=request_body.id
    )

    response = await handler.handle_message(mock_msg)

    # Convert response to dict
    if hasattr(response, 'result'):
        return {"jsonrpc": "2.0", "id": request_body.id, "result": response.result}
    elif hasattr(response, 'error'):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"jsonrpc": "2.0", "id": request_body.id, "error": response.error}
        )
    else:
        return {"jsonrpc": "2.0", "id": request_body.id, "result": None}


@router.post("/tools/{tool_name}")
async def call_tool_directly(
    tool_name: str,
    request_body: MCPToolCallRequest,
    agent_id: Optional[int] = None,
    session_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Direct tool invocation endpoint.

    Call an MCP tool directly by name without JSON-RPC wrapping.
    Permission checking is still enforced based on agent_id.

    Path Parameters:
        - tool_name: Name of the tool to invoke

    Query Parameters:
        - agent_id: Optional agent ID to scope permissions
        - session_id: Optional session ID for tracing

    Request Body:
        - name: Tool name (should match path parameter)
        - arguments: Tool arguments
    """
    # Validate agent_id if provided
    if agent_id:
        agent = db.query(Agent).filter(
            Agent.id == agent_id,
            Agent.user_id == current_user.id
        ).first()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )

    # Get registered tools
    registered_tools = get_registered_tools()

    if tool_name not in registered_tools:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool not found: {tool_name}"
        )

    # Create context and check permissions
    permissions = None
    if agent_id:
        # Get agent permissions
        agent_perm = db.query(AgentPermission).filter(
            AgentPermission.agent_id == agent_id
        ).first()

        if agent_perm:
            permissions = resolve_permissions(agent_perm.preset, agent_perm.custom_permissions)
        else:
            permissions = resolve_permissions(PermissionPreset.OBSERVER.value, None)

        # Check if tool permission is granted
        from ...mcp_server.permissions import has_permission
        tool_metadata = registered_tools[tool_name]
        required_perm = tool_metadata["permission"]

        if not has_permission(permissions, required_perm):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied for tool: {tool_name}"
            )

    # Create context
    ctx = create_context(
        user=current_user,
        db=db,
        agent_id=agent_id,
        session_id=session_id,
        permissions=permissions
    )

    token = set_context(ctx)

    try:
        # Get and execute tool handler
        tool_metadata = registered_tools[tool_name]
        handler = tool_metadata["handler"]
        arguments = request_body.arguments or {}

        result = await handler(**arguments)

        # Convert result to serializable format
        content = []
        for item in result:
            if hasattr(item, 'text'):
                content.append({"type": "text", "text": item.text})
            else:
                content.append({"type": "text", "text": str(item)})

        return {"success": True, "content": content}

    except MCPError as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "error": e.to_dict()}
        )
    except Exception as e:
        logger.exception(f"Tool execution error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool execution failed: {str(e)}"
        )
    finally:
        reset_context(token)


@router.get("/tools")
async def list_available_tools(
    agent_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List available MCP tools.

    Returns tools filtered by the agent's permissions (if agent_id provided)
    or all tools (if called directly by user).

    Query Parameters:
        - agent_id: Optional agent ID to filter by permissions
    """
    # Get permissions
    permissions = {"*"}  # Default: full access for direct user calls

    if agent_id:
        agent = db.query(Agent).filter(
            Agent.id == agent_id,
            Agent.user_id == current_user.id
        ).first()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )

        # Get agent permissions
        agent_perm = db.query(AgentPermission).filter(
            AgentPermission.agent_id == agent_id
        ).first()

        if agent_perm:
            permissions = resolve_permissions(agent_perm.preset, agent_perm.custom_permissions)
        else:
            permissions = resolve_permissions(PermissionPreset.OBSERVER.value, None)

    # Get tools for permissions
    tools = get_tools_for_permissions(permissions)

    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.inputSchema
            }
            for t in tools
        ],
        "total": len(tools)
    }


@router.get("/capabilities")
async def get_server_capabilities(
    current_user: User = Depends(get_current_user)
):
    """
    Get MCP server capabilities.

    Returns information about the server's capabilities and supported features.
    """
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {
                "listChanged": False
            }
        },
        "serverInfo": {
            "name": "deepagent-studio",
            "version": "1.0.0"
        },
        "toolCount": len(get_registered_tools())
    }
