"""
Workspace Service for Advanced Agent Toolkit.

This service manages isolated workspaces for agent sessions:
- Creates and manages workspace directories
- Handles file operations within sandboxed workspaces
- Manages task lists and scratchpads
- Syncs between database and workspace files
"""
import os
import shutil
import logging
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func

from ..models import (
    Session, SessionWorkspace, SessionTask, SessionScratchpad,
    TaskStatus
)
from ..config import settings

logger = logging.getLogger(__name__)


# Configuration
WORKSPACE_BASE_PATH = os.environ.get("WORKSPACE_BASE_PATH", "/var/lib/deepagent/workspaces")
WORKSPACE_MAX_SIZE_MB = int(os.environ.get("WORKSPACE_MAX_SIZE_MB", "100"))
WORKSPACE_FILE_MAX_SIZE_MB = int(os.environ.get("WORKSPACE_FILE_MAX_SIZE_MB", "10"))


@dataclass
class FileInfo:
    """Information about a file in the workspace"""
    path: str
    size: int
    modified: datetime
    is_directory: bool = False


@dataclass
class WorkspaceResult:
    """Result of workspace operation"""
    success: bool
    data: Any = None
    error: Optional[str] = None


class WorkspaceService:
    """
    Service for managing session workspaces.

    Each session gets an isolated workspace directory where files can be
    created, read, edited, and deleted. The workspace is sandboxed for security.

    Usage:
        workspace = WorkspaceService(db)
        result = workspace.create_workspace(session_id)
        result = workspace.write_file(session_id, "report.md", "# Report\n...")
    """

    def __init__(self, db: DBSession):
        """Initialize workspace service with database session"""
        self.db = db
        self.base_path = Path(WORKSPACE_BASE_PATH)
        self.max_workspace_size = WORKSPACE_MAX_SIZE_MB * 1024 * 1024  # Convert to bytes
        self.max_file_size = WORKSPACE_FILE_MAX_SIZE_MB * 1024 * 1024

    def _get_workspace_path(self, session_id: int) -> Path:
        """Get the filesystem path for a session's workspace"""
        return self.base_path / str(session_id)

    def _validate_path(self, workspace_path: Path, relative_path: str) -> tuple[bool, Optional[str], Optional[Path]]:
        """
        Validate a relative path within a workspace.

        Returns:
            Tuple of (is_valid, error_message, resolved_path)
        """
        # Normalize and check for path traversal
        try:
            # Remove leading slashes to make it relative
            relative_path = relative_path.lstrip("/\\")

            # Check for path traversal attempts
            if ".." in relative_path:
                return False, "Path traversal not allowed", None

            # Resolve the full path
            full_path = (workspace_path / relative_path).resolve()

            # Ensure it's still within the workspace
            if not str(full_path).startswith(str(workspace_path.resolve())):
                return False, "Path must be within workspace", None

            return True, None, full_path

        except Exception as e:
            return False, f"Invalid path: {str(e)}", None

    def _update_workspace_stats(self, workspace: SessionWorkspace) -> None:
        """Update workspace size and file count statistics"""
        workspace_path = self._get_workspace_path(workspace.session_id)

        total_size = 0
        file_count = 0

        if workspace_path.exists():
            for root, dirs, files in os.walk(workspace_path):
                for f in files:
                    file_path = Path(root) / f
                    if file_path.exists():
                        total_size += file_path.stat().st_size
                        file_count += 1

        workspace.total_size_bytes = total_size
        workspace.file_count = file_count
        self.db.commit()

    # === Workspace Management ===

    def create_workspace(self, session_id: int) -> WorkspaceResult:
        """
        Create a workspace for a session.

        Args:
            session_id: Session ID to create workspace for

        Returns:
            WorkspaceResult with workspace info
        """
        try:
            # Check if workspace already exists
            existing = self.db.query(SessionWorkspace).filter(
                SessionWorkspace.session_id == session_id
            ).first()

            if existing:
                return WorkspaceResult(
                    success=True,
                    data={"workspace_path": existing.workspace_path, "already_exists": True}
                )

            # Create workspace directory
            workspace_path = self._get_workspace_path(session_id)
            workspace_path.mkdir(parents=True, exist_ok=True)

            # Create workspace record
            workspace = SessionWorkspace(
                session_id=session_id,
                workspace_path=str(session_id),
                total_size_bytes=0,
                file_count=0
            )
            self.db.add(workspace)
            self.db.commit()

            # Create default files
            self._create_default_files(workspace_path, session_id)

            logger.info(f"Created workspace for session {session_id} at {workspace_path}")

            return WorkspaceResult(
                success=True,
                data={"workspace_path": str(session_id), "created": True}
            )

        except Exception as e:
            logger.error(f"Failed to create workspace for session {session_id}: {e}")
            self.db.rollback()
            return WorkspaceResult(success=False, error=str(e))

    def _create_default_files(self, workspace_path: Path, session_id: int) -> None:
        """Create default workspace files (_tasks.md, _scratchpad.md, _progress.md)"""
        # Tasks file
        tasks_content = f"""# Task List - Session {session_id}

_This file is auto-synced with the task_manager tool._

## Tasks

_No tasks yet. Use the task_manager tool to add tasks._
"""
        (workspace_path / "_tasks.md").write_text(tasks_content)

        # Scratchpad file
        scratchpad_content = f"""# Scratchpad - Session {session_id}

_This file is auto-synced with the scratchpad tool._

## Notes

_Use the scratchpad tool to add notes and working thoughts._
"""
        (workspace_path / "_scratchpad.md").write_text(scratchpad_content)

        # Progress file
        progress_content = f"""# Progress Log - Session {session_id}

_This file auto-updates as tasks are completed._

## Timeline

- {datetime.now().isoformat()}: Workspace created
"""
        (workspace_path / "_progress.md").write_text(progress_content)

    def get_workspace(self, session_id: int) -> Optional[SessionWorkspace]:
        """Get workspace record for a session"""
        return self.db.query(SessionWorkspace).filter(
            SessionWorkspace.session_id == session_id
        ).first()

    def delete_workspace(self, session_id: int) -> WorkspaceResult:
        """
        Delete a workspace and all its contents.

        Args:
            session_id: Session ID to delete workspace for

        Returns:
            WorkspaceResult indicating success/failure
        """
        try:
            workspace = self.get_workspace(session_id)
            if not workspace:
                return WorkspaceResult(success=True, data={"message": "Workspace not found"})

            # Delete filesystem directory
            workspace_path = self._get_workspace_path(session_id)
            if workspace_path.exists():
                shutil.rmtree(workspace_path)

            # Delete database record (cascade deletes tasks and scratchpads)
            self.db.delete(workspace)
            self.db.commit()

            logger.info(f"Deleted workspace for session {session_id}")
            return WorkspaceResult(success=True, data={"message": "Workspace deleted"})

        except Exception as e:
            logger.error(f"Failed to delete workspace for session {session_id}: {e}")
            self.db.rollback()
            return WorkspaceResult(success=False, error=str(e))

    # === File Operations ===

    def read_file(
        self,
        session_id: int,
        path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None
    ) -> WorkspaceResult:
        """
        Read a file from the workspace.

        Args:
            session_id: Session ID
            path: Relative path to file
            start_line: Starting line (1-indexed, optional)
            end_line: Ending line (inclusive, optional)

        Returns:
            WorkspaceResult with file contents
        """
        try:
            workspace = self.get_workspace(session_id)
            if not workspace:
                return WorkspaceResult(success=False, error="Workspace not found")

            workspace_path = self._get_workspace_path(session_id)
            valid, error, full_path = self._validate_path(workspace_path, path)
            if not valid:
                return WorkspaceResult(success=False, error=error)

            if not full_path.exists():
                return WorkspaceResult(success=False, error=f"File not found: {path}")

            if full_path.is_dir():
                return WorkspaceResult(success=False, error=f"Path is a directory: {path}")

            content = full_path.read_text()

            # Apply line range if specified
            if start_line is not None or end_line is not None:
                lines = content.split('\n')
                start = (start_line - 1) if start_line else 0
                end = end_line if end_line else len(lines)
                selected_lines = lines[start:end]

                # Format with line numbers
                numbered_lines = [
                    f"{i + start + 1}: {line}"
                    for i, line in enumerate(selected_lines)
                ]
                content = '\n'.join(numbered_lines)

            return WorkspaceResult(
                success=True,
                data={
                    "path": path,
                    "content": content,
                    "size": full_path.stat().st_size
                }
            )

        except Exception as e:
            logger.error(f"Failed to read file {path} in session {session_id}: {e}")
            return WorkspaceResult(success=False, error=str(e))

    def write_file(
        self,
        session_id: int,
        path: str,
        content: str,
        create_dirs: bool = True
    ) -> WorkspaceResult:
        """
        Write content to a file in the workspace.

        Args:
            session_id: Session ID
            path: Relative path for the file
            content: Content to write
            create_dirs: Create parent directories if needed

        Returns:
            WorkspaceResult with file info
        """
        try:
            workspace = self.get_workspace(session_id)
            if not workspace:
                return WorkspaceResult(success=False, error="Workspace not found")

            # Check file size limit
            content_size = len(content.encode('utf-8'))
            if content_size > self.max_file_size:
                return WorkspaceResult(
                    success=False,
                    error=f"File size ({content_size} bytes) exceeds limit ({self.max_file_size} bytes)"
                )

            workspace_path = self._get_workspace_path(session_id)
            valid, error, full_path = self._validate_path(workspace_path, path)
            if not valid:
                return WorkspaceResult(success=False, error=error)

            # Check workspace size limit
            current_size = workspace.total_size_bytes or 0
            if current_size + content_size > self.max_workspace_size:
                return WorkspaceResult(
                    success=False,
                    error=f"Workspace size limit exceeded ({self.max_workspace_size // (1024*1024)}MB)"
                )

            # Create parent directories if needed
            if create_dirs:
                full_path.parent.mkdir(parents=True, exist_ok=True)
            elif not full_path.parent.exists():
                return WorkspaceResult(success=False, error=f"Parent directory does not exist: {full_path.parent}")

            # Write the file
            full_path.write_text(content)

            # Update workspace stats
            self._update_workspace_stats(workspace)

            logger.info(f"Wrote {content_size} bytes to {path} in session {session_id}")

            return WorkspaceResult(
                success=True,
                data={
                    "path": path,
                    "size": content_size,
                    "message": f"Successfully wrote {content_size} bytes to {path}"
                }
            )

        except Exception as e:
            logger.error(f"Failed to write file {path} in session {session_id}: {e}")
            return WorkspaceResult(success=False, error=str(e))

    def edit_file(
        self,
        session_id: int,
        path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False
    ) -> WorkspaceResult:
        """
        Edit a file using string replacement.

        Args:
            session_id: Session ID
            path: Relative path to file
            old_string: String to find
            new_string: Replacement string
            replace_all: Replace all occurrences (default: first only)

        Returns:
            WorkspaceResult with edit info
        """
        try:
            workspace = self.get_workspace(session_id)
            if not workspace:
                return WorkspaceResult(success=False, error="Workspace not found")

            workspace_path = self._get_workspace_path(session_id)
            valid, error, full_path = self._validate_path(workspace_path, path)
            if not valid:
                return WorkspaceResult(success=False, error=error)

            if not full_path.exists():
                return WorkspaceResult(success=False, error=f"File not found: {path}")

            content = full_path.read_text()

            # Check if old_string exists
            count = content.count(old_string)
            if count == 0:
                return WorkspaceResult(success=False, error=f"String not found in file: {old_string[:50]}...")

            if count > 1 and not replace_all:
                return WorkspaceResult(
                    success=False,
                    error=f"Multiple occurrences found ({count}). Use replace_all=true to replace all."
                )

            # Perform replacement
            if replace_all:
                new_content = content.replace(old_string, new_string)
                replacements = count
            else:
                new_content = content.replace(old_string, new_string, 1)
                replacements = 1

            # Write back
            full_path.write_text(new_content)

            # Update workspace stats
            self._update_workspace_stats(workspace)

            return WorkspaceResult(
                success=True,
                data={
                    "path": path,
                    "replacements": replacements,
                    "message": f"Replaced {replacements} occurrence(s) in {path}"
                }
            )

        except Exception as e:
            logger.error(f"Failed to edit file {path} in session {session_id}: {e}")
            return WorkspaceResult(success=False, error=str(e))

    def list_files(
        self,
        session_id: int,
        pattern: str = "*",
        include_hidden: bool = False
    ) -> WorkspaceResult:
        """
        List files in workspace matching a pattern.

        Args:
            session_id: Session ID
            pattern: Glob pattern (e.g., "*.md", "**/*.py")
            include_hidden: Include hidden files (starting with .)

        Returns:
            WorkspaceResult with list of FileInfo
        """
        try:
            workspace = self.get_workspace(session_id)
            if not workspace:
                return WorkspaceResult(success=False, error="Workspace not found")

            workspace_path = self._get_workspace_path(session_id)
            if not workspace_path.exists():
                return WorkspaceResult(success=False, error="Workspace directory not found")

            files = []
            for file_path in workspace_path.glob(pattern):
                # Skip hidden files unless requested
                if not include_hidden and file_path.name.startswith('.'):
                    continue

                # Get relative path
                rel_path = file_path.relative_to(workspace_path)
                stat = file_path.stat()

                files.append({
                    "path": str(rel_path),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "is_directory": file_path.is_dir()
                })

            # Sort by modification time (most recent first)
            files.sort(key=lambda x: x["modified"], reverse=True)

            return WorkspaceResult(success=True, data={"files": files, "count": len(files)})

        except Exception as e:
            logger.error(f"Failed to list files in session {session_id}: {e}")
            return WorkspaceResult(success=False, error=str(e))

    def search_files(
        self,
        session_id: int,
        pattern: str,
        file_pattern: str = "**/*",
        max_results: int = 50,
        context_lines: int = 2
    ) -> WorkspaceResult:
        """
        Search file contents using regex.

        Args:
            session_id: Session ID
            pattern: Regex pattern to search for
            file_pattern: Glob pattern for files to search
            max_results: Maximum results to return
            context_lines: Lines of context around matches

        Returns:
            WorkspaceResult with search matches
        """
        import re

        try:
            workspace = self.get_workspace(session_id)
            if not workspace:
                return WorkspaceResult(success=False, error="Workspace not found")

            workspace_path = self._get_workspace_path(session_id)
            if not workspace_path.exists():
                return WorkspaceResult(success=False, error="Workspace directory not found")

            # Compile regex
            try:
                regex = re.compile(pattern)
            except re.error as e:
                return WorkspaceResult(success=False, error=f"Invalid regex: {e}")

            matches = []
            for file_path in workspace_path.glob(file_pattern):
                if file_path.is_dir():
                    continue

                try:
                    content = file_path.read_text()
                    lines = content.split('\n')

                    for i, line in enumerate(lines):
                        if regex.search(line):
                            # Get context
                            start = max(0, i - context_lines)
                            end = min(len(lines), i + context_lines + 1)
                            context = '\n'.join(
                                f"{j+1}: {lines[j]}"
                                for j in range(start, end)
                            )

                            matches.append({
                                "file": str(file_path.relative_to(workspace_path)),
                                "line": i + 1,
                                "match": line.strip(),
                                "context": context
                            })

                            if len(matches) >= max_results:
                                break

                except Exception:
                    # Skip files that can't be read as text
                    continue

                if len(matches) >= max_results:
                    break

            return WorkspaceResult(
                success=True,
                data={"matches": matches, "count": len(matches), "truncated": len(matches) >= max_results}
            )

        except Exception as e:
            logger.error(f"Failed to search files in session {session_id}: {e}")
            return WorkspaceResult(success=False, error=str(e))

    # === Task Management ===

    def get_tasks(self, session_id: int) -> WorkspaceResult:
        """Get all tasks for a session"""
        try:
            tasks = self.db.query(SessionTask).filter(
                SessionTask.session_id == session_id
            ).order_by(SessionTask.task_number).all()

            return WorkspaceResult(
                success=True,
                data={
                    "tasks": [
                        {
                            "id": t.task_number,
                            "title": t.title,
                            "description": t.description,
                            "status": t.status.value,
                            "notes": t.notes,
                            "created_at": t.created_at.isoformat() if t.created_at else None,
                            "completed_at": t.completed_at.isoformat() if t.completed_at else None
                        }
                        for t in tasks
                    ]
                }
            )

        except Exception as e:
            logger.error(f"Failed to get tasks for session {session_id}: {e}")
            return WorkspaceResult(success=False, error=str(e))

    def add_task(
        self,
        session_id: int,
        title: str,
        description: Optional[str] = None
    ) -> WorkspaceResult:
        """Add a new task"""
        try:
            # Get next task number
            max_num = self.db.query(func.max(SessionTask.task_number)).filter(
                SessionTask.session_id == session_id
            ).scalar() or 0

            task = SessionTask(
                session_id=session_id,
                task_number=max_num + 1,
                title=title,
                description=description,
                status=TaskStatus.PENDING
            )
            self.db.add(task)
            self.db.commit()

            # Sync to workspace file
            self._sync_tasks_to_file(session_id)

            return WorkspaceResult(
                success=True,
                data={
                    "message": f"Task #{task.task_number} created",
                    "task_id": task.task_number
                }
            )

        except Exception as e:
            logger.error(f"Failed to add task for session {session_id}: {e}")
            self.db.rollback()
            return WorkspaceResult(success=False, error=str(e))

    def update_task(
        self,
        session_id: int,
        task_id: int,
        status: Optional[str] = None,
        notes: Optional[str] = None,
        description: Optional[str] = None
    ) -> WorkspaceResult:
        """Update an existing task"""
        try:
            task = self.db.query(SessionTask).filter(
                SessionTask.session_id == session_id,
                SessionTask.task_number == task_id
            ).first()

            if not task:
                return WorkspaceResult(success=False, error=f"Task #{task_id} not found")

            if status:
                try:
                    task.status = TaskStatus(status)
                    if status == "completed":
                        task.completed_at = datetime.utcnow()
                except ValueError:
                    return WorkspaceResult(success=False, error=f"Invalid status: {status}")

            if notes:
                # Append to existing notes
                if task.notes:
                    task.notes = f"{task.notes}\n\n---\n{datetime.utcnow().isoformat()}: {notes}"
                else:
                    task.notes = f"{datetime.utcnow().isoformat()}: {notes}"

            if description:
                task.description = description

            self.db.commit()

            # Sync to workspace file
            self._sync_tasks_to_file(session_id)

            # Update progress file if completed
            if status == "completed":
                self._log_progress(session_id, f"Completed task #{task_id}: {task.title}")

            return WorkspaceResult(
                success=True,
                data={"message": f"Task #{task_id} updated", "status": task.status.value}
            )

        except Exception as e:
            logger.error(f"Failed to update task {task_id} for session {session_id}: {e}")
            self.db.rollback()
            return WorkspaceResult(success=False, error=str(e))

    def complete_task(self, session_id: int, task_id: int, notes: Optional[str] = None) -> WorkspaceResult:
        """Mark a task as completed"""
        return self.update_task(session_id, task_id, status="completed", notes=notes)

    def remove_task(self, session_id: int, task_id: int) -> WorkspaceResult:
        """Remove a task"""
        try:
            task = self.db.query(SessionTask).filter(
                SessionTask.session_id == session_id,
                SessionTask.task_number == task_id
            ).first()

            if not task:
                return WorkspaceResult(success=False, error=f"Task #{task_id} not found")

            self.db.delete(task)
            self.db.commit()

            # Sync to workspace file
            self._sync_tasks_to_file(session_id)

            return WorkspaceResult(success=True, data={"message": f"Task #{task_id} removed"})

        except Exception as e:
            logger.error(f"Failed to remove task {task_id} for session {session_id}: {e}")
            self.db.rollback()
            return WorkspaceResult(success=False, error=str(e))

    def _sync_tasks_to_file(self, session_id: int) -> None:
        """Sync task list to workspace file"""
        try:
            workspace_path = self._get_workspace_path(session_id)
            if not workspace_path.exists():
                return

            tasks = self.db.query(SessionTask).filter(
                SessionTask.session_id == session_id
            ).order_by(SessionTask.task_number).all()

            content = f"""# Task List - Session {session_id}

_This file is auto-synced with the task_manager tool._
_Last updated: {datetime.utcnow().isoformat()}_

## Tasks

"""
            for task in tasks:
                status_icon = {
                    TaskStatus.PENDING: "[ ]",
                    TaskStatus.IN_PROGRESS: "[~]",
                    TaskStatus.COMPLETED: "[x]",
                    TaskStatus.BLOCKED: "[!]"
                }.get(task.status, "[ ]")

                content += f"{status_icon} **#{task.task_number}**: {task.title}\n"
                if task.description:
                    content += f"    {task.description}\n"
                if task.notes:
                    content += f"    _Notes: {task.notes[:100]}{'...' if len(task.notes) > 100 else ''}_\n"
                content += "\n"

            if not tasks:
                content += "_No tasks yet. Use the task_manager tool to add tasks._\n"

            (workspace_path / "_tasks.md").write_text(content)

        except Exception as e:
            logger.error(f"Failed to sync tasks to file for session {session_id}: {e}")

    # === Scratchpad Management ===

    def get_scratchpad(self, session_id: int, section: str = "default") -> WorkspaceResult:
        """Get scratchpad content for a section"""
        try:
            scratchpad = self.db.query(SessionScratchpad).filter(
                SessionScratchpad.session_id == session_id,
                SessionScratchpad.section == section
            ).first()

            if not scratchpad:
                return WorkspaceResult(success=True, data={"section": section, "content": ""})

            return WorkspaceResult(
                success=True,
                data={"section": section, "content": scratchpad.content}
            )

        except Exception as e:
            logger.error(f"Failed to get scratchpad for session {session_id}: {e}")
            return WorkspaceResult(success=False, error=str(e))

    def get_all_scratchpads(self, session_id: int) -> WorkspaceResult:
        """Get all scratchpad sections"""
        try:
            scratchpads = self.db.query(SessionScratchpad).filter(
                SessionScratchpad.session_id == session_id
            ).all()

            return WorkspaceResult(
                success=True,
                data={
                    "sections": {s.section: s.content for s in scratchpads}
                }
            )

        except Exception as e:
            logger.error(f"Failed to get scratchpads for session {session_id}: {e}")
            return WorkspaceResult(success=False, error=str(e))

    def write_scratchpad(
        self,
        session_id: int,
        content: str,
        section: str = "default"
    ) -> WorkspaceResult:
        """Write content to scratchpad (overwrites)"""
        try:
            scratchpad = self.db.query(SessionScratchpad).filter(
                SessionScratchpad.session_id == session_id,
                SessionScratchpad.section == section
            ).first()

            if scratchpad:
                scratchpad.content = content
            else:
                scratchpad = SessionScratchpad(
                    session_id=session_id,
                    section=section,
                    content=content
                )
                self.db.add(scratchpad)

            self.db.commit()

            # Sync to workspace file
            self._sync_scratchpad_to_file(session_id)

            return WorkspaceResult(
                success=True,
                data={"message": f"Wrote {len(content)} characters to section '{section}'"}
            )

        except Exception as e:
            logger.error(f"Failed to write scratchpad for session {session_id}: {e}")
            self.db.rollback()
            return WorkspaceResult(success=False, error=str(e))

    def append_scratchpad(
        self,
        session_id: int,
        content: str,
        section: str = "default"
    ) -> WorkspaceResult:
        """Append content to scratchpad"""
        try:
            scratchpad = self.db.query(SessionScratchpad).filter(
                SessionScratchpad.session_id == session_id,
                SessionScratchpad.section == section
            ).first()

            if scratchpad:
                scratchpad.content = f"{scratchpad.content}\n{content}" if scratchpad.content else content
            else:
                scratchpad = SessionScratchpad(
                    session_id=session_id,
                    section=section,
                    content=content
                )
                self.db.add(scratchpad)

            self.db.commit()

            # Sync to workspace file
            self._sync_scratchpad_to_file(session_id)

            return WorkspaceResult(
                success=True,
                data={"message": f"Appended {len(content)} characters to section '{section}'"}
            )

        except Exception as e:
            logger.error(f"Failed to append scratchpad for session {session_id}: {e}")
            self.db.rollback()
            return WorkspaceResult(success=False, error=str(e))

    def clear_scratchpad(self, session_id: int, section: Optional[str] = None) -> WorkspaceResult:
        """Clear scratchpad content (specific section or all)"""
        try:
            query = self.db.query(SessionScratchpad).filter(
                SessionScratchpad.session_id == session_id
            )
            if section:
                query = query.filter(SessionScratchpad.section == section)

            query.delete()
            self.db.commit()

            # Sync to workspace file
            self._sync_scratchpad_to_file(session_id)

            return WorkspaceResult(
                success=True,
                data={"message": f"Cleared scratchpad{f' section {section}' if section else ''}"}
            )

        except Exception as e:
            logger.error(f"Failed to clear scratchpad for session {session_id}: {e}")
            self.db.rollback()
            return WorkspaceResult(success=False, error=str(e))

    def _sync_scratchpad_to_file(self, session_id: int) -> None:
        """Sync scratchpad to workspace file"""
        try:
            workspace_path = self._get_workspace_path(session_id)
            if not workspace_path.exists():
                return

            scratchpads = self.db.query(SessionScratchpad).filter(
                SessionScratchpad.session_id == session_id
            ).all()

            content = f"""# Scratchpad - Session {session_id}

_This file is auto-synced with the scratchpad tool._
_Last updated: {datetime.utcnow().isoformat()}_

"""
            for sp in scratchpads:
                content += f"## {sp.section}\n\n{sp.content}\n\n"

            if not scratchpads:
                content += "_Use the scratchpad tool to add notes and working thoughts._\n"

            (workspace_path / "_scratchpad.md").write_text(content)

        except Exception as e:
            logger.error(f"Failed to sync scratchpad to file for session {session_id}: {e}")

    def _log_progress(self, session_id: int, message: str) -> None:
        """Log a progress entry"""
        try:
            workspace_path = self._get_workspace_path(session_id)
            if not workspace_path.exists():
                return

            progress_file = workspace_path / "_progress.md"
            content = progress_file.read_text() if progress_file.exists() else ""
            content += f"- {datetime.utcnow().isoformat()}: {message}\n"
            progress_file.write_text(content)

        except Exception as e:
            logger.error(f"Failed to log progress for session {session_id}: {e}")


# Singleton instance
_workspace_service: Optional[WorkspaceService] = None


def get_workspace_service(db: DBSession) -> WorkspaceService:
    """Get workspace service instance"""
    return WorkspaceService(db)
