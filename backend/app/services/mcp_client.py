"""
MCP Client Service for connecting to Model Context Protocol servers.

Provides async client connections to MCP servers over stdio or SSE/HTTP transports.
Includes connection pooling for efficient reuse during agent execution.
"""
import asyncio
import logging
import json
import sys
from typing import Optional, Dict, Any, List, AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.sse import sse_client
from mcp import types as mcp_types

from ..models.mcp_server import MCPServerConfig, MCPTransportType
from ..encryption import decrypt_api_key


logger = logging.getLogger(__name__)


# Whitelist of allowed commands for MCP stdio transport
# This prevents arbitrary command execution via MCP server configuration
# Common MCP servers use npx (Node.js) or uvx (Python) package runners
ALLOWED_MCP_COMMANDS = frozenset({
    # Package runners (most common for MCP servers)
    "npx",          # Node.js package runner (npm)
    "uvx",          # Python package runner (uv)
    "pipx",         # Python package runner (pipx)

    # Direct interpreters (for local development)
    "node",         # Node.js runtime
    "python",       # Python interpreter
    "python3",      # Python 3 interpreter

    # Container execution (for isolated servers)
    "docker",       # Docker container execution
    "podman",       # Podman container execution
})


@dataclass
class MCPConnection:
    """Represents an active MCP connection with session and transport info."""
    session: ClientSession
    server_id: int
    server_name: str
    transport_type: MCPTransportType
    connected_at: datetime = field(default_factory=datetime.utcnow)

    # Transport-specific cleanup context managers
    _read_stream: Any = None
    _write_stream: Any = None


class MCPClientError(Exception):
    """Base exception for MCP client errors."""
    pass


class MCPConnectionError(MCPClientError):
    """Error establishing connection to MCP server."""
    pass


class MCPToolCallError(MCPClientError):
    """Error calling an MCP tool."""
    pass


class MCPClientService:
    """
    Service for connecting to and interacting with MCP servers.

    Supports both stdio (subprocess) and SSE (HTTP) transports.

    Usage:
        async with MCPClientService.connect(config, env_vars) as client:
            tools = await client.list_tools()
            result = await client.call_tool("tool_name", {"arg": "value"})
    """

    def __init__(
        self,
        config: MCPServerConfig,
        decrypted_env_vars: Optional[Dict[str, str]] = None
    ):
        """
        Initialize MCP client service.

        Args:
            config: MCP server configuration from database
            decrypted_env_vars: Pre-decrypted environment variables (optional)
        """
        self.config = config
        self._env_vars = decrypted_env_vars
        self._session: Optional[ClientSession] = None
        self._read_stream = None
        self._write_stream = None
        self._process = None

    def _get_env_vars(self) -> Optional[Dict[str, str]]:
        """Get decrypted environment variables."""
        if self._env_vars is not None:
            return self._env_vars

        if self.config.encrypted_env_vars:
            try:
                decrypted = decrypt_api_key(self.config.encrypted_env_vars)
                return json.loads(decrypted)
            except Exception as e:
                logger.error(f"Failed to decrypt env vars for {self.config.name}: {e}")
                return None
        return None

    @asynccontextmanager
    async def connect(self) -> AsyncGenerator["MCPClientService", None]:
        """
        Async context manager for establishing MCP connection.

        Yields:
            Self with active session ready for use.

        Raises:
            MCPConnectionError: If connection fails.
        """
        try:
            if self.config.transport_type == MCPTransportType.STDIO:
                async with self._connect_stdio() as session:
                    self._session = session
                    yield self
            elif self.config.transport_type in (MCPTransportType.SSE, MCPTransportType.STREAMABLE_HTTP):
                async with self._connect_sse() as session:
                    self._session = session
                    yield self
            else:
                raise MCPConnectionError(f"Unknown transport type: {self.config.transport_type}")
        finally:
            self._session = None

    @asynccontextmanager
    async def _connect_stdio(self) -> AsyncGenerator[ClientSession, None]:
        """Connect via stdio (subprocess) transport."""
        stdio_config = self.config.stdio_config or {}
        command = stdio_config.get("command")
        args = stdio_config.get("args", [])

        if not command:
            raise MCPConnectionError("stdio transport requires 'command' in stdio_config")

        # Security: Validate command against whitelist to prevent arbitrary command execution
        # Extract base command (handle paths like /usr/bin/npx)
        base_command = command.split("/")[-1] if "/" in command else command
        if base_command not in ALLOWED_MCP_COMMANDS:
            allowed_list = ", ".join(sorted(ALLOWED_MCP_COMMANDS))
            raise MCPConnectionError(
                f"Command '{command}' is not allowed for MCP servers. "
                f"Allowed commands: {allowed_list}"
            )

        env_vars = self._get_env_vars()

        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env_vars
        )

        logger.info(f"Connecting to MCP server '{self.config.name}' via stdio: {command} {' '.join(args)}")

        try:
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    # Initialize the session
                    await session.initialize()
                    logger.info(f"Connected to MCP server '{self.config.name}'")
                    yield session
        except Exception as e:
            logger.error(f"Failed to connect to MCP server '{self.config.name}': {e}")
            raise MCPConnectionError(f"Failed to connect via stdio: {e}") from e

    @asynccontextmanager
    async def _connect_sse(self) -> AsyncGenerator[ClientSession, None]:
        """Connect via SSE/HTTP transport."""
        http_config = self.config.http_config or {}
        url = http_config.get("url")
        headers = http_config.get("headers", {})

        if not url:
            raise MCPConnectionError("SSE transport requires 'url' in http_config")

        logger.info(f"Connecting to MCP server '{self.config.name}' via SSE: {url}")

        try:
            async with sse_client(url=url, headers=headers) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    # Initialize the session
                    await session.initialize()
                    logger.info(f"Connected to MCP server '{self.config.name}'")
                    yield session
        except Exception as e:
            logger.error(f"Failed to connect to MCP server '{self.config.name}': {e}")
            raise MCPConnectionError(f"Failed to connect via SSE: {e}") from e

    async def list_tools(self) -> List[mcp_types.Tool]:
        """
        List available tools from the MCP server.

        Returns:
            List of Tool objects with name, description, and input schema.

        Raises:
            MCPClientError: If not connected or listing fails.
        """
        if not self._session:
            raise MCPClientError("Not connected. Use 'async with client.connect()' first.")

        try:
            result = await self._session.list_tools()
            return result.tools
        except Exception as e:
            logger.error(f"Failed to list tools from '{self.config.name}': {e}")
            raise MCPClientError(f"Failed to list tools: {e}") from e

    async def call_tool(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> mcp_types.CallToolResult:
        """
        Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool

        Returns:
            CallToolResult with content and metadata.

        Raises:
            MCPToolCallError: If the tool call fails.
        """
        if not self._session:
            raise MCPClientError("Not connected. Use 'async with client.connect()' first.")

        try:
            result = await self._session.call_tool(tool_name, arguments or {})

            if result.isError:
                # Extract error message from content
                error_msg = self._extract_text_content(result)
                raise MCPToolCallError(f"Tool '{tool_name}' returned error: {error_msg}")

            return result
        except MCPToolCallError:
            raise
        except Exception as e:
            logger.error(f"Failed to call tool '{tool_name}' on '{self.config.name}': {e}")
            raise MCPToolCallError(f"Failed to call tool '{tool_name}': {e}") from e

    def _extract_text_content(self, result: mcp_types.CallToolResult) -> str:
        """Extract text content from a CallToolResult."""
        texts = []
        for item in result.content:
            if hasattr(item, 'text'):
                texts.append(item.text)
            elif hasattr(item, 'data'):
                texts.append(f"[{item.type} data]")
        return "\n".join(texts) if texts else "[No content]"


class MCPConnectionPool:
    """
    Connection pool for MCP servers during agent execution.

    Maintains active connections to MCP servers for the duration of an
    agent execution, allowing tool calls without reconnecting each time.

    Usage:
        pool = MCPConnectionPool()
        async with pool:
            await pool.add_server(config1)
            await pool.add_server(config2)

            tools = await pool.get_all_tools()
            result = await pool.call_tool(server_id, "tool_name", {})
    """

    def __init__(self):
        self._connections: Dict[int, MCPConnection] = {}
        self._clients: Dict[int, MCPClientService] = {}
        self._context_managers: Dict[int, Any] = {}
        self._lock = asyncio.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    @property
    def loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """Get the event loop where connections were created."""
        return self._loop

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_all()

    async def add_server(
        self,
        config: MCPServerConfig,
        env_vars: Optional[Dict[str, str]] = None
    ) -> List[mcp_types.Tool]:
        """
        Add an MCP server to the pool and connect.

        Args:
            config: MCP server configuration
            env_vars: Pre-decrypted environment variables

        Returns:
            List of tools available from this server.

        Raises:
            MCPConnectionError: If connection fails.
        """
        async with self._lock:
            # Capture the event loop on first connection
            if self._loop is None:
                self._loop = asyncio.get_running_loop()

            if config.id in self._connections:
                # Already connected, return cached tools
                client = self._clients.get(config.id)
                if client:
                    return await client.list_tools()
                return []

            client = MCPClientService(config, env_vars)
            self._clients[config.id] = client

            # Enter the connection context
            cm = client.connect()
            connected_client = await cm.__aenter__()
            self._context_managers[config.id] = cm

            # Get tools
            tools = await connected_client.list_tools()

            # Store connection info
            self._connections[config.id] = MCPConnection(
                session=connected_client._session,
                server_id=config.id,
                server_name=config.name,
                transport_type=config.transport_type
            )

            logger.info(f"Added MCP server '{config.name}' to pool with {len(tools)} tools")
            return tools

    async def get_all_tools(self) -> Dict[int, List[mcp_types.Tool]]:
        """
        Get all tools from all connected servers.

        Returns:
            Dict mapping server_id to list of tools.
        """
        async with self._lock:
            result = {}
            for server_id, client in self._clients.items():
                if client._session:
                    try:
                        tools = await client.list_tools()
                        result[server_id] = tools
                    except Exception as e:
                        logger.error(f"Failed to get tools from server {server_id}: {e}")
                        result[server_id] = []
            return result

    async def call_tool(
        self,
        server_id: int,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> mcp_types.CallToolResult:
        """
        Call a tool on a specific server.

        Args:
            server_id: ID of the MCP server
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            CallToolResult from the tool.

        Raises:
            MCPClientError: If server not connected.
            MCPToolCallError: If tool call fails.
        """
        client = self._clients.get(server_id)
        if not client or not client._session:
            raise MCPClientError(f"Server {server_id} not connected")

        return await client.call_tool(tool_name, arguments)

    def get_connection(self, server_id: int) -> Optional[MCPConnection]:
        """Get connection info for a server."""
        return self._connections.get(server_id)

    def is_connected(self, server_id: int) -> bool:
        """Check if a server is connected."""
        return server_id in self._connections

    async def close_all(self):
        """Close all connections in the pool."""
        async with self._lock:
            for server_id, cm in list(self._context_managers.items()):
                try:
                    await cm.__aexit__(None, None, None)
                    logger.info(f"Closed connection to MCP server {server_id}")
                except Exception as e:
                    logger.error(f"Error closing MCP connection {server_id}: {e}")

            self._connections.clear()
            self._clients.clear()
            self._context_managers.clear()


async def test_mcp_connection(
    config: MCPServerConfig,
    env_vars: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Test connection to an MCP server and discover tools.

    Args:
        config: MCP server configuration
        env_vars: Pre-decrypted environment variables

    Returns:
        Dict with success, message, tools_count, and latency_ms.
    """
    import time
    start = time.time()

    try:
        client = MCPClientService(config, env_vars)
        async with client.connect():
            tools = await client.list_tools()
            latency_ms = int((time.time() - start) * 1000)

            return {
                "success": True,
                "message": f"Connected successfully. Found {len(tools)} tools.",
                "tools_count": len(tools),
                "latency_ms": latency_ms,
                "tools": [
                    {
                        "name": t.name,
                        "description": t.description or "",
                        "input_schema": t.inputSchema
                    }
                    for t in tools
                ]
            }
    except MCPConnectionError as e:
        return {
            "success": False,
            "message": str(e),
            "tools_count": 0,
            "latency_ms": None,
            "tools": []
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Unexpected error: {e}",
            "tools_count": 0,
            "latency_ms": None,
            "tools": []
        }
