"""
MCP Tool Wrapper for LangChain Integration.

Wraps MCP tools as LangChain-compatible tools for use in agents.
Handles tool naming, argument passing, and result formatting.
"""
import asyncio
import logging
import json
import concurrent.futures
import threading
from typing import Any, Dict, List, Optional, Tuple, Type
from langchain.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field, create_model
import nest_asyncio

from mcp import types as mcp_types

from .mcp_client import MCPConnectionPool, MCPClientService, MCPToolCallError
from ..models.mcp_server import MCPServerConfig


logger = logging.getLogger(__name__)


def json_schema_to_pydantic(schema: Dict[str, Any], model_name: str = "DynamicModel") -> Type[BaseModel]:
    """
    Convert a JSON schema to a Pydantic model for LangChain args_schema.

    Args:
        schema: JSON schema dict with 'properties' and optionally 'required'
        model_name: Name for the generated model

    Returns:
        A Pydantic model class
    """
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    field_definitions = {}

    for prop_name, prop_schema in properties.items():
        # Determine the Python type from JSON schema type
        json_type = prop_schema.get("type", "string")
        python_type: Any = str  # Default

        if json_type == "string":
            python_type = str
        elif json_type == "integer":
            python_type = int
        elif json_type == "number":
            python_type = float
        elif json_type == "boolean":
            python_type = bool
        elif json_type == "array":
            python_type = list
        elif json_type == "object":
            python_type = dict

        # Get description
        description = prop_schema.get("description", "")

        # Determine if required or optional
        if prop_name in required:
            # Required field
            field_definitions[prop_name] = (python_type, Field(description=description))
        else:
            # Optional field with default None
            field_definitions[prop_name] = (Optional[python_type], Field(default=None, description=description))

    # Create the model dynamically
    if not field_definitions:
        # No properties - create empty model
        field_definitions["_placeholder"] = (Optional[str], Field(default=None, description="No parameters required"))

    return create_model(model_name, **field_definitions)


def sanitize_tool_name(name: str) -> str:
    """
    Sanitize a tool name for LangChain compatibility.

    LangChain tool names must be alphanumeric with underscores.
    """
    import re
    # Replace non-alphanumeric chars (except underscore) with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    # Collapse multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Ensure it starts with a letter
    if sanitized and not sanitized[0].isalpha():
        sanitized = 'tool_' + sanitized
    return sanitized or 'unnamed_tool'


def make_mcp_tool_name(server_name: str, tool_name: str) -> str:
    """
    Create a unique LangChain tool name for an MCP tool.

    Format: mcp_{server_name}_{tool_name}

    Args:
        server_name: Name of the MCP server
        tool_name: Name of the tool from MCP

    Returns:
        Sanitized, unique tool name
    """
    server_part = sanitize_tool_name(server_name.lower().replace(' ', '_'))
    tool_part = sanitize_tool_name(tool_name)
    return f"mcp_{server_part}_{tool_part}"


class MCPToolWrapper(BaseTool):
    """
    LangChain tool wrapper for MCP tools.

    Wraps an MCP tool to be used in LangChain agents.
    Uses the MCPConnectionPool to make tool calls.
    """
    name: str = ""
    description: str = ""
    server_id: int = 0
    server_name: str = ""
    original_tool_name: str = ""
    input_schema_def: Dict[str, Any] = Field(default_factory=dict)
    connection_pool: Optional[MCPConnectionPool] = None
    # args_schema will be set dynamically during wrapper creation

    class Config:
        arbitrary_types_allowed = True

    def _run(self, **kwargs) -> str:
        """
        Execute the MCP tool synchronously.

        This runs the async version in the same event loop where MCP
        connections were created. Uses nest_asyncio to allow nested
        event loop execution, which is required because LangChain's
        AgentExecutor.invoke() calls tools synchronously even within
        an async context.
        """
        if not self.connection_pool:
            return f"Error: No connection pool set for tool {self.name}"

        # Get the event loop from the connection pool
        pool_loop = self.connection_pool.loop
        if pool_loop is None:
            return f"Error: Connection pool has no event loop"

        try:
            # Check if we're in the same thread as the pool's event loop
            # If yes, we need to use nest_asyncio for nested execution
            # If no (different thread), use run_coroutine_threadsafe

            current_thread = threading.current_thread()
            pool_thread_id = getattr(pool_loop, '_thread_id', None)

            # Try to determine if we're in the same thread as the loop
            # The loop is "running" when we're inside an async context
            if pool_loop.is_running():
                # Loop is running - check if same thread
                if pool_thread_id is None or pool_thread_id == current_thread.ident:
                    # Same thread - apply nest_asyncio and run directly
                    # This allows nested run_until_complete calls
                    nest_asyncio.apply(pool_loop)
                    return pool_loop.run_until_complete(self._arun(**kwargs))
                else:
                    # Different thread - use run_coroutine_threadsafe
                    future = asyncio.run_coroutine_threadsafe(self._arun(**kwargs), pool_loop)
                    return future.result(timeout=60)
            else:
                # Loop is not running - run directly
                return pool_loop.run_until_complete(self._arun(**kwargs))

        except concurrent.futures.TimeoutError:
            return f"Error: Tool {self.name} timed out after 60 seconds"
        except Exception as e:
            logger.error(f"Error executing MCP tool {self.name}: {e}")
            return f"Error: {str(e)}"

    async def _arun(self, **kwargs) -> str:
        """
        Execute the MCP tool asynchronously.

        Args:
            **kwargs: Tool arguments

        Returns:
            Tool result as string
        """
        if not self.connection_pool:
            return f"Error: No connection pool set for tool {self.name}"

        if not self.connection_pool.is_connected(self.server_id):
            return f"Error: MCP server {self.server_name} is not connected"

        # Extract arguments
        # Handle different argument passing styles from LangChain
        tool_args = {}

        # If we got a 'tool_input' argument (ReAct style), try to parse it
        if 'tool_input' in kwargs:
            tool_input = kwargs['tool_input']
            if isinstance(tool_input, str):
                # Try to parse as JSON
                try:
                    parsed = json.loads(tool_input)
                    if isinstance(parsed, dict):
                        tool_args = parsed
                    else:
                        # Single value - try to map to first property
                        props = self.input_schema_def.get('properties', {})
                        if props:
                            first_prop = next(iter(props.keys()))
                            tool_args = {first_prop: parsed}
                        else:
                            tool_args = {'input': parsed}
                except json.JSONDecodeError:
                    # Not JSON - use as single string input
                    props = self.input_schema_def.get('properties', {})
                    if props:
                        first_prop = next(iter(props.keys()))
                        tool_args = {first_prop: tool_input}
                    else:
                        tool_args = {'input': tool_input}
            elif isinstance(tool_input, dict):
                tool_args = tool_input
            else:
                tool_args = {'input': tool_input}
        else:
            # Direct keyword arguments (tool-calling style)
            tool_args = {k: v for k, v in kwargs.items()
                        if not k.startswith('_')}

        try:
            result = await self.connection_pool.call_tool(
                self.server_id,
                self.original_tool_name,
                tool_args
            )

            # Format result
            return self._format_result(result)

        except MCPToolCallError as e:
            return f"Tool error: {str(e)}"
        except Exception as e:
            logger.error(f"Error calling MCP tool {self.name}: {e}")
            return f"Error: {str(e)}"

    def _format_result(self, result: mcp_types.CallToolResult) -> str:
        """Format MCP tool result as string for LangChain."""
        texts = []

        for item in result.content:
            if hasattr(item, 'text'):
                texts.append(item.text)
            elif hasattr(item, 'data'):
                # Binary data - describe it
                texts.append(f"[{item.type} data: {len(item.data)} bytes]")
            elif hasattr(item, 'uri'):
                texts.append(f"[Resource: {item.uri}]")

        if result.structuredContent:
            texts.append(json.dumps(result.structuredContent, indent=2, default=str))

        return "\n".join(texts) if texts else "[No output]"


def create_mcp_tools_from_server(
    config: MCPServerConfig,
    tools: List[mcp_types.Tool],
    connection_pool: MCPConnectionPool
) -> List[MCPToolWrapper]:
    """
    Create LangChain tool wrappers for all tools from an MCP server.

    Args:
        config: MCP server configuration
        tools: List of tools discovered from the server
        connection_pool: Active connection pool to use for tool calls

    Returns:
        List of MCPToolWrapper instances
    """
    wrappers = []

    for tool in tools:
        tool_name = make_mcp_tool_name(config.name, tool.name)
        description = tool.description or f"MCP tool from {config.name}"

        # Add server info to description
        full_description = f"[MCP:{config.name}] {description}"

        # Generate args_schema from the tool's input schema
        # This is required for LangChain's tool-calling agents to know
        # what arguments the tool expects
        args_schema_model = json_schema_to_pydantic(
            tool.inputSchema,
            f"{sanitize_tool_name(tool_name)}Input"
        )

        wrapper = MCPToolWrapper(
            name=tool_name,
            description=full_description,
            server_id=config.id,
            server_name=config.name,
            original_tool_name=tool.name,
            input_schema_def=tool.inputSchema,
            connection_pool=connection_pool,
            args_schema=args_schema_model
        )

        wrappers.append(wrapper)
        logger.debug(f"Created MCP tool wrapper: {tool_name} with schema: {tool.inputSchema}")

    return wrappers


async def create_mcp_tools_for_agent(
    configs: List[MCPServerConfig],
    connection_pool: MCPConnectionPool,
    decrypted_env_vars: Optional[Dict[int, Dict[str, str]]] = None
) -> Tuple[List[MCPToolWrapper], Dict[int, str]]:
    """
    Create MCP tool wrappers for all servers assigned to an agent.

    This connects to each MCP server and creates tool wrappers for their tools.

    Args:
        configs: List of MCP server configurations
        connection_pool: Connection pool to manage connections
        decrypted_env_vars: Optional dict mapping server_id to decrypted env vars

    Returns:
        Tuple of (list of tool wrappers, dict of server_id to error messages)
    """
    all_tools: List[MCPToolWrapper] = []
    errors: Dict[int, str] = {}

    for config in configs:
        if not config.is_active:
            logger.info(f"Skipping inactive MCP server: {config.name}")
            continue

        try:
            # Get env vars for this server
            env_vars = None
            if decrypted_env_vars:
                env_vars = decrypted_env_vars.get(config.id)

            # Connect and get tools
            mcp_tools = await connection_pool.add_server(config, env_vars)

            # Create wrappers
            wrappers = create_mcp_tools_from_server(config, mcp_tools, connection_pool)
            all_tools.extend(wrappers)

            logger.info(f"Loaded {len(wrappers)} tools from MCP server '{config.name}'")

        except Exception as e:
            error_msg = str(e)
            errors[config.id] = error_msg
            logger.error(f"Failed to load MCP server '{config.name}': {error_msg}")

    return all_tools, errors


def get_mcp_tool_info(wrapper: MCPToolWrapper) -> Dict[str, Any]:
    """
    Get information about an MCP tool wrapper.

    Args:
        wrapper: MCPToolWrapper instance

    Returns:
        Dict with tool info including server, name, description, schema
    """
    return {
        "name": wrapper.name,
        "original_name": wrapper.original_tool_name,
        "server_name": wrapper.server_name,
        "server_id": wrapper.server_id,
        "description": wrapper.description,
        "input_schema": wrapper.input_schema_def,
        "is_mcp": True
    }
