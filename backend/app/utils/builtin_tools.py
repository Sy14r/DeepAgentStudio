"""
Built-in tool catalog for LangChain tools.

DeepAgentStudio provides two essential built-in tools:
1. Python Code Execution - Run Python code in a sandboxed environment
2. HTTP Requests - Make HTTP requests to external APIs
"""
from typing import List, Dict, Any
from ..models.tool import ToolCategory


# Python Code Execution implementation
PYTHON_CODE_EXECUTION_CODE = '''def python_code_execution(code: str) -> str:
    """
    Execute Python code and return the result.

    Args:
        code: Python code to execute

    Returns:
        Result of the code execution as a string
    """
    import io
    import json
    from contextlib import redirect_stdout, redirect_stderr

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
        'base64': __import__('base64'),
        'hashlib': __import__('hashlib'),
        'statistics': __import__('statistics'),
    }

    # Create execution environment with safe builtins
    exec_globals = {
        '__builtins__': {
            'abs': abs, 'all': all, 'any': any, 'bool': bool, 'dict': dict,
            'enumerate': enumerate, 'filter': filter, 'float': float,
            'format': format, 'frozenset': frozenset, 'getattr': getattr,
            'hasattr': hasattr, 'hash': hash, 'int': int, 'isinstance': isinstance,
            'issubclass': issubclass, 'iter': iter, 'len': len, 'list': list,
            'map': map, 'max': max, 'min': min, 'next': next, 'ord': ord,
            'pow': pow, 'print': print, 'range': range, 'repr': repr,
            'reversed': reversed, 'round': round, 'set': set, 'slice': slice,
            'sorted': sorted, 'str': str, 'sum': sum, 'tuple': tuple,
            'type': type, 'zip': zip, 'True': True, 'False': False, 'None': None,
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

    # Capture stdout/stderr
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(code, exec_globals, exec_locals)

        stdout_output = stdout_capture.getvalue()
        stderr_output = stderr_capture.getvalue()

        # Check for 'result' variable
        if 'result' in exec_locals:
            result_value = exec_locals['result']
            if isinstance(result_value, (dict, list)):
                return json.dumps(result_value, indent=2, default=str)
            return str(result_value)

        # Return stdout if available
        if stdout_output:
            return stdout_output.strip()

        if stderr_output:
            return f"stderr: {stderr_output.strip()}"

        # Return last defined variable
        user_vars = {k: v for k, v in exec_locals.items()
                    if not k.startswith('_') and k not in allowed_modules}
        if user_vars:
            last_var = list(user_vars.values())[-1]
            if isinstance(last_var, (dict, list)):
                return json.dumps(last_var, indent=2, default=str)
            return str(last_var)

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
'''

# HTTP Request implementation
HTTP_REQUEST_CODE = '''def http_request(request_config: str) -> str:
    """
    Make HTTP requests to external APIs.

    Args:
        request_config: JSON string with url, method, headers, data, params, timeout

    Returns:
        JSON response with status_code, headers, and body
    """
    import json
    import httpx

    try:
        # Parse request configuration
        if isinstance(request_config, str):
            try:
                config = json.loads(request_config)
            except json.JSONDecodeError:
                config = {"url": request_config}
        else:
            config = request_config

        url = config.get("url")
        if not url:
            return "Error: URL is required"

        method = config.get("method", "GET").upper()
        headers = config.get("headers", {})
        data = config.get("data")
        params = config.get("params")
        timeout = config.get("timeout", 30)

        valid_methods = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
        if method not in valid_methods:
            return f"Error: Invalid method '{method}'. Supported: {', '.join(valid_methods)}"

        request_kwargs = {"timeout": timeout, "follow_redirects": True}

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

        result = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
        }

        try:
            result["body"] = response.json()
        except (json.JSONDecodeError, ValueError):
            body_text = response.text
            if len(body_text) > 10000:
                body_text = body_text[:10000] + "\\n... (truncated)"
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
'''


# Built-in tool definitions
BUILTIN_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "Python Code Execution",
        "description": """Execute Python code and return the result.

Capabilities:
- Run arbitrary Python code with common libraries (json, datetime, math, re, collections, itertools, functools)
- Process data, perform calculations, parse text
- Return results as strings, numbers, or JSON

Usage:
- Input should be valid Python code
- Use 'result' variable or 'print()' for output
- For complex output, use json.dumps()

Examples:
- "2 + 2" returns "4"
- "import math; result = math.sqrt(16)" returns "4.0"
- "data = {'a': 1, 'b': 2}; result = json.dumps(data)" returns '{"a": 1, "b": 2}'
""",
        "category": ToolCategory.PYTHON,
        "tags": ["python", "code", "execution", "programming", "calculation"],
        "langchain_class": "PythonCodeExecution",
        "required_config": {},
        "function_code": PYTHON_CODE_EXECUTION_CODE,
    },
    {
        "name": "HTTP Request",
        "description": """Make HTTP requests to external URLs and APIs.

Capabilities:
- Supports GET, POST, PUT, PATCH, DELETE methods
- Send JSON data in request body
- Set custom headers
- Automatic JSON response parsing
- Timeout and error handling

Usage:
- Input should be a JSON object with: url (required), method (default: GET), headers, data
- Returns response body (JSON if applicable, otherwise text)

Examples:
- '{"url": "https://api.example.com/data"}' - Simple GET request
- '{"url": "https://api.example.com/items", "method": "POST", "data": {"name": "test"}}' - POST with JSON body
- '{"url": "https://api.example.com", "headers": {"Authorization": "Bearer token"}}' - GET with headers
""",
        "category": ToolCategory.API,
        "tags": ["http", "api", "requests", "web", "rest"],
        "langchain_class": "HTTPRequest",
        "required_config": {},
        "function_code": HTTP_REQUEST_CODE,
    },
]


def get_builtin_tools() -> List[Dict[str, Any]]:
    """
    Get list of built-in tool definitions.

    Returns:
        List of tool definition dictionaries
    """
    return BUILTIN_TOOLS


def seed_builtin_tools(db):
    """
    Seed built-in tools into the database.

    Args:
        db: Database session
    """
    from ..models.tool import Tool, ToolType

    for tool_def in BUILTIN_TOOLS:
        # Check if tool already exists
        existing = db.query(Tool).filter(Tool.name == tool_def["name"]).first()
        if existing:
            # Update function_code if it's missing or different
            if existing.function_code != tool_def.get("function_code"):
                existing.function_code = tool_def.get("function_code")
                existing.description = tool_def["description"]
            continue

        # Create new built-in tool
        tool = Tool(
            name=tool_def["name"],
            description=tool_def["description"],
            category=tool_def["category"],
            tags=tool_def["tags"],
            tool_type=ToolType.BUILTIN,
            langchain_class=tool_def["langchain_class"],
            required_config=tool_def["required_config"],
            function_code=tool_def.get("function_code"),
            user_id=None,  # Built-in tools have no owner
            is_active=True
        )
        db.add(tool)

    db.commit()
