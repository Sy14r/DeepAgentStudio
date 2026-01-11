"""
Sandbox Service for Tool Execution.

This service provides an abstraction layer for executing tool code.
Currently implements a no-op passthrough, but designed for easy
replacement with actual sandboxing (Docker, RestrictedPython, etc.)
in the future.

╔══════════════════════════════════════════════════════════════════════════════╗
║                           SECURITY WARNING                                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Custom tool code is executed WITHOUT sandboxing by default.                  ║
║                                                                              ║
║  This means custom Python tools have FULL ACCESS to:                         ║
║    - File system (read/write any files)                                      ║
║    - Network (make HTTP requests, open sockets)                              ║
║    - Environment variables (including secrets)                               ║
║    - System resources                                                        ║
║                                                                              ║
║  ONLY deploy DeepAgentStudio with untrusted users if you:                    ║
║    1. Disable custom tool creation (use built-in tools only)                 ║
║    2. Implement proper sandboxing (Docker, gVisor, etc.)                     ║
║    3. Run in a fully isolated environment                                    ║
║                                                                              ║
║  For self-hosted deployments with trusted users, this is acceptable.         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass
import logging
import traceback
import sys
from io import StringIO

logger = logging.getLogger(__name__)


@dataclass
class SandboxResult:
    """Result of sandbox execution"""
    success: bool
    output: Any
    error: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    execution_time_ms: Optional[int] = None


class BaseSandbox(ABC):
    """
    Abstract base class for sandbox implementations.

    Implement this interface to add new sandboxing strategies:
    - DockerSandbox: Execute in isolated Docker container
    - RestrictedPythonSandbox: Use RestrictedPython for safe exec
    - GVisorSandbox: Use gVisor for kernel-level isolation
    """

    @abstractmethod
    def execute(
        self,
        code: str,
        inputs: Dict[str, Any],
        timeout_seconds: int = 30
    ) -> SandboxResult:
        """
        Execute code in sandbox.

        Args:
            code: Python code to execute
            inputs: Dictionary of input variables available to the code
            timeout_seconds: Maximum execution time

        Returns:
            SandboxResult with output or error
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this sandbox implementation is available"""
        pass


class NoOpSandbox(BaseSandbox):
    """
    No-op sandbox that executes code directly.

    ⚠️  SECURITY WARNING: This provides NO security isolation.  ⚠️

    Code executed through this sandbox has:
    - Full file system access
    - Full network access
    - Access to all environment variables
    - Access to import any Python module
    - No memory or CPU limits
    - No timeout enforcement at the sandbox level

    Only use in:
    - Development environments
    - Self-hosted deployments with fully trusted users
    - Deployments where custom tools are disabled

    For untrusted code, implement DockerSandbox or similar.
    """

    _warning_logged = False

    def execute(
        self,
        code: str,
        inputs: Dict[str, Any],
        timeout_seconds: int = 30
    ) -> SandboxResult:
        """
        Execute code directly (no sandboxing).

        Creates a local namespace with inputs and executes the code.
        The result should be stored in a 'result' variable.
        """
        # Log warning on first execution
        if not NoOpSandbox._warning_logged:
            logger.warning(
                "⚠️  NoOpSandbox: Custom tool code is executing WITHOUT sandboxing. "
                "This is only safe for trusted users. See SECURITY.md for details."
            )
            NoOpSandbox._warning_logged = True

        import time
        start_time = time.time()

        # Capture stdout/stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()

        try:
            # Create execution namespace with inputs
            namespace = {
                **inputs,
                "__builtins__": __builtins__,
            }

            # Execute the code
            exec(code, namespace)

            # Get the result (code should set 'result' variable)
            output = namespace.get("result", None)

            # Capture output streams
            stdout_output = sys.stdout.getvalue()
            stderr_output = sys.stderr.getvalue()

            execution_time = int((time.time() - start_time) * 1000)

            return SandboxResult(
                success=True,
                output=output,
                stdout=stdout_output if stdout_output else None,
                stderr=stderr_output if stderr_output else None,
                execution_time_ms=execution_time
            )

        except Exception as e:
            stderr_output = sys.stderr.getvalue()
            execution_time = int((time.time() - start_time) * 1000)

            logger.error(f"Tool execution error: {str(e)}")

            return SandboxResult(
                success=False,
                output=None,
                error=f"{type(e).__name__}: {str(e)}",
                stderr=stderr_output if stderr_output else traceback.format_exc(),
                execution_time_ms=execution_time
            )

        finally:
            # Restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def is_available(self) -> bool:
        """NoOp sandbox is always available"""
        return True


class SandboxService:
    """
    Service for managing tool code execution.

    This service provides a unified interface for executing tool code
    through various sandbox implementations. It handles:
    - Sandbox selection based on availability/configuration
    - Execution with proper error handling
    - Result normalization

    Usage:
        sandbox = SandboxService()
        result = sandbox.execute_tool(
            code="result = x + y",
            inputs={"x": 1, "y": 2}
        )
        if result.success:
            print(f"Result: {result.output}")  # 3
        else:
            print(f"Error: {result.error}")
    """

    def __init__(self, sandbox_type: str = "noop"):
        """
        Initialize sandbox service.

        Args:
            sandbox_type: Type of sandbox to use:
                - "noop": Direct execution (no sandboxing) - DEFAULT
                - "docker": Docker container isolation (future)
                - "restricted": RestrictedPython (future)
        """
        self.sandbox_type = sandbox_type
        self.sandbox = self._create_sandbox(sandbox_type)

    def _create_sandbox(self, sandbox_type: str) -> BaseSandbox:
        """Create sandbox instance based on type"""
        if sandbox_type == "noop":
            return NoOpSandbox()
        # Future implementations:
        # elif sandbox_type == "docker":
        #     return DockerSandbox()
        # elif sandbox_type == "restricted":
        #     return RestrictedPythonSandbox()
        else:
            logger.warning(
                f"Unknown sandbox type '{sandbox_type}', falling back to noop"
            )
            return NoOpSandbox()

    def execute_tool(
        self,
        code: str,
        inputs: Dict[str, Any],
        timeout_seconds: int = 30
    ) -> SandboxResult:
        """
        Execute tool code in sandbox.

        Args:
            code: Python code to execute. Should set 'result' variable.
            inputs: Dictionary of input variables
            timeout_seconds: Maximum execution time

        Returns:
            SandboxResult with output or error details

        Example:
            # Tool code that adds two numbers
            code = '''
            result = a + b
            '''
            result = sandbox.execute_tool(code, {"a": 5, "b": 3})
            # result.output == 8
        """
        if not code or not code.strip():
            return SandboxResult(
                success=False,
                output=None,
                error="No code provided"
            )

        return self.sandbox.execute(code, inputs, timeout_seconds)

    def execute_function(
        self,
        func_code: str,
        func_name: str,
        args: Dict[str, Any],
        timeout_seconds: int = 30
    ) -> SandboxResult:
        """
        Execute a function defined in code.

        Args:
            func_code: Python code containing function definition
            func_name: Name of function to call
            args: Arguments to pass to function
            timeout_seconds: Maximum execution time

        Returns:
            SandboxResult with function return value

        Example:
            code = '''
            def add(a, b):
                return a + b
            '''
            result = sandbox.execute_function(code, "add", {"a": 5, "b": 3})
            # result.output == 8
        """
        # Wrap the function call
        wrapper_code = f"""
{func_code}

result = {func_name}(**__args__)
"""
        inputs = {"__args__": args}
        return self.sandbox.execute(wrapper_code, inputs, timeout_seconds)

    def validate_code(self, code: str) -> tuple[bool, Optional[str]]:
        """
        Validate code syntax without executing.

        Args:
            code: Python code to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            compile(code, "<string>", "exec")
            return True, None
        except SyntaxError as e:
            return False, f"Syntax error at line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, str(e)

    def is_sandbox_available(self) -> bool:
        """Check if the configured sandbox is available"""
        return self.sandbox.is_available()

    def get_sandbox_info(self) -> Dict[str, Any]:
        """Get information about current sandbox configuration"""
        return {
            "type": self.sandbox_type,
            "available": self.is_sandbox_available(),
            "class": self.sandbox.__class__.__name__,
            "security_level": "none" if self.sandbox_type == "noop" else "isolated"
        }


# Singleton instance for easy access
_sandbox_service: Optional[SandboxService] = None


def get_sandbox_service() -> SandboxService:
    """
    Get the singleton sandbox service instance.

    Returns:
        SandboxService instance
    """
    global _sandbox_service
    if _sandbox_service is None:
        _sandbox_service = SandboxService(sandbox_type="noop")
    return _sandbox_service


def execute_tool_code(
    code: str,
    inputs: Dict[str, Any],
    timeout_seconds: int = 30
) -> SandboxResult:
    """
    Convenience function to execute tool code.

    Args:
        code: Python code to execute
        inputs: Input variables
        timeout_seconds: Timeout

    Returns:
        SandboxResult
    """
    service = get_sandbox_service()
    return service.execute_tool(code, inputs, timeout_seconds)
