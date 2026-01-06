"""
Tool Wrapper Service for LangChain Integration.

This module wraps DeepAgentStudio tools as LangChain-compatible tools.

Supports:
- Built-in tools: Python Code Execution and HTTP Request
- Custom tools: Create dynamic tools that execute user code via SandboxService
"""
from typing import Any, Dict, List, Optional, Type, Callable
from langchain.tools import BaseTool, StructuredTool, Tool as LangChainTool
from pydantic import BaseModel, Field, create_model
from sqlalchemy.orm import Session
import logging
import json

from ..models.tool import Tool, ToolType, agent_tools
from .sandbox import SandboxService, SandboxResult, get_sandbox_service

logger = logging.getLogger(__name__)


class ToolWrapperError(Exception):
    """Exception raised when tool wrapping fails"""
    pass


class UnsupportedToolError(ToolWrapperError):
    """Exception raised for unsupported tool types"""
    pass


# Mapping of langchain_class names to actual tool classes/factories
BUILTIN_TOOL_REGISTRY: Dict[str, Callable[[], BaseTool]] = {
    "PythonCodeExecution": lambda: _create_python_execution_tool(),
    "HTTPRequest": lambda: _create_http_request_tool(),
}


def _create_python_execution_tool() -> BaseTool:
    """
    Create a Python code execution tool.

    This tool executes Python code in a controlled environment with access to
    common libraries like json, datetime, math, re, collections, etc.
    """
    import io
    import sys
    from contextlib import redirect_stdout, redirect_stderr

    def execute_python(code: str) -> str:
        """Execute Python code and return the result"""
        import ast

        # Allowed modules for import
        allowed_modules = {
            'json': __import__('json'),
            'math': __import__('math'),
            're': __import__('re'),
            'datetime': __import__('datetime'),
            'collections': __import__('collections'),
            'itertools': __import__('itertools'),
            'functools': __import__('functools'),
            'random': __import__('random'),
            'string': __import__('string'),
            'textwrap': __import__('textwrap'),
            'urllib.parse': __import__('urllib.parse'),
            'base64': __import__('base64'),
            'hashlib': __import__('hashlib'),
            'statistics': __import__('statistics'),
        }

        # Create execution environment
        exec_globals = {
            '__builtins__': {
                # Safe builtins
                'abs': abs,
                'all': all,
                'any': any,
                'bool': bool,
                'dict': dict,
                'enumerate': enumerate,
                'filter': filter,
                'float': float,
                'format': format,
                'frozenset': frozenset,
                'getattr': getattr,
                'hasattr': hasattr,
                'hash': hash,
                'int': int,
                'isinstance': isinstance,
                'issubclass': issubclass,
                'iter': iter,
                'len': len,
                'list': list,
                'map': map,
                'max': max,
                'min': min,
                'next': next,
                'ord': ord,
                'pow': pow,
                'print': print,
                'range': range,
                'repr': repr,
                'reversed': reversed,
                'round': round,
                'set': set,
                'slice': slice,
                'sorted': sorted,
                'str': str,
                'sum': sum,
                'tuple': tuple,
                'type': type,
                'zip': zip,
                'True': True,
                'False': False,
                'None': None,
                '__import__': lambda name, *args, **kwargs: allowed_modules.get(name.split('.')[0]),
            },
            # Pre-import common modules
            'json': allowed_modules['json'],
            'math': allowed_modules['math'],
            're': allowed_modules['re'],
            'datetime': allowed_modules['datetime'],
            'collections': allowed_modules['collections'],
            'random': allowed_modules['random'],
        }
        exec_locals = {}

        # Capture stdout
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            # Try to capture the result of the last expression
            # Parse the code to see if the last statement is an expression
            last_expr_result = None
            try:
                tree = ast.parse(code)
                if tree.body and isinstance(tree.body[-1], ast.Expr):
                    # Last statement is an expression - extract it
                    last_expr = tree.body[-1]
                    # Execute all but the last statement
                    if len(tree.body) > 1:
                        module_without_last = ast.Module(body=tree.body[:-1], type_ignores=[])
                        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                            exec(compile(module_without_last, '<string>', 'exec'), exec_globals, exec_locals)
                    # Evaluate the last expression
                    expr_code = compile(ast.Expression(body=last_expr.value), '<string>', 'eval')
                    last_expr_result = eval(expr_code, exec_globals, exec_locals)
                else:
                    # No trailing expression, execute normally
                    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                        exec(code, exec_globals, exec_locals)
            except SyntaxError:
                # If parsing fails, just execute normally
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    exec(code, exec_globals, exec_locals)

            # Get printed output
            stdout_output = stdout_capture.getvalue()
            stderr_output = stderr_capture.getvalue()

            # Priority 1: Return the last expression result if we captured one
            if last_expr_result is not None:
                if isinstance(last_expr_result, (dict, list, tuple)):
                    return json.dumps(last_expr_result, indent=2, default=str)
                return str(last_expr_result)

            # Priority 2: Check for 'result' variable (common pattern)
            if 'result' in exec_locals:
                result_value = exec_locals['result']
                if isinstance(result_value, (dict, list, tuple)):
                    return json.dumps(result_value, indent=2, default=str)
                return str(result_value)

            # Priority 3: Return stdout if available
            if stdout_output:
                return stdout_output.strip()

            # Priority 4: Return stderr if available (for debugging)
            if stderr_output:
                return f"stderr: {stderr_output.strip()}"

            # Priority 5: Return all user-defined variables as a dict
            user_vars = {k: v for k, v in exec_locals.items()
                        if not k.startswith('_') and k not in allowed_modules}

            if user_vars:
                # Return ALL user variables as JSON for better visibility
                return json.dumps(user_vars, indent=2, default=str)

            return "Code executed successfully (no output)"

        except SyntaxError as e:
            return f"Syntax Error: {str(e)}"
        except NameError as e:
            return f"Name Error: {str(e)}"
        except TypeError as e:
            return f"Type Error: {str(e)}"
        except ValueError as e:
            return f"Value Error: {str(e)}"
        except Exception as e:
            return f"Error: {type(e).__name__}: {str(e)}"

    return StructuredTool.from_function(
        func=execute_python,
        name="python_code_execution",
        description="""Execute Python code and return the result.
Use the 'result' variable to store output, or use print() statements.
Available modules: json, math, re, datetime, collections, itertools, functools, random, string, base64, hashlib, statistics.
Example: 'import math; result = math.sqrt(16)' returns '4.0'"""
    )


def _create_http_request_tool() -> BaseTool:
    """
    Create an HTTP request tool supporting multiple methods.

    Supports GET, POST, PUT, PATCH, DELETE with JSON body and custom headers.
    """
    import httpx

    def make_http_request(request_config: str) -> str:
        """
        Make an HTTP request based on the configuration.

        Args:
            request_config: JSON string with url, method, headers, data, params, timeout

        Returns:
            Response body as string (JSON formatted if applicable)
        """
        try:
            # Parse the request configuration
            if isinstance(request_config, str):
                # Try to parse as JSON first
                try:
                    config = json.loads(request_config)
                except json.JSONDecodeError:
                    # If not JSON, treat as a simple URL (GET request)
                    config = {"url": request_config}
            else:
                config = request_config

            # Extract request parameters
            url = config.get("url")
            if not url:
                return "Error: URL is required"

            method = config.get("method", "GET").upper()
            headers = config.get("headers", {})
            data = config.get("data")
            params = config.get("params")
            timeout = config.get("timeout", 30)

            # Validate method
            valid_methods = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
            if method not in valid_methods:
                return f"Error: Invalid method '{method}'. Supported: {', '.join(valid_methods)}"

            # Build request kwargs
            request_kwargs = {
                "timeout": timeout,
                "follow_redirects": True,
            }

            if headers:
                request_kwargs["headers"] = headers

            if params:
                request_kwargs["params"] = params

            # Add JSON body for methods that support it
            if data and method in {"POST", "PUT", "PATCH"}:
                if isinstance(data, dict):
                    request_kwargs["json"] = data
                else:
                    request_kwargs["content"] = str(data)

            # Make the request
            with httpx.Client() as client:
                if method == "GET":
                    response = client.get(url, **request_kwargs)
                elif method == "POST":
                    response = client.post(url, **request_kwargs)
                elif method == "PUT":
                    response = client.put(url, **request_kwargs)
                elif method == "PATCH":
                    response = client.patch(url, **request_kwargs)
                elif method == "DELETE":
                    response = client.delete(url, **request_kwargs)
                elif method == "HEAD":
                    response = client.head(url, **request_kwargs)
                elif method == "OPTIONS":
                    response = client.options(url, **request_kwargs)

            # Build response
            result = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
            }

            # Try to parse response as JSON
            try:
                result["body"] = response.json()
            except (json.JSONDecodeError, ValueError):
                # Return text body, limited to prevent huge responses
                body_text = response.text
                if len(body_text) > 10000:
                    body_text = body_text[:10000] + "\n... (truncated)"
                result["body"] = body_text

            return json.dumps(result, indent=2, default=str)

        except httpx.TimeoutException:
            return "Error: Request timed out"
        except httpx.ConnectError as e:
            return f"Error: Connection failed - {str(e)}"
        except httpx.HTTPStatusError as e:
            return f"Error: HTTP {e.response.status_code} - {str(e)}"
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON in request config - {str(e)}"
        except Exception as e:
            return f"Error: {type(e).__name__}: {str(e)}"

    return StructuredTool.from_function(
        func=make_http_request,
        name="http_request",
        description="""Make HTTP requests to external APIs.
Input: JSON object with url (required), method (GET/POST/PUT/PATCH/DELETE), headers, data, params, timeout.
Examples:
- '{"url": "https://api.example.com/data"}' for GET
- '{"url": "https://api.example.com/items", "method": "POST", "data": {"name": "test"}}' for POST
Returns: JSON with status_code, headers, and body."""
    )


class CustomToolWrapper(BaseTool):
    """
    LangChain tool wrapper for custom user-defined tools.

    Executes tool code via SandboxService.
    """
    name: str = ""
    description: str = ""
    tool_id: int = 0
    function_code: str = ""
    input_schema_def: Optional[Dict[str, Any]] = None

    class Config:
        arbitrary_types_allowed = True

    def _extract_first_param_inputs(self, tool_input: str) -> Dict[str, Any]:
        """
        Extract first parameter name from function code and create inputs dict.
        Falls back to 'input' if parsing fails.
        """
        import re
        # Try to extract function signature like: def func_name(param1: type, ...)
        match = re.search(r'def\s+\w+\s*\(\s*(\w+)', self.function_code)
        if match:
            param_name = match.group(1)
            return {param_name: tool_input}
        return {"input": tool_input}

    def _run(self, tool_input: str = "", **kwargs) -> str:
        """Execute the custom tool"""
        sandbox = get_sandbox_service()

        # Get the actual parameter name from function signature (source of truth)
        # The function signature is what the code actually expects
        import re
        actual_param_name = None
        match = re.search(r'def\s+\w+\s*\(\s*(\w+)', self.function_code)
        if match:
            actual_param_name = match.group(1)

        # Fall back to schema if function parsing fails
        if not actual_param_name:
            if self.input_schema_def and "properties" in self.input_schema_def:
                param_names = list(self.input_schema_def["properties"].keys())
                if param_names:
                    actual_param_name = param_names[0]

        if not actual_param_name:
            actual_param_name = "input"

        # Handle different argument passing styles
        inputs = {}

        # Check for tool_input in kwargs (tool-calling agents use this)
        if "tool_input" in kwargs:
            inputs[actual_param_name] = kwargs["tool_input"]
        # Check for direct tool_input parameter (text-based ReAct agents)
        elif tool_input:
            inputs[actual_param_name] = tool_input
        # Check if kwargs contains the actual parameter name already
        elif actual_param_name in kwargs:
            inputs[actual_param_name] = kwargs[actual_param_name]
        # Otherwise, use all kwargs (might be multi-param tool)
        elif kwargs:
            # Map any remaining kwargs, handling tool_input specially
            for key, value in kwargs.items():
                if key == "tool_input":
                    inputs[actual_param_name] = value
                else:
                    inputs[key] = value

        # Execute the tool as a function (the code defines a function)
        # The function name should match the tool name
        result = sandbox.execute_function(
            func_code=self.function_code,
            func_name=self.name,
            args=inputs,
            timeout_seconds=30
        )

        if result.success:
            # Convert output to string for LangChain
            output = result.output
            if output is None:
                return "Tool executed successfully but returned no result"
            return str(output)
        else:
            return f"Tool error: {result.error}"

    async def _arun(self, tool_input: str = "", **kwargs) -> str:
        """Async execution (runs sync version)"""
        return self._run(tool_input, **kwargs)


class ToolLoader:
    """
    Service for loading and wrapping tools for LangChain agents.

    Handles:
    - Loading tools from database
    - Wrapping built-in tools
    - Wrapping custom tools
    - Tool configuration overrides
    """

    def __init__(self, db: Session, sandbox: Optional[SandboxService] = None):
        """
        Initialize tool loader.

        Args:
            db: Database session
            sandbox: Optional SandboxService (uses singleton if not provided)
        """
        self.db = db
        self.sandbox = sandbox or get_sandbox_service()

    def load_tools_for_agent(
        self,
        agent_id: int,
        user_id: int
    ) -> List[BaseTool]:
        """
        Load all tools assigned to an agent.

        Args:
            agent_id: Agent ID
            user_id: User ID (for access validation)

        Returns:
            List of LangChain-compatible tools
        """
        # Get tool assignments for this agent
        assignments = self.db.execute(
            agent_tools.select().where(agent_tools.c.agent_id == agent_id)
        ).all()

        tools = []
        for assignment in assignments:
            tool_id = assignment.tool_id
            config_override = assignment.config or {}

            try:
                tool = self.load_tool(tool_id, user_id, config_override)
                if tool:
                    tools.append(tool)
            except Exception as e:
                logger.warning(f"Failed to load tool {tool_id}: {str(e)}")

        return tools

    def load_tools_by_ids(
        self,
        tool_ids: List[int],
        user_id: int
    ) -> List[BaseTool]:
        """
        Load tools by their IDs.

        Args:
            tool_ids: List of tool IDs to load
            user_id: User ID (for access validation)

        Returns:
            List of LangChain-compatible tools
        """
        tools = []
        for tool_id in tool_ids:
            try:
                tool = self.load_tool(tool_id, user_id)
                if tool:
                    tools.append(tool)
            except Exception as e:
                logger.warning(f"Failed to load tool {tool_id}: {str(e)}")

        return tools

    def load_tool(
        self,
        tool_id: int,
        user_id: int,
        config_override: Optional[Dict[str, Any]] = None
    ) -> Optional[BaseTool]:
        """
        Load a single tool by ID.

        Args:
            tool_id: Tool ID
            user_id: User ID (for access validation)
            config_override: Optional config to override tool defaults

        Returns:
            LangChain-compatible tool, or None if not found

        Raises:
            ToolWrapperError: If tool loading fails
        """
        # Query tool from database
        tool_model = self.db.query(Tool).filter(Tool.id == tool_id).first()

        if not tool_model:
            logger.warning(f"Tool {tool_id} not found")
            return None

        if not tool_model.is_active:
            logger.warning(f"Tool {tool_id} is not active")
            return None

        # Check access - built-in tools are public, custom tools are user-specific
        if tool_model.tool_type == ToolType.CUSTOM:
            if tool_model.user_id != user_id:
                logger.warning(f"User {user_id} does not have access to tool {tool_id}")
                return None

        # Wrap the tool based on its type
        if tool_model.tool_type == ToolType.BUILTIN:
            return self._wrap_builtin_tool(tool_model, config_override)
        else:
            return self._wrap_custom_tool(tool_model, config_override)

    def _wrap_builtin_tool(
        self,
        tool_model: Tool,
        config_override: Optional[Dict[str, Any]] = None
    ) -> Optional[BaseTool]:
        """
        Wrap a built-in tool.

        Args:
            tool_model: Tool database model
            config_override: Optional configuration override

        Returns:
            LangChain tool instance
        """
        langchain_class = tool_model.langchain_class

        if not langchain_class:
            logger.warning(f"Built-in tool {tool_model.name} has no langchain_class")
            return None

        if langchain_class not in BUILTIN_TOOL_REGISTRY:
            logger.warning(f"Unknown built-in tool class: {langchain_class}")
            return None

        try:
            # Create the tool using the factory
            tool = BUILTIN_TOOL_REGISTRY[langchain_class]()
            logger.debug(f"Created built-in tool: {tool_model.name}")
            return tool
        except Exception as e:
            logger.error(f"Failed to create built-in tool {tool_model.name}: {str(e)}")
            raise ToolWrapperError(f"Failed to create tool {tool_model.name}: {str(e)}")

    def _wrap_custom_tool(
        self,
        tool_model: Tool,
        config_override: Optional[Dict[str, Any]] = None
    ) -> Optional[BaseTool]:
        """
        Wrap a custom user-defined tool.

        Args:
            tool_model: Tool database model
            config_override: Optional configuration override

        Returns:
            LangChain tool instance
        """
        if not tool_model.function_code:
            logger.warning(f"Custom tool {tool_model.name} has no function code")
            return None

        # Create the custom tool wrapper
        wrapper = CustomToolWrapper(
            name=tool_model.name,
            description=tool_model.description,
            tool_id=tool_model.id,
            function_code=tool_model.function_code,
            input_schema_def=tool_model.input_schema
        )

        logger.debug(f"Created custom tool wrapper: {tool_model.name}")
        return wrapper

    @staticmethod
    def get_available_builtin_tools() -> List[str]:
        """
        Get list of available built-in tool class names.

        Returns:
            List of tool class names
        """
        return list(BUILTIN_TOOL_REGISTRY.keys())

    @staticmethod
    def is_builtin_tool_supported(langchain_class: str) -> bool:
        """
        Check if a built-in tool class is supported.

        Args:
            langchain_class: Tool class name

        Returns:
            True if supported
        """
        return langchain_class in BUILTIN_TOOL_REGISTRY


def load_agent_tools(
    db: Session,
    agent_id: int,
    user_id: int
) -> List[BaseTool]:
    """
    Convenience function to load tools for an agent.

    Args:
        db: Database session
        agent_id: Agent ID
        user_id: User ID

    Returns:
        List of LangChain-compatible tools
    """
    loader = ToolLoader(db)
    return loader.load_tools_for_agent(agent_id, user_id)


def load_tools_by_ids(
    db: Session,
    tool_ids: List[int],
    user_id: int
) -> List[BaseTool]:
    """
    Convenience function to load tools by IDs.

    Args:
        db: Database session
        tool_ids: List of tool IDs
        user_id: User ID

    Returns:
        List of LangChain-compatible tools
    """
    loader = ToolLoader(db)
    return loader.load_tools_by_ids(tool_ids, user_id)
