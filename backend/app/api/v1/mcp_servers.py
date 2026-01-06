"""
MCP Server Configuration API endpoints

Provides CRUD operations for managing MCP server configurations with:
- Support for stdio and SSE/HTTP transports
- Encrypted environment variable storage
- Connection testing and tool discovery
"""
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from ...database import get_db
from ...models.user import User
from ...models.mcp_server import MCPServerConfig, MCPTransportType
from ...schemas.mcp_server import (
    MCPServerConfigCreate,
    MCPServerConfigUpdate,
    MCPServerConfigResponse,
    MCPServerConfigListResponse,
    MCPServerToolsResponse,
    MCPServerTestResponse,
    MCPToolSchema,
)
from ...encryption import encrypt_api_key, decrypt_api_key
from ...services.mcp_client import test_mcp_connection, MCPClientService
from ..deps import get_current_user

router = APIRouter()


def _server_to_response(server: MCPServerConfig) -> MCPServerConfigResponse:
    """Convert MCPServerConfig model to response schema"""
    # Count cached tools
    cached_tools_count = 0
    if server.cached_tools:
        cached_tools_count = len(server.cached_tools)

    return MCPServerConfigResponse(
        id=server.id,
        user_id=server.user_id,
        name=server.name,
        description=server.description,
        transport_type=server.transport_type,
        stdio_config=server.stdio_config,
        http_config=server.http_config,
        config=server.config,
        has_env_vars=bool(server.encrypted_env_vars),
        cached_tools_count=cached_tools_count,
        tools_last_discovered_at=server.tools_last_discovered_at,
        is_active=server.is_active,
        last_connected_at=server.last_connected_at,
        last_error=server.last_error,
        created_at=server.created_at,
        updated_at=server.updated_at,
    )


@router.post("", response_model=MCPServerConfigResponse, status_code=status.HTTP_201_CREATED)
def create_mcp_server(
    server_data: MCPServerConfigCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new MCP server configuration.

    For stdio transport, provide stdio_config with command and args.
    For SSE/HTTP transport, provide http_config with url and optional headers.
    Environment variables will be encrypted before storage.
    """
    # Validate transport-specific config
    if server_data.transport_type == MCPTransportType.STDIO:
        if not server_data.stdio_config or not server_data.stdio_config.get("command"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="stdio transport requires stdio_config with 'command' field"
            )
    elif server_data.transport_type in (MCPTransportType.SSE, MCPTransportType.STREAMABLE_HTTP):
        if not server_data.http_config or not server_data.http_config.get("url"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SSE/HTTP transport requires http_config with 'url' field"
            )

    # Encrypt environment variables if provided
    encrypted_env = None
    if server_data.env_vars:
        encrypted_env = encrypt_api_key(json.dumps(server_data.env_vars))

    # Create server config
    server = MCPServerConfig(
        user_id=current_user.id,
        name=server_data.name,
        description=server_data.description,
        transport_type=server_data.transport_type,
        stdio_config=server_data.stdio_config,
        http_config=server_data.http_config,
        encrypted_env_vars=encrypted_env,
        config=server_data.config or {},
    )

    db.add(server)
    db.commit()
    db.refresh(server)

    return _server_to_response(server)


@router.get("", response_model=MCPServerConfigListResponse)
def list_mcp_servers(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    active_only: bool = Query(False, description="Only return active servers"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all MCP server configurations for the current user.

    Environment variables are NEVER included in the response.
    """
    query = db.query(MCPServerConfig).filter(
        MCPServerConfig.user_id == current_user.id
    )

    if active_only:
        query = query.filter(MCPServerConfig.is_active == True)

    total = query.count()
    servers = query.order_by(
        MCPServerConfig.updated_at.desc()
    ).offset(skip).limit(limit).all()

    return MCPServerConfigListResponse(
        servers=[_server_to_response(s) for s in servers],
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit
    )


@router.get("/{server_id}", response_model=MCPServerConfigResponse)
def get_mcp_server(
    server_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific MCP server configuration.

    Environment variables are NEVER included in the response.
    """
    server = db.query(MCPServerConfig).filter(
        MCPServerConfig.id == server_id,
        MCPServerConfig.user_id == current_user.id
    ).first()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP server configuration not found"
        )

    return _server_to_response(server)


@router.put("/{server_id}", response_model=MCPServerConfigResponse)
def update_mcp_server(
    server_id: int,
    server_data: MCPServerConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update MCP server configuration.

    Environment variables can be updated - set to {} to clear them.
    """
    server = db.query(MCPServerConfig).filter(
        MCPServerConfig.id == server_id,
        MCPServerConfig.user_id == current_user.id
    ).first()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP server configuration not found"
        )

    # Update fields if provided
    if server_data.name is not None:
        server.name = server_data.name
    if server_data.description is not None:
        server.description = server_data.description
    if server_data.stdio_config is not None:
        server.stdio_config = server_data.stdio_config
    if server_data.http_config is not None:
        server.http_config = server_data.http_config
    if server_data.config is not None:
        server.config = server_data.config
    if server_data.is_active is not None:
        server.is_active = server_data.is_active

    # Handle env_vars update
    if server_data.env_vars is not None:
        if server_data.env_vars:
            server.encrypted_env_vars = encrypt_api_key(json.dumps(server_data.env_vars))
        else:
            # Empty dict means clear env vars
            server.encrypted_env_vars = None

    db.commit()
    db.refresh(server)

    return _server_to_response(server)


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mcp_server(
    server_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an MCP server configuration.

    This permanently deletes the configuration and its encrypted environment variables.
    """
    server = db.query(MCPServerConfig).filter(
        MCPServerConfig.id == server_id,
        MCPServerConfig.user_id == current_user.id
    ).first()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP server configuration not found"
        )

    db.delete(server)
    db.commit()

    return None


@router.post("/{server_id}/test", response_model=MCPServerTestResponse)
async def test_mcp_server(
    server_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Test connection to an MCP server and discover available tools.

    This will:
    1. Connect to the MCP server using the configured transport
    2. Discover available tools
    3. Cache the discovered tools
    4. Update connection status

    This makes an actual connection to the MCP server.
    """
    server = db.query(MCPServerConfig).filter(
        MCPServerConfig.id == server_id,
        MCPServerConfig.user_id == current_user.id
    ).first()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP server configuration not found"
        )

    # Decrypt environment variables if present
    env_vars = None
    if server.encrypted_env_vars:
        try:
            decrypted = decrypt_api_key(server.encrypted_env_vars)
            env_vars = json.loads(decrypted)
        except Exception as e:
            return MCPServerTestResponse(
                success=False,
                message="Failed to decrypt environment variables",
                tools_count=0
            )

    # Test connection
    result = await test_mcp_connection(server, env_vars)

    # Update server status based on result
    if result["success"]:
        server.last_connected_at = datetime.utcnow()
        server.last_error = None
        server.cached_tools = result.get("tools", [])
        server.tools_last_discovered_at = datetime.utcnow()
    else:
        server.last_error = result["message"]

    db.commit()

    return MCPServerTestResponse(
        success=result["success"],
        message=result["message"],
        tools_count=result["tools_count"],
        latency_ms=result.get("latency_ms"),
        tools=result.get("tools") if result["success"] else None
    )


@router.get("/{server_id}/tools", response_model=MCPServerToolsResponse)
async def get_mcp_server_tools(
    server_id: int,
    refresh: bool = Query(False, description="Force refresh tools from server"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get tools available from an MCP server.

    By default, returns cached tools. Use refresh=true to reconnect and
    discover tools fresh from the server.
    """
    server = db.query(MCPServerConfig).filter(
        MCPServerConfig.id == server_id,
        MCPServerConfig.user_id == current_user.id
    ).first()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP server configuration not found"
        )

    # If refresh requested or no cached tools, discover fresh
    if refresh or not server.cached_tools:
        # Decrypt environment variables
        env_vars = None
        if server.encrypted_env_vars:
            try:
                decrypted = decrypt_api_key(server.encrypted_env_vars)
                env_vars = json.loads(decrypted)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to decrypt environment variables"
                )

        # Connect and discover tools
        result = await test_mcp_connection(server, env_vars)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to connect to MCP server: {result['message']}"
            )

        # Update cache
        server.cached_tools = result.get("tools", [])
        server.tools_last_discovered_at = datetime.utcnow()
        server.last_connected_at = datetime.utcnow()
        server.last_error = None
        db.commit()

        tools = [
            MCPToolSchema(
                name=t["name"],
                description=t.get("description", ""),
                input_schema=t.get("input_schema", {})
            )
            for t in result.get("tools", [])
        ]

        return MCPServerToolsResponse(
            server_id=server.id,
            server_name=server.name,
            tools=tools,
            cached=False,
            last_discovered_at=server.tools_last_discovered_at
        )

    # Return cached tools
    tools = [
        MCPToolSchema(
            name=t["name"],
            description=t.get("description", ""),
            input_schema=t.get("input_schema", {})
        )
        for t in (server.cached_tools or [])
    ]

    return MCPServerToolsResponse(
        server_id=server.id,
        server_name=server.name,
        tools=tools,
        cached=True,
        last_discovered_at=server.tools_last_discovered_at
    )
