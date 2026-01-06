"""
Pydantic schemas for MCP Server Configuration.

Security Note: Environment variables may contain secrets and are NEVER
included in response schemas. Use has_env_vars flag instead.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


# Re-export enum for schema use
class MCPTransportType(str, Enum):
    """MCP transport types"""
    STDIO = "stdio"
    SSE = "sse"
    STREAMABLE_HTTP = "streamable_http"


# ============================================================================
# Configuration Sub-Schemas
# ============================================================================

class StdioConfig(BaseModel):
    """Configuration for stdio transport (subprocess)"""
    command: str = Field(..., description="Command to execute (e.g., 'npx', 'python')")
    args: List[str] = Field(default_factory=list, description="Command arguments")


class HttpConfig(BaseModel):
    """Configuration for HTTP/SSE transport (remote server)"""
    url: str = Field(..., description="Server URL (e.g., 'http://localhost:3000/mcp')")
    headers: Dict[str, str] = Field(default_factory=dict, description="HTTP headers (may include auth)")


# ============================================================================
# Request Schemas
# ============================================================================

class MCPServerConfigBase(BaseModel):
    """Base schema for MCP server configuration"""
    name: str = Field(..., max_length=255, description="User-defined name for this server")
    description: Optional[str] = Field(None, description="Optional description")
    transport_type: MCPTransportType = Field(..., description="Transport type (stdio or sse)")
    config: Dict[str, Any] = Field(default_factory=dict, description="Additional MCP-specific configuration")


class MCPServerConfigCreate(MCPServerConfigBase):
    """
    Schema for creating a new MCP server configuration.

    For stdio transport, provide stdio_config with command and args.
    For SSE/HTTP transport, provide http_config with url and optional headers.
    Environment variables will be encrypted before storage.
    """
    stdio_config: Optional[Dict[str, Any]] = Field(
        None,
        description="Stdio transport config: {command: string, args: string[]}"
    )
    http_config: Optional[Dict[str, Any]] = Field(
        None,
        description="HTTP transport config: {url: string, headers?: object}"
    )
    env_vars: Optional[Dict[str, str]] = Field(
        None,
        description="Environment variables (will be encrypted)"
    )


class MCPServerConfigUpdate(BaseModel):
    """
    Schema for updating MCP server configuration.

    All fields are optional. Only provided fields will be updated.
    """
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    stdio_config: Optional[Dict[str, Any]] = None
    http_config: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None
    env_vars: Optional[Dict[str, str]] = Field(
        None,
        description="Environment variables (will be encrypted). Set to {} to clear."
    )
    is_active: Optional[bool] = None


# ============================================================================
# Response Schemas
# ============================================================================

class MCPServerConfigResponse(MCPServerConfigBase):
    """
    Schema for MCP server configuration response.

    SECURITY: Environment variables are NEVER included in responses.
    Use has_env_vars flag to check if env vars are configured.
    """
    id: int
    user_id: int
    stdio_config: Optional[Dict[str, Any]]
    http_config: Optional[Dict[str, Any]]
    has_env_vars: bool = Field(..., description="Indicates if environment variables are configured")
    cached_tools_count: int = Field(..., description="Number of cached tools from last discovery")
    tools_last_discovered_at: Optional[datetime] = Field(None, description="When tools were last discovered")
    is_active: bool
    last_connected_at: Optional[datetime] = Field(None, description="Last successful connection time")
    last_error: Optional[str] = Field(None, description="Last connection error message")
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class MCPServerConfigListResponse(BaseModel):
    """Schema for paginated MCP server configuration list"""
    servers: List[MCPServerConfigResponse]
    total: int = Field(..., description="Total number of server configs")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")


# ============================================================================
# Tool Discovery Schemas
# ============================================================================

class MCPToolSchema(BaseModel):
    """Schema for a single MCP tool"""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    input_schema: Dict[str, Any] = Field(..., description="JSON Schema for tool inputs")


class MCPServerToolsResponse(BaseModel):
    """Schema for tools discovery response"""
    server_id: int
    server_name: str
    tools: List[MCPToolSchema]
    cached: bool = Field(..., description="Whether these are cached tools or freshly discovered")
    last_discovered_at: Optional[datetime]


# ============================================================================
# Test/Validation Schemas
# ============================================================================

class MCPServerTestResponse(BaseModel):
    """Schema for MCP server connection test response"""
    success: bool = Field(..., description="Whether the connection test succeeded")
    message: str = Field(..., description="Status message or error description")
    tools_count: int = Field(..., description="Number of tools discovered")
    latency_ms: Optional[int] = Field(None, description="Connection latency in milliseconds")
    tools: Optional[List[MCPToolSchema]] = Field(None, description="Discovered tools list")


# ============================================================================
# Agent Association Schemas
# ============================================================================

class AgentMCPServerAssignment(BaseModel):
    """Schema for assigning MCP servers to an agent"""
    mcp_server_ids: List[int] = Field(..., description="List of MCP server IDs to assign")
