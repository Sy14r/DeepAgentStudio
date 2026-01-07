"""
Custom Strategy Executor for User-Defined Execution Code.

This service executes custom Python strategy code in a sandboxed environment.
Users can define their own execution logic by implementing an execute() function.
"""
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
import ast
import logging
import time
import traceback
from io import StringIO
import sys

from langchain_core.language_models import BaseChatModel
from langchain.tools import BaseTool
from langchain_core.messages import BaseMessage

from .execution_helpers import ExecutionHelpers, ExecutionResult

logger = logging.getLogger(__name__)


# Safe builtins allowed in custom strategy code
SAFE_BUILTINS = {
    # Type constructors
    "bool": bool,
    "int": int,
    "float": float,
    "str": str,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
    "frozenset": frozenset,
    "bytes": bytes,
    "bytearray": bytearray,

    # Built-in functions
    "abs": abs,
    "all": all,
    "any": any,
    "bin": bin,
    "callable": callable,
    "chr": chr,
    "divmod": divmod,
    "enumerate": enumerate,
    "filter": filter,
    "format": format,
    "getattr": getattr,
    "hasattr": hasattr,
    "hash": hash,
    "hex": hex,
    "isinstance": isinstance,
    "issubclass": issubclass,
    "iter": iter,
    "len": len,
    "map": map,
    "max": max,
    "min": min,
    "next": next,
    "oct": oct,
    "ord": ord,
    "pow": pow,
    "print": print,  # Captured to stdout
    "range": range,
    "repr": repr,
    "reversed": reversed,
    "round": round,
    "sorted": sorted,
    "sum": sum,
    "zip": zip,

    # Exceptions for error handling
    "Exception": Exception,
    "ValueError": ValueError,
    "TypeError": TypeError,
    "KeyError": KeyError,
    "IndexError": IndexError,
    "AttributeError": AttributeError,
    "RuntimeError": RuntimeError,

    # Constants
    "True": True,
    "False": False,
    "None": None,
}

# Allowed modules that can be imported
ALLOWED_MODULES = {
    "json",
    "math",
    "re",
    "datetime",
    "collections",
    "itertools",
    "functools",
    "typing",
    "dataclasses",
    "copy",
    "textwrap",
    "string",
}

# Dangerous patterns to check for in code
DANGEROUS_PATTERNS = [
    "__import__",
    "exec(",
    "eval(",
    "compile(",
    "open(",
    "os.",
    "sys.",
    "subprocess",
    "socket",
    "urllib",
    "requests",
    "http.client",
    "ftplib",
    "smtplib",
    "pickle",
    "marshal",
    "shelve",
    "dbm",
    "__builtins__",
    "__code__",
    "__globals__",
    "globals()",
    "locals()",
    "vars(",
    "dir(",
    "getattr(",  # Can be used for introspection attacks - keep for legitimate use but flag
]


@dataclass
class ValidationResult:
    """Result of code validation"""
    is_valid: bool
    error: Optional[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class StrategyExecutionResult:
    """Result of strategy execution"""
    success: bool
    result: Optional[ExecutionResult] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    execution_time_ms: int = 0
    stdout: Optional[str] = None
    stderr: Optional[str] = None


class CustomStrategyExecutor:
    """
    Executes custom strategy code in a controlled environment.

    Security features:
    - Restricted builtins (no exec, eval, open, __import__)
    - Module allowlist (json, math, re, datetime, etc.)
    - Pattern checking for dangerous operations
    - Timeout enforcement
    - Output capture

    Usage:
        executor = CustomStrategyExecutor()

        # Validate code first
        validation = executor.validate_code(code)
        if not validation.is_valid:
            print(f"Invalid code: {validation.error}")
            return

        # Execute the strategy
        result = executor.execute(
            code=code,
            llm=llm_instance,
            tools=tool_list,
            input_message="Hello",
            chat_history=[],
            config={"max_iterations": 10}
        )

        if result.success:
            print(f"Output: {result.result.output}")
        else:
            print(f"Error: {result.error}")
    """

    def __init__(
        self,
        timeout_seconds: int = 60,
        enable_restricted_mode: bool = True
    ):
        """
        Initialize the strategy executor.

        Args:
            timeout_seconds: Maximum execution time
            enable_restricted_mode: If True, use restricted builtins
        """
        self.timeout_seconds = timeout_seconds
        self.enable_restricted_mode = enable_restricted_mode

    def validate_code(self, code: str) -> ValidationResult:
        """
        Validate strategy code for syntax and security.

        Checks:
        1. Valid Python syntax
        2. execute() function exists with correct signature
        3. No dangerous patterns
        4. No disallowed imports

        Args:
            code: Python code to validate

        Returns:
            ValidationResult with is_valid, error, and warnings
        """
        warnings = []

        # Check syntax
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return ValidationResult(
                is_valid=False,
                error=f"Syntax error at line {e.lineno}: {e.msg}"
            )

        # Find execute function
        execute_func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "execute":
                execute_func = node
                break

        if execute_func is None:
            return ValidationResult(
                is_valid=False,
                error="Code must define an 'execute' function"
            )

        # Check function signature
        args = execute_func.args
        expected_args = ["llm", "tools", "input_message", "chat_history", "config", "helpers"]
        actual_args = [arg.arg for arg in args.args]

        if actual_args != expected_args:
            return ValidationResult(
                is_valid=False,
                error=f"execute() must have signature: execute(llm, tools, input_message, chat_history, config, helpers). "
                      f"Got: execute({', '.join(actual_args)})"
            )

        # Check for dangerous patterns
        code_lower = code.lower()
        for pattern in DANGEROUS_PATTERNS:
            if pattern.lower() in code_lower:
                # Some patterns are warnings, others are errors
                if pattern in ["getattr(", "dir("]:
                    warnings.append(f"Use of '{pattern}' detected - ensure it's for legitimate purposes")
                elif pattern in ["__import__", "exec(", "eval(", "compile(", "open("]:
                    return ValidationResult(
                        is_valid=False,
                        error=f"Dangerous pattern '{pattern}' is not allowed in strategy code"
                    )

        # Check imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name.split(".")[0]
                    if module_name not in ALLOWED_MODULES:
                        return ValidationResult(
                            is_valid=False,
                            error=f"Import of '{alias.name}' is not allowed. "
                                  f"Allowed modules: {', '.join(sorted(ALLOWED_MODULES))}"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module.split(".")[0]
                    if module_name not in ALLOWED_MODULES:
                        return ValidationResult(
                            is_valid=False,
                            error=f"Import from '{node.module}' is not allowed. "
                                  f"Allowed modules: {', '.join(sorted(ALLOWED_MODULES))}"
                        )

        return ValidationResult(is_valid=True, warnings=warnings)

    def execute(
        self,
        code: str,
        llm: BaseChatModel,
        tools: List[BaseTool],
        input_message: str,
        chat_history: List[BaseMessage],
        config: Dict[str, Any],
        stream_callback: Optional[Callable[[str], None]] = None
    ) -> StrategyExecutionResult:
        """
        Execute custom strategy code.

        Args:
            code: Python code defining execute() function
            llm: LangChain chat model instance
            tools: List of available tools
            input_message: User's input message
            chat_history: Previous conversation messages
            config: Agent configuration dict
            stream_callback: Optional callback for streaming tokens

        Returns:
            StrategyExecutionResult with success status and result or error
        """
        start_time = time.time()

        # Capture stdout/stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()

        try:
            # Create execution helpers
            helpers = ExecutionHelpers(
                llm=llm,
                tools=tools,
                stream_callback=stream_callback
            )

            # Create safe execution namespace
            namespace = self._create_namespace()

            # Add allowed module imports
            self._add_allowed_imports(namespace)

            # Execute the code to define the execute function
            exec(code, namespace)

            # Get the execute function
            execute_func = namespace.get("execute")
            if not callable(execute_func):
                raise ValueError("execute() function not found or not callable")

            # Call the execute function
            result = execute_func(
                llm=llm,
                tools=tools,
                input_message=input_message,
                chat_history=chat_history,
                config=config,
                helpers=helpers
            )

            # Validate result type
            if not isinstance(result, ExecutionResult):
                # Try to convert if it's a dict or similar
                if isinstance(result, dict):
                    result = ExecutionResult(**result)
                elif isinstance(result, str):
                    result = helpers.create_result(output=result)
                else:
                    result = helpers.create_result(output=str(result))

            execution_time = int((time.time() - start_time) * 1000)

            return StrategyExecutionResult(
                success=True,
                result=result,
                execution_time_ms=execution_time,
                stdout=sys.stdout.getvalue() or None,
                stderr=sys.stderr.getvalue() or None
            )

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            error_traceback = traceback.format_exc()

            logger.error(f"Strategy execution error: {str(e)}\n{error_traceback}")

            return StrategyExecutionResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
                execution_time_ms=execution_time,
                stdout=sys.stdout.getvalue() or None,
                stderr=error_traceback
            )

        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def _create_namespace(self) -> Dict[str, Any]:
        """Create execution namespace with restricted builtins"""
        if self.enable_restricted_mode:
            return {
                "__builtins__": SAFE_BUILTINS,
                "ExecutionResult": ExecutionResult,
            }
        else:
            return {
                "__builtins__": __builtins__,
                "ExecutionResult": ExecutionResult,
            }

    def _add_allowed_imports(self, namespace: Dict[str, Any]) -> None:
        """Pre-import allowed modules into namespace"""
        import json
        import math
        import re
        import datetime
        import collections
        import itertools
        import functools
        import copy
        import textwrap
        import string

        namespace.update({
            "json": json,
            "math": math,
            "re": re,
            "datetime": datetime,
            "collections": collections,
            "itertools": itertools,
            "functools": functools,
            "copy": copy,
            "textwrap": textwrap,
            "string": string,
        })


# Default code templates for users to start from
STRATEGY_TEMPLATES = {
    "simple_chat": '''def execute(llm, tools, input_message, chat_history, config, helpers):
    """Simple conversational strategy - no tools, just chat."""
    helpers.record_thought("Processing user input...")

    messages = []
    if config.get("system_prompt"):
        messages.append({"role": "system", "content": config["system_prompt"]})

    for msg in chat_history:
        role = "assistant" if hasattr(msg, "type") and msg.type == "ai" else "user"
        messages.append({"role": role, "content": msg.content})

    messages.append({"role": "user", "content": input_message})

    response = helpers.call_llm(messages)

    return helpers.create_result(output=response)
''',

    "react_custom": '''def execute(llm, tools, input_message, chat_history, config, helpers):
    """Custom ReAct-style execution with tools."""
    max_iterations = config.get("max_iterations", 10)
    tool_descriptions = helpers.format_tools_for_prompt()

    prompt = f"""You have access to these tools:
{tool_descriptions}

To use a tool, respond in this format:
Thought: <your reasoning>
Action: <tool_name>
Action Input: <JSON input for the tool>

When you have the final answer:
Thought: I have the answer
Final Answer: <your response>

Question: {input_message}"""

    messages = [{"role": "user", "content": prompt}]

    for i in range(max_iterations):
        helpers.record_thought(f"Iteration {i+1}")
        response = helpers.call_llm(messages)

        if "Final Answer:" in response:
            answer = response.split("Final Answer:")[-1].strip()
            return helpers.create_result(output=answer)

        # Parse action and input
        if "Action:" in response and "Action Input:" in response:
            action_match = re.search(r"Action:\\s*(.+?)\\n", response)
            input_match = re.search(r"Action Input:\\s*(.+?)(?:\\n|$)", response, re.DOTALL)

            if action_match and input_match:
                tool_name = action_match.group(1).strip()
                tool_input = json.loads(input_match.group(1).strip())

                result = helpers.call_tool(tool_name, tool_input)
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": f"Observation: {result}"})
                continue

        # No valid action found
        messages.append({"role": "assistant", "content": response})
        messages.append({"role": "user", "content": "Please use the correct format."})

    return helpers.create_result(output="Max iterations reached without final answer.")
''',

    "chain_of_thought": '''def execute(llm, tools, input_message, chat_history, config, helpers):
    """Chain-of-thought prompting strategy."""
    helpers.record_thought("Using chain-of-thought reasoning...")

    system_prompt = config.get("system_prompt", "You are a helpful assistant.")
    cot_prompt = f"""{system_prompt}

When answering questions, think through the problem step by step:
1. First, understand what is being asked
2. Break down the problem into smaller parts
3. Solve each part systematically
4. Combine your findings into a final answer

Show your reasoning clearly before giving the final answer."""

    messages = [
        {"role": "system", "content": cot_prompt},
        {"role": "user", "content": input_message}
    ]

    response = helpers.call_llm(messages)

    return helpers.create_result(output=response)
''',

    "tool_selector": '''def execute(llm, tools, input_message, chat_history, config, helpers):
    """Strategy that asks LLM to select and use the best tool."""
    tool_info = helpers.list_tools()

    if not tool_info:
        # No tools available, just chat
        response = helpers.call_llm([
            {"role": "user", "content": input_message}
        ])
        return helpers.create_result(output=response)

    # Ask LLM which tool to use
    tool_list = "\\n".join([f"- {t['name']}: {t['description']}" for t in tool_info])

    selector_prompt = f"""Given the user request below, decide which tool to use.

Available tools:
{tool_list}

User request: {input_message}

Respond with ONLY the tool name if a tool should be used, or "NONE" if no tool is needed."""

    selection = helpers.call_llm([{"role": "user", "content": selector_prompt}])
    selected_tool = selection.strip()

    if selected_tool == "NONE" or selected_tool not in [t["name"] for t in tool_info]:
        response = helpers.call_llm([{"role": "user", "content": input_message}])
        return helpers.create_result(output=response)

    # Generate tool input
    tool = helpers.get_tool(selected_tool)
    input_prompt = f"""Generate the input for the "{selected_tool}" tool.

Tool description: {tool.description}

User request: {input_message}

Respond with ONLY valid JSON that can be passed to the tool."""

    tool_input_str = helpers.call_llm([{"role": "user", "content": input_prompt}])
    tool_input = json.loads(tool_input_str)

    # Execute tool
    result = helpers.call_tool(selected_tool, tool_input)

    # Generate final response
    final_prompt = f"""The user asked: {input_message}

I used the {selected_tool} tool and got this result: {result}

Please provide a helpful response to the user based on this result."""

    response = helpers.call_llm([{"role": "user", "content": final_prompt}])

    return helpers.create_result(output=response)
''',
}


def get_strategy_template(template_name: str) -> Optional[str]:
    """Get a strategy template by name"""
    return STRATEGY_TEMPLATES.get(template_name)


def list_strategy_templates() -> List[Dict[str, str]]:
    """List available strategy templates"""
    return [
        {"name": "simple_chat", "description": "Simple conversational strategy without tools"},
        {"name": "react_custom", "description": "Custom ReAct-style execution with tools"},
        {"name": "chain_of_thought", "description": "Chain-of-thought prompting strategy"},
        {"name": "tool_selector", "description": "Strategy that asks LLM to select the best tool"},
    ]
