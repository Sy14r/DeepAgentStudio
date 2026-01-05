"""
Tool Wrapper Service for LangChain Integration.

This module wraps DeepAgentStudio tools as LangChain-compatible tools.

Supports:
- Built-in tools: Instantiate the appropriate LangChain tool class
- Custom tools: Create dynamic tools that execute user code via SandboxService
"""
from typing import Any, Dict, List, Optional, Type, Callable
from langchain.tools import BaseTool, StructuredTool, Tool as LangChainTool
from langchain_community.tools import DuckDuckGoSearchRun, WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_experimental.tools import PythonREPLTool
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
    "DuckDuckGoSearchRun": lambda: DuckDuckGoSearchRun(),
    "WikipediaQueryRun": lambda: WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper()),
    "Calculator": lambda: _create_calculator_tool(),
    "PythonREPL": lambda: PythonREPLTool(),
    "RequestsGet": lambda: _create_requests_tool(),
}


def _create_calculator_tool() -> BaseTool:
    """Create a simple calculator tool"""
    def calculate(expression: str) -> str:
        """Evaluate a mathematical expression"""
        try:
            # Only allow safe mathematical operations
            allowed_chars = set("0123456789+-*/.() ")
            if not all(c in allowed_chars for c in expression):
                return "Error: Only mathematical expressions are allowed"
            result = eval(expression)
            return str(result)
        except Exception as e:
            return f"Error: {str(e)}"

    return StructuredTool.from_function(
        func=calculate,
        name="Calculator",
        description="Calculate mathematical expressions. Input should be a valid math expression like '2 + 2' or '(3 * 4) / 2'"
    )


def _create_requests_tool() -> BaseTool:
    """Create a simple HTTP GET requests tool"""
    import httpx

    def make_request(url: str) -> str:
        """Make an HTTP GET request to a URL"""
        try:
            response = httpx.get(url, timeout=30, follow_redirects=True)
            return response.text[:5000]  # Limit response size
        except Exception as e:
            return f"Error: {str(e)}"

    return StructuredTool.from_function(
        func=make_request,
        name="HTTP Request",
        description="Make an HTTP GET request to a URL and return the response"
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
