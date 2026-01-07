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
    # ============= WORKSPACE TOOLS =============
    # These tools are created dynamically with session context
    # and provide file, task, and scratchpad operations within
    # sandboxed workspaces.
    {
        "name": "File Read",
        "description": """Read contents of a file from the session workspace.

Capabilities:
- Read any text file in the workspace
- Optionally read specific line ranges for large files
- Supports all text-based formats

Usage:
- path (required): Relative path to file (e.g., "report.md", "data/results.json")
- start_line (optional): Starting line number (1-indexed)
- end_line (optional): Ending line number (inclusive)

Examples:
- file_read(path="notes.md") - Read entire file
- file_read(path="data.csv", start_line=1, end_line=50) - Read first 50 lines
""",
        "category": ToolCategory.FILESYSTEM,
        "tags": ["file", "read", "workspace", "filesystem"],
        "langchain_class": "WorkspaceFileRead",
        "required_config": {},
        "function_code": '''def file_read(path: str, start_line: int = None, end_line: int = None) -> str:
    """
    Read contents of a file from the workspace.

    Args:
        path: Relative path to file within workspace
        start_line: Starting line number (1-indexed, optional)
        end_line: Ending line number (inclusive, optional)

    Returns:
        File contents as string
    """
    # This tool operates within a sandboxed session workspace
    # The workspace is automatically created for each agent session

    from pathlib import Path

    workspace_path = Path(WORKSPACE_BASE_PATH) / str(session_id)
    file_path = workspace_path / path

    # Security: Ensure path stays within workspace
    if not file_path.resolve().is_relative_to(workspace_path.resolve()):
        return "Error: Path must be within workspace"

    if not file_path.exists():
        return f"Error: File not found: {path}"

    if not file_path.is_file():
        return f"Error: Not a file: {path}"

    content = file_path.read_text(encoding="utf-8")

    # Handle line range if specified
    if start_line is not None or end_line is not None:
        lines = content.splitlines(keepends=True)
        start_idx = (start_line - 1) if start_line else 0
        end_idx = end_line if end_line else len(lines)
        content = "".join(lines[start_idx:end_idx])

    return content
''',
    },
    {
        "name": "File Write",
        "description": """Write content to a file in the session workspace (creates or overwrites).

Capabilities:
- Create new files or overwrite existing files
- Automatically create parent directories
- Supports all text-based formats

Usage:
- path (required): Relative path for the file (e.g., "reports/summary.md")
- content (required): Content to write to the file
- create_dirs (optional): Create parent directories if needed (default: true)

Examples:
- file_write(path="report.md", content="# Report\\n\\nFindings...")
- file_write(path="data/output.json", content='{"result": 42}')
""",
        "category": ToolCategory.FILESYSTEM,
        "tags": ["file", "write", "workspace", "filesystem"],
        "langchain_class": "WorkspaceFileWrite",
        "required_config": {},
        "function_code": '''def file_write(path: str, content: str, create_dirs: bool = True) -> str:
    """
    Write content to a file in the workspace.

    Args:
        path: Relative path for the file
        content: Content to write
        create_dirs: Create parent directories if needed (default: True)

    Returns:
        Confirmation message with file size
    """
    from pathlib import Path

    workspace_path = Path(WORKSPACE_BASE_PATH) / str(session_id)
    file_path = workspace_path / path

    # Security: Ensure path stays within workspace
    if not file_path.resolve().is_relative_to(workspace_path.resolve()):
        return "Error: Path must be within workspace"

    # Create parent directories if requested
    if create_dirs:
        file_path.parent.mkdir(parents=True, exist_ok=True)
    elif not file_path.parent.exists():
        return f"Error: Parent directory does not exist: {file_path.parent}"

    # Write content
    file_path.write_text(content, encoding="utf-8")
    size_bytes = file_path.stat().st_size

    return f"Successfully wrote {size_bytes} bytes to {path}"
''',
    },
    {
        "name": "File Edit",
        "description": """Edit a file using targeted string replacement.

Capabilities:
- Find and replace exact strings in files
- Optionally replace all occurrences
- Precise, targeted edits without rewriting entire file

Usage:
- path (required): Relative path to file
- old_string (required): Exact string to find and replace
- new_string (required): Replacement string
- replace_all (optional): Replace all occurrences (default: false)

Examples:
- file_edit(path="config.json", old_string='"debug": false', new_string='"debug": true')
- file_edit(path="text.md", old_string="TODO", new_string="DONE", replace_all=true)
""",
        "category": ToolCategory.FILESYSTEM,
        "tags": ["file", "edit", "replace", "workspace", "filesystem"],
        "langchain_class": "WorkspaceFileEdit",
        "required_config": {},
        "function_code": '''def file_edit(path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
    """
    Edit a file using string replacement.

    Args:
        path: Relative path to file
        old_string: Exact string to find and replace
        new_string: Replacement string
        replace_all: Replace all occurrences (default: False)

    Returns:
        Confirmation with number of replacements
    """
    from pathlib import Path

    workspace_path = Path(WORKSPACE_BASE_PATH) / str(session_id)
    file_path = workspace_path / path

    # Security: Ensure path stays within workspace
    if not file_path.resolve().is_relative_to(workspace_path.resolve()):
        return "Error: Path must be within workspace"

    if not file_path.exists():
        return f"Error: File not found: {path}"

    content = file_path.read_text(encoding="utf-8")

    # Check if old_string exists
    count = content.count(old_string)
    if count == 0:
        return f"Error: String not found in file: {old_string[:50]}..."

    # Replace
    if replace_all:
        new_content = content.replace(old_string, new_string)
        replacements = count
    else:
        if count > 1:
            return f"Error: Multiple matches ({count}) found. Use replace_all=true"
        new_content = content.replace(old_string, new_string, 1)
        replacements = 1

    file_path.write_text(new_content, encoding="utf-8")
    return f"Successfully replaced {replacements} occurrence(s) in {path}"
''',
    },
    {
        "name": "File List",
        "description": """List files in workspace matching a glob pattern.

Capabilities:
- Find files using glob patterns
- Get file metadata (size, modified date)
- Optionally include hidden files

Usage:
- pattern (optional): Glob pattern (default: "*"). Examples: "*.md", "**/*.py", "data/*"
- include_hidden (optional): Include hidden files (default: false)

Examples:
- file_list(pattern="**/*.md") - Find all markdown files
- file_list(pattern="src/**/*.py") - Find Python files in src
- file_list() - List all files in workspace root
""",
        "category": ToolCategory.FILESYSTEM,
        "tags": ["file", "list", "search", "workspace", "filesystem"],
        "langchain_class": "WorkspaceFileList",
        "required_config": {},
        "function_code": '''def file_list(pattern: str = "*", include_hidden: bool = False) -> str:
    """
    List files in workspace matching a pattern.

    Args:
        pattern: Glob pattern (e.g., "*.md", "**/*.py")
        include_hidden: Include hidden files (default: False)

    Returns:
        JSON list of files with path, size, and modified date
    """
    import json
    from pathlib import Path
    from datetime import datetime

    workspace_path = Path(WORKSPACE_BASE_PATH) / str(session_id)

    if not workspace_path.exists():
        return json.dumps({"files": [], "count": 0})

    files = []
    for file_path in workspace_path.glob(pattern):
        if file_path.is_file():
            # Skip hidden files unless requested
            if not include_hidden and file_path.name.startswith("."):
                continue

            rel_path = file_path.relative_to(workspace_path)
            stat = file_path.stat()

            files.append({
                "path": str(rel_path),
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })

    # Sort by path
    files.sort(key=lambda f: f["path"])

    return json.dumps({"files": files, "count": len(files)}, indent=2)
''',
    },
    {
        "name": "File Search",
        "description": """Search file contents using regex pattern.

Capabilities:
- Search across multiple files using regex
- Filter files by glob pattern
- Show context around matches

Usage:
- pattern (required): Regex pattern to search for (e.g., "def \\w+\\(", "TODO")
- file_pattern (optional): Glob pattern for files to search (default: "**/*")
- max_results (optional): Maximum results (default: 50)
- context_lines (optional): Lines of context around matches (default: 2)

Examples:
- file_search(pattern="import.*pandas", file_pattern="**/*.py")
- file_search(pattern="TODO|FIXME", max_results=20)
""",
        "category": ToolCategory.FILESYSTEM,
        "tags": ["file", "search", "grep", "workspace", "filesystem"],
        "langchain_class": "WorkspaceFileSearch",
        "required_config": {},
        "function_code": '''def file_search(
    pattern: str,
    file_pattern: str = "**/*",
    max_results: int = 50,
    context_lines: int = 2
) -> str:
    """
    Search file contents using regex.

    Args:
        pattern: Regex pattern to search for
        file_pattern: Glob pattern for files to search
        max_results: Maximum results to return
        context_lines: Lines of context around matches

    Returns:
        JSON list of matches with file, line number, and context
    """
    import re
    import json
    from pathlib import Path

    workspace_path = Path(WORKSPACE_BASE_PATH) / str(session_id)

    if not workspace_path.exists():
        return json.dumps({"matches": [], "count": 0})

    try:
        regex = re.compile(pattern)
    except re.error as e:
        return f"Error: Invalid regex pattern: {e}"

    matches = []
    for file_path in workspace_path.glob(file_pattern):
        if not file_path.is_file():
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        lines = content.splitlines()
        rel_path = str(file_path.relative_to(workspace_path))

        for i, line in enumerate(lines):
            if regex.search(line):
                # Get context
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                context = lines[start:end]

                matches.append({
                    "file": rel_path,
                    "line_number": i + 1,
                    "match": line.strip(),
                    "context": context
                })

                if len(matches) >= max_results:
                    break

        if len(matches) >= max_results:
            break

    return json.dumps({"matches": matches, "count": len(matches)}, indent=2)
''',
    },
    {
        "name": "Task Manager",
        "description": """Manage a persistent task list for tracking progress on complex tasks.

Capabilities:
- Create, update, and track tasks
- Mark tasks as pending, in_progress, completed, or blocked
- Add notes to tasks
- Tasks persist across conversation turns

Actions:
- "list": Show all tasks
- "add": Create a new task (requires title, optional description)
- "update": Update task status/notes (requires task_id)
- "complete": Mark task as completed (requires task_id, optional notes)
- "remove": Delete a task (requires task_id)

Status values: pending, in_progress, completed, blocked

Examples:
- task_manager(action="add", title="Research Python frameworks")
- task_manager(action="update", task_id=1, status="in_progress")
- task_manager(action="complete", task_id=1, notes="Completed research, FastAPI recommended")
- task_manager(action="list")
""",
        "category": ToolCategory.OTHER,
        "tags": ["task", "todo", "planning", "workspace", "management"],
        "langchain_class": "WorkspaceTaskManager",
        "required_config": {},
        "function_code": '''def task_manager(
    action: str,
    task_id: int = None,
    title: str = None,
    description: str = None,
    status: str = None,
    notes: str = None
) -> str:
    """
    Manage a task list for tracking progress.

    Args:
        action: One of "list", "add", "update", "complete", "remove"
        task_id: Task ID (for update/complete/remove)
        title: Task title (for add)
        description: Task description (for add/update)
        status: pending, in_progress, completed, blocked (for update)
        notes: Notes to append (for update/complete)

    Returns:
        Task list or confirmation message
    """
    import json
    from datetime import datetime

    # Tasks are stored in database (SessionTask model) and synced to workspace
    # This is a simplified representation of the actual implementation

    if action == "list":
        # Query tasks from database for this session
        tasks = db.query(SessionTask).filter(
            SessionTask.session_id == session_id
        ).order_by(SessionTask.task_number).all()

        return json.dumps({
            "tasks": [
                {
                    "id": t.task_number,
                    "title": t.title,
                    "description": t.description,
                    "status": t.status.value,
                    "notes": t.notes,
                    "created_at": t.created_at.isoformat()
                }
                for t in tasks
            ]
        }, indent=2)

    elif action == "add":
        if not title:
            return "Error: 'title' is required for add action"

        # Create new task
        task = SessionTask(
            session_id=session_id,
            task_number=next_task_number,
            title=title,
            description=description,
            status=TaskStatus.PENDING
        )
        db.add(task)
        db.commit()

        return f"Added task #{task.task_number}: {title}"

    elif action == "update":
        if task_id is None:
            return "Error: 'task_id' is required for update action"

        task = get_task_by_number(session_id, task_id)
        if not task:
            return f"Error: Task #{task_id} not found"

        if status:
            task.status = TaskStatus(status)
        if description:
            task.description = description
        if notes:
            task.notes = (task.notes or "") + "\\n" + notes

        db.commit()
        return f"Updated task #{task_id}"

    elif action == "complete":
        if task_id is None:
            return "Error: 'task_id' is required for complete action"

        task = get_task_by_number(session_id, task_id)
        if not task:
            return f"Error: Task #{task_id} not found"

        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        if notes:
            task.notes = (task.notes or "") + "\\n" + notes

        db.commit()
        return f"Completed task #{task_id}: {task.title}"

    elif action == "remove":
        if task_id is None:
            return "Error: 'task_id' is required for remove action"

        task = get_task_by_number(session_id, task_id)
        if not task:
            return f"Error: Task #{task_id} not found"

        db.delete(task)
        db.commit()
        return f"Removed task #{task_id}"

    else:
        return f"Error: Unknown action '{action}'. Use: list, add, update, complete, remove"
''',
    },
    {
        "name": "Scratchpad",
        "description": """Manage working notes and intermediate thoughts that persist across turns.

Capabilities:
- Store and retrieve working notes
- Organize notes by named sections
- Persist notes across conversation turns
- Perfect for maintaining context during complex tasks

Actions:
- "read": Read scratchpad contents (use section="all" for all sections)
- "write": Write content (overwrites section)
- "append": Append content to section
- "clear": Clear section or all (if section not specified)

Sections let you organize notes by topic (e.g., "research_notes", "findings").

Examples:
- scratchpad(action="append", section="research", content="## FastAPI\\n- Modern async support")
- scratchpad(action="read", section="all")
- scratchpad(action="clear")
""",
        "category": ToolCategory.OTHER,
        "tags": ["notes", "scratchpad", "memory", "workspace", "planning"],
        "langchain_class": "WorkspaceScratchpad",
        "required_config": {},
        "function_code": '''def scratchpad(
    action: str,
    content: str = None,
    section: str = "default"
) -> str:
    """
    Manage working notes and intermediate thoughts.

    Args:
        action: One of "read", "write", "append", "clear"
        content: Content to write/append (for write/append actions)
        section: Named section (default: "default")

    Returns:
        Scratchpad contents or confirmation
    """
    # Scratchpad is stored in database (SessionScratchpad model)
    # and also synced to workspace files for visibility

    if action == "read":
        if section == "all":
            # Get all sections for this session
            scratchpads = db.query(SessionScratchpad).filter(
                SessionScratchpad.session_id == session_id
            ).all()

            if not scratchpads:
                return "Scratchpad is empty. Use action='write' or 'append' to add notes."

            output = "# Scratchpad Contents\\n\\n"
            for sp in scratchpads:
                output += f"## {sp.section}\\n\\n{sp.content}\\n\\n"
            return output

        else:
            # Get specific section
            sp = db.query(SessionScratchpad).filter(
                SessionScratchpad.session_id == session_id,
                SessionScratchpad.section == section
            ).first()

            if not sp or not sp.content:
                return f"Section '{section}' is empty."
            return sp.content

    elif action == "write":
        if content is None:
            return "Error: 'content' is required for write action"

        # Find or create section
        sp = db.query(SessionScratchpad).filter(
            SessionScratchpad.session_id == session_id,
            SessionScratchpad.section == section
        ).first()

        if sp:
            sp.content = content
        else:
            sp = SessionScratchpad(
                session_id=session_id,
                section=section,
                content=content
            )
            db.add(sp)

        db.commit()
        return f"Wrote {len(content)} chars to section '{section}'"

    elif action == "append":
        if content is None:
            return "Error: 'content' is required for append action"

        sp = db.query(SessionScratchpad).filter(
            SessionScratchpad.session_id == session_id,
            SessionScratchpad.section == section
        ).first()

        if sp:
            sp.content = (sp.content or "") + "\\n" + content
        else:
            sp = SessionScratchpad(
                session_id=session_id,
                section=section,
                content=content
            )
            db.add(sp)

        db.commit()
        return f"Appended {len(content)} chars to section '{section}'"

    elif action == "clear":
        # Clear specific section or all
        if section == "default":
            db.query(SessionScratchpad).filter(
                SessionScratchpad.session_id == session_id
            ).delete()
        else:
            db.query(SessionScratchpad).filter(
                SessionScratchpad.session_id == session_id,
                SessionScratchpad.section == section
            ).delete()

        db.commit()
        return f"Cleared scratchpad{' section: ' + section if section != 'default' else ''}"

    else:
        return f"Error: Unknown action '{action}'. Use: read, write, append, clear"
''',
    },
    # ============= WEB TOOLS =============
    # Tools for web search and content fetching
    {
        "name": "Web Search",
        "description": """Search the web for information.

Capabilities:
- Search using DuckDuckGo (free, no API key)
- Optionally use Tavily for better results (if configured)
- Returns titles, URLs, and snippets
- Up to 10 results per query

Usage:
- query (required): Search query string
- max_results (optional): Number of results 1-10 (default 5)

Examples:
- web_search(query="python asyncio tutorial") - Basic search
- web_search(query="latest AI news 2024", max_results=10) - More results
""",
        "category": ToolCategory.SEARCH,
        "tags": ["web", "search", "research", "internet"],
        "langchain_class": "WebSearch",
        "required_config": {},
        "function_code": '''def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web for information.

    Args:
        query: Search query string
        max_results: Maximum number of results (1-10)

    Returns:
        JSON formatted search results with titles, URLs, and snippets
    """
    import os
    import json
    import httpx
    from bs4 import BeautifulSoup
    import urllib.parse

    # Validate max_results
    max_results = max(1, min(10, max_results))

    def search_duckduckgo(query: str, max_results: int):
        """Search using DuckDuckGo HTML."""
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            "Accept": "text/html,application/xhtml+xml",
        }

        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.post(url, data={"q": query}, headers=headers)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        for result in soup.select(".result")[:max_results]:
            title_elem = result.select_one(".result__title a")
            snippet_elem = result.select_one(".result__snippet")

            if title_elem:
                result_url = title_elem.get("href", "")
                # Extract actual URL from DuckDuckGo redirect
                if "uddg=" in result_url:
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(result_url).query)
                    result_url = parsed.get("uddg", [result_url])[0]

                results.append({
                    "title": title_elem.get_text(strip=True),
                    "url": result_url,
                    "snippet": snippet_elem.get_text(strip=True) if snippet_elem else ""
                })

        return results

    try:
        results = search_duckduckgo(query, max_results)

        if not results:
            return json.dumps({
                "success": False,
                "error": "No search results found",
                "query": query
            }, indent=2)

        return json.dumps({
            "success": True,
            "source": "duckduckgo",
            "query": query,
            "count": len(results),
            "results": results
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "query": query
        }, indent=2)
''',
    },
    {
        "name": "Web Fetch",
        "description": """Fetch and read content from a web page URL.

Capabilities:
- Fetch any web page content
- Extract clean text from HTML
- Handle JSON responses
- Follow redirects
- Respect content length limits

Usage:
- url (required): URL to fetch
- extract_text (optional): Extract text from HTML (default True)
- include_links (optional): Include links as markdown (default False)
- max_length (optional): Maximum content length (default 10000)

Examples:
- web_fetch(url="https://example.com/article") - Fetch article text
- web_fetch(url="https://api.example.com/data", extract_text=False) - Fetch JSON
- web_fetch(url="https://docs.python.org", include_links=True) - Include links
""",
        "category": ToolCategory.SEARCH,
        "tags": ["web", "fetch", "read", "scrape", "content"],
        "langchain_class": "WebFetch",
        "required_config": {},
        "function_code": '''def web_fetch(url: str, extract_text: bool = True, include_links: bool = False, max_length: int = 10000) -> str:
    """
    Fetch content from a URL.

    Args:
        url: URL to fetch
        extract_text: Whether to extract text from HTML
        include_links: Whether to include links as markdown
        max_length: Maximum content length to return

    Returns:
        JSON formatted response with content
    """
    import json
    import re
    import httpx
    from urllib.parse import urlparse
    from bs4 import BeautifulSoup

    MAX_CONTENT_LENGTH = 50000

    # Validate URL
    try:
        parsed = urlparse(url)
        if not parsed.scheme:
            url = "https://" + url
            parsed = urlparse(url)
        if not parsed.netloc:
            return json.dumps({"success": False, "error": "Invalid URL"}, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, indent=2)

    max_length = max(100, min(MAX_CONTENT_LENGTH, max_length))

    def clean_html_to_text(html: str, include_links: bool = False) -> str:
        """Extract readable text from HTML."""
        soup = BeautifulSoup(html, "html.parser")

        # Remove non-content elements
        for elem in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            elem.decompose()

        if include_links:
            for a in soup.find_all("a", href=True):
                text = a.get_text(strip=True)
                href = a["href"]
                if text and href and not href.startswith(("#", "javascript:")):
                    a.replace_with(f"[{text}]({href})")

        text = soup.get_text(separator="\\n", strip=True)
        lines = [l.strip() for l in text.split("\\n") if l.strip()]
        return re.sub(r"\\n{3,}", "\\n\\n", "\\n".join(lines))

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()

        content_type = response.headers.get("content-type", "").lower()

        if "application/json" in content_type:
            content = json.dumps(response.json(), indent=2)
            content_format = "json"
        elif "text/html" in content_type and extract_text:
            content = clean_html_to_text(response.text, include_links)
            content_format = "text"
        else:
            content = response.text
            content_format = "raw"

        truncated = len(content) > max_length
        if truncated:
            content = content[:max_length] + "\\n\\n... [Content truncated]"

        return json.dumps({
            "success": True,
            "url": str(response.url),
            "status_code": response.status_code,
            "content_type": content_type,
            "content_format": content_format,
            "content_length": len(content),
            "truncated": truncated,
            "content": content
        }, indent=2)

    except httpx.TimeoutException:
        return json.dumps({"success": False, "error": "Request timed out"}, indent=2)
    except httpx.HTTPStatusError as e:
        return json.dumps({"success": False, "error": f"HTTP {e.response.status_code}"}, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, indent=2)
''',
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
