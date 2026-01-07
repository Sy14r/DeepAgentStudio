"""
Workspace Tools for Advanced Agent Toolkit.

This module provides LangChain-compatible tools for file operations,
task management, and scratchpad functionality within session workspaces.

Tools require a session context and operate within sandboxed workspaces.
"""
import json
import logging
from typing import List, Optional
from langchain.tools import StructuredTool, BaseTool
from sqlalchemy.orm import Session as DBSession

from .workspace import WorkspaceService, get_workspace_service

logger = logging.getLogger(__name__)


def create_workspace_tools(db: DBSession, session_id: int) -> List[BaseTool]:
    """
    Create workspace tools for a specific session.

    Args:
        db: Database session
        session_id: Session ID for workspace context

    Returns:
        List of LangChain-compatible tools
    """
    workspace_service = get_workspace_service(db)

    # Ensure workspace exists
    workspace_service.create_workspace(session_id)

    tools = [
        _create_file_read_tool(workspace_service, session_id),
        _create_file_write_tool(workspace_service, session_id),
        _create_file_edit_tool(workspace_service, session_id),
        _create_file_list_tool(workspace_service, session_id),
        _create_file_search_tool(workspace_service, session_id),
        _create_task_manager_tool(workspace_service, session_id),
        _create_scratchpad_tool(workspace_service, session_id),
    ]

    return tools


def _create_file_read_tool(ws: WorkspaceService, session_id: int) -> BaseTool:
    """Create file_read tool"""

    def file_read(path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
        """
        Read contents of a file from the workspace.

        Args:
            path: Relative path to file within workspace
            start_line: Starting line number (1-indexed, optional)
            end_line: Ending line number (inclusive, optional)

        Returns:
            File contents as string
        """
        result = ws.read_file(session_id, path, start_line, end_line)
        if result.success:
            return result.data["content"]
        else:
            return f"Error: {result.error}"

    return StructuredTool.from_function(
        func=file_read,
        name="file_read",
        description="""Read contents of a file from the workspace.
Args:
  - path (required): Relative path to file (e.g., "report.md", "data/results.json")
  - start_line (optional): Starting line number (1-indexed)
  - end_line (optional): Ending line number (inclusive)
Returns file contents. Use start_line/end_line for large files.
Example: file_read(path="notes.md") or file_read(path="data.csv", start_line=1, end_line=50)"""
    )


def _create_file_write_tool(ws: WorkspaceService, session_id: int) -> BaseTool:
    """Create file_write tool"""

    def file_write(path: str, content: str, create_dirs: bool = True) -> str:
        """
        Write content to a file in the workspace.

        Args:
            path: Relative path for the file
            content: Content to write
            create_dirs: Create parent directories if needed (default: True)

        Returns:
            Confirmation message
        """
        result = ws.write_file(session_id, path, content, create_dirs)
        if result.success:
            return result.data["message"]
        else:
            return f"Error: {result.error}"

    return StructuredTool.from_function(
        func=file_write,
        name="file_write",
        description="""Write content to a file in the workspace (creates or overwrites).
Args:
  - path (required): Relative path for the file (e.g., "reports/summary.md")
  - content (required): Content to write to the file
  - create_dirs (optional): Create parent directories if needed (default: true)
Returns confirmation with file size.
Example: file_write(path="report.md", content="# Report\\n\\nFindings...")"""
    )


def _create_file_edit_tool(ws: WorkspaceService, session_id: int) -> BaseTool:
    """Create file_edit tool"""

    def file_edit(path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
        """
        Edit a file using string replacement.

        Args:
            path: Relative path to file
            old_string: Exact string to find and replace
            new_string: Replacement string
            replace_all: Replace all occurrences (default: False, replaces first only)

        Returns:
            Confirmation with number of replacements
        """
        result = ws.edit_file(session_id, path, old_string, new_string, replace_all)
        if result.success:
            return result.data["message"]
        else:
            return f"Error: {result.error}"

    return StructuredTool.from_function(
        func=file_edit,
        name="file_edit",
        description="""Edit a file using targeted string replacement.
Args:
  - path (required): Relative path to file
  - old_string (required): Exact string to find and replace
  - new_string (required): Replacement string
  - replace_all (optional): Replace all occurrences (default: false, replaces first only)
Returns confirmation. Errors if old_string not found or multiple matches found (unless replace_all=true).
Example: file_edit(path="config.json", old_string='"debug": false', new_string='"debug": true')"""
    )


def _create_file_list_tool(ws: WorkspaceService, session_id: int) -> BaseTool:
    """Create file_list tool"""

    def file_list(pattern: str = "*", include_hidden: bool = False) -> str:
        """
        List files in workspace matching a pattern.

        Args:
            pattern: Glob pattern (e.g., "*.md", "src/**/*.py", "**/*")
            include_hidden: Include hidden files starting with . (default: False)

        Returns:
            JSON list of files with path, size, and modified date
        """
        result = ws.list_files(session_id, pattern, include_hidden)
        if result.success:
            return json.dumps(result.data, indent=2)
        else:
            return f"Error: {result.error}"

    return StructuredTool.from_function(
        func=file_list,
        name="file_list",
        description="""List files in workspace matching a glob pattern.
Args:
  - pattern (optional): Glob pattern (default: "*"). Examples: "*.md", "**/*.py", "data/*"
  - include_hidden (optional): Include hidden files (default: false)
Returns JSON list of files with path, size (bytes), and modified timestamp.
Example: file_list(pattern="**/*.md") to find all markdown files"""
    )


def _create_file_search_tool(ws: WorkspaceService, session_id: int) -> BaseTool:
    """Create file_search tool"""

    def file_search(
        pattern: str,
        file_pattern: str = "**/*",
        max_results: int = 50,
        context_lines: int = 2
    ) -> str:
        """
        Search file contents using regex.

        Args:
            pattern: Regex pattern to search for
            file_pattern: Glob pattern for files to search (default: all files)
            max_results: Maximum results to return (default: 50)
            context_lines: Lines of context around matches (default: 2)

        Returns:
            JSON list of matches with file, line number, and context
        """
        result = ws.search_files(session_id, pattern, file_pattern, max_results, context_lines)
        if result.success:
            return json.dumps(result.data, indent=2)
        else:
            return f"Error: {result.error}"

    return StructuredTool.from_function(
        func=file_search,
        name="file_search",
        description="""Search file contents using regex pattern.
Args:
  - pattern (required): Regex pattern to search for (e.g., "def \\w+\\(", "TODO")
  - file_pattern (optional): Glob pattern for files to search (default: "**/*")
  - max_results (optional): Maximum results (default: 50)
  - context_lines (optional): Lines of context around matches (default: 2)
Returns JSON list of matches with file path, line number, match text, and surrounding context.
Example: file_search(pattern="import.*pandas", file_pattern="**/*.py")"""
    )


def _create_task_manager_tool(ws: WorkspaceService, session_id: int) -> BaseTool:
    """Create task_manager tool"""

    def task_manager(
        action: str,
        task_id: Optional[int] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        notes: Optional[str] = None
    ) -> str:
        """
        Manage a task list for tracking progress on complex tasks.

        Args:
            action: One of "list", "add", "update", "complete", "remove"
            task_id: Task ID (for update/complete/remove actions)
            title: Task title (for add action)
            description: Task description (for add/update)
            status: Task status: pending, in_progress, completed, blocked (for update)
            notes: Notes to append (for update/complete)

        Returns:
            Task list or confirmation message
        """
        if action == "list":
            result = ws.get_tasks(session_id)
            if result.success:
                tasks = result.data["tasks"]
                if not tasks:
                    return "No tasks in list. Use action='add' to create tasks."
                return json.dumps({"tasks": tasks}, indent=2)
            return f"Error: {result.error}"

        elif action == "add":
            if not title:
                return "Error: 'title' is required for add action"
            result = ws.add_task(session_id, title, description)
            if result.success:
                # Return updated task list
                tasks_result = ws.get_tasks(session_id)
                return json.dumps({
                    "message": result.data["message"],
                    "tasks": tasks_result.data["tasks"] if tasks_result.success else []
                }, indent=2)
            return f"Error: {result.error}"

        elif action == "update":
            if task_id is None:
                return "Error: 'task_id' is required for update action"
            result = ws.update_task(session_id, task_id, status, notes, description)
            if result.success:
                tasks_result = ws.get_tasks(session_id)
                return json.dumps({
                    "message": result.data["message"],
                    "tasks": tasks_result.data["tasks"] if tasks_result.success else []
                }, indent=2)
            return f"Error: {result.error}"

        elif action == "complete":
            if task_id is None:
                return "Error: 'task_id' is required for complete action"
            result = ws.complete_task(session_id, task_id, notes)
            if result.success:
                tasks_result = ws.get_tasks(session_id)
                return json.dumps({
                    "message": result.data["message"],
                    "tasks": tasks_result.data["tasks"] if tasks_result.success else []
                }, indent=2)
            return f"Error: {result.error}"

        elif action == "remove":
            if task_id is None:
                return "Error: 'task_id' is required for remove action"
            result = ws.remove_task(session_id, task_id)
            if result.success:
                tasks_result = ws.get_tasks(session_id)
                return json.dumps({
                    "message": result.data["message"],
                    "tasks": tasks_result.data["tasks"] if tasks_result.success else []
                }, indent=2)
            return f"Error: {result.error}"

        else:
            return f"Error: Unknown action '{action}'. Use: list, add, update, complete, remove"

    return StructuredTool.from_function(
        func=task_manager,
        name="task_manager",
        description="""Manage a persistent task list for tracking progress on complex tasks.
Actions:
  - "list": Show all tasks
  - "add": Create a new task (requires title, optional description)
  - "update": Update task status/notes (requires task_id)
  - "complete": Mark task as completed (requires task_id, optional notes)
  - "remove": Delete a task (requires task_id)
Status values: pending, in_progress, completed, blocked
Tasks persist across conversation turns.
Examples:
  task_manager(action="add", title="Research Python frameworks")
  task_manager(action="update", task_id=1, status="in_progress")
  task_manager(action="complete", task_id=1, notes="Completed research, FastAPI recommended")"""
    )


def _create_scratchpad_tool(ws: WorkspaceService, session_id: int) -> BaseTool:
    """Create scratchpad tool"""

    def scratchpad(
        action: str,
        content: Optional[str] = None,
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
        if action == "read":
            if section == "all":
                result = ws.get_all_scratchpads(session_id)
                if result.success:
                    sections = result.data["sections"]
                    if not sections:
                        return "Scratchpad is empty. Use action='write' or 'append' to add notes."
                    output = "# Scratchpad Contents\n\n"
                    for sec, text in sections.items():
                        output += f"## {sec}\n\n{text}\n\n"
                    return output
            else:
                result = ws.get_scratchpad(session_id, section)
                if result.success:
                    content = result.data["content"]
                    if not content:
                        return f"Section '{section}' is empty."
                    return content
            return f"Error: {result.error}"

        elif action == "write":
            if content is None:
                return "Error: 'content' is required for write action"
            result = ws.write_scratchpad(session_id, content, section)
            if result.success:
                return result.data["message"]
            return f"Error: {result.error}"

        elif action == "append":
            if content is None:
                return "Error: 'content' is required for append action"
            result = ws.append_scratchpad(session_id, content, section)
            if result.success:
                return result.data["message"]
            return f"Error: {result.error}"

        elif action == "clear":
            result = ws.clear_scratchpad(session_id, section if section != "default" else None)
            if result.success:
                return result.data["message"]
            return f"Error: {result.error}"

        else:
            return f"Error: Unknown action '{action}'. Use: read, write, append, clear"

    return StructuredTool.from_function(
        func=scratchpad,
        name="scratchpad",
        description="""Manage working notes and intermediate thoughts that persist across turns.
Actions:
  - "read": Read scratchpad contents (use section="all" for all sections)
  - "write": Write content (overwrites section)
  - "append": Append content to section
  - "clear": Clear section or all (if section not specified)
Sections let you organize notes by topic (e.g., "research_notes", "findings").
Scratchpad persists across conversation turns for maintaining context.
Examples:
  scratchpad(action="append", section="research", content="## FastAPI\\n- Modern async support")
  scratchpad(action="read", section="all")
  scratchpad(action="clear")"""
    )


# Tool name to factory mapping for registration in BUILTIN_TOOL_REGISTRY
# Note: These tools require session context, so they're created dynamically
WORKSPACE_TOOL_NAMES = [
    "file_read",
    "file_write",
    "file_edit",
    "file_list",
    "file_search",
    "task_manager",
    "scratchpad",
]


def is_workspace_tool(tool_name: str) -> bool:
    """Check if a tool name is a workspace tool"""
    return tool_name in WORKSPACE_TOOL_NAMES
