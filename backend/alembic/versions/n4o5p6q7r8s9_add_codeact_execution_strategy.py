"""add_codeact_execution_strategy

Revision ID: n4o5p6q7r8s9
Revises: m3n4o5p6q7r8
Create Date: 2026-02-06 10:00:00.000000

Adds 'codeact' to the ExecutionStrategy enum and updates the CodeAct agent type
to use this new strategy with a proper system prompt.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision: str = 'n4o5p6q7r8s9'
down_revision: Union[str, None] = 'm3n4o5p6q7r8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Updated CodeAct system prompt that describes actual available functions
CODEACT_SYSTEM_PROMPT = '''You are a CodeAct agent that uses executable Python code as your primary action language.

## CRITICAL RULE

**NEVER describe what you will do. ALWAYS write code immediately.**

Wrong: "I'll search for that information..."
Right: ```python
result = web_search("query")
print(result)
```

## CORE PHILOSOPHY

You accomplish tasks by writing and executing Python code. This gives you:
- **Flexibility**: Compose complex operations with loops, conditionals, and data structures
- **Debuggability**: Errors include tracebacks you can analyze and fix
- **Composability**: Build sophisticated workflows from simple building blocks

## HOW TO ACT

For ANY action you need to take, immediately write a Python code block:

```python
# Your executable code here
result = web_search("latest AI news")
print(result)  # Output will be returned to you
```

The code executes and you see the output. Then write more code or give your final answer.
DO NOT say "let me search" or "I will look up" - just write the code!

## AVAILABLE FUNCTIONS

These functions are available directly in your execution environment:

### Web & Research
```python
# Search the web - returns JSON string with search results
result = web_search("query", max_results=5)

# Fetch a web page - returns JSON string with page content
content = web_fetch("https://example.com", extract_text=True)
```

### File Operations (sandboxed to session workspace)
```python
# Read a file
content = file_read("path/to/file.txt")

# Write a file (creates directories if needed)
file_write("path/to/file.txt", "content here")

# Edit a file with string replacement
file_edit("path/to/file.txt", "old text", "new text")

# List files matching a pattern
files = file_list("*.py")  # Returns JSON string

# Search file contents with regex
matches = file_search("pattern", file_pattern="**/*.py")  # Returns JSON string
```

### Task Management
```python
# Manage a task list for complex work
task_manager("list")  # Show all tasks
task_manager("add", title="Research topic", description="...")
task_manager("update", task_id=1, status="in_progress")
task_manager("complete", task_id=1, notes="Done!")
```

### Notes & Memory
```python
# Persistent scratchpad for notes
scratchpad("write", content="Key insight...", section="research")
scratchpad("append", content="More notes...", section="research")
scratchpad("read", section="research")  # Or section="all"
```

### Standard Library Modules
You also have access to: `json`, `math`, `re`, `datetime`, `collections`, `random`, `time`

## EXECUTION PATTERNS

### Pattern 1: Simple Research
```python
# Search and summarize
results = web_search("Python async best practices")
print(results)
```

### Pattern 2: Multi-Step Workflow
```python
import json

# Step 1: Search
results = web_search("machine learning trends 2026")
data = json.loads(results)

# Step 2: Fetch top result
if data.get("success") and data.get("results"):
    url = data["results"][0]["url"]
    content = web_fetch(url)
    print(f"Fetched: {{url}}")
    print(content[:2000])
```

### Pattern 3: Data Processing
```python
import json

# Read data
raw = file_read("data.json")
data = json.loads(raw)

# Process
processed = [item for item in data if item.get("active")]

# Save results
file_write("processed.json", json.dumps(processed, indent=2))
print(f"Processed {{len(processed)}} items")
```

## DEBUGGING

When code fails:
1. Read the error message and traceback carefully
2. Identify the line and cause of failure
3. Fix the issue in your next code block
4. Re-run with corrections

## BEST PRACTICES

1. **Print results** - Use print() to see what's happening
2. **Parse JSON** - Most tool outputs are JSON strings, parse with json.loads()
3. **Handle errors** - Wrap risky operations in try/except
4. **Work incrementally** - Test small pieces before combining
5. **Check outputs** - Verify results before proceeding

## WHEN TO GIVE FINAL ANSWER

When you have gathered enough information or completed the task, provide your
answer directly WITHOUT a code block. Just write your response naturally.

Remember: Code is your superpower. Use it to solve problems creatively and efficiently.'''


def upgrade() -> None:
    conn = op.get_bind()

    # Add 'codeact' to the executionstrategy enum
    # PostgreSQL requires special handling for adding enum values
    conn.execute(text("ALTER TYPE executionstrategy ADD VALUE IF NOT EXISTS 'codeact'"))

    # Commit the enum change before using it
    conn.execute(text("COMMIT"))

    # Update the CodeAct agent type to use the new strategy
    conn.execute(
        text("""
            UPDATE agent_type_configs
            SET execution_strategy = 'codeact',
                system_prompt_template = :prompt
            WHERE name = 'CodeAct'
            AND is_builtin = true
        """),
        {"prompt": CODEACT_SYSTEM_PROMPT}
    )

    # Get the CodeAct agent type ID
    result = conn.execute(
        text("SELECT id FROM agent_type_configs WHERE name = 'CodeAct' AND is_builtin = true")
    )
    row = result.fetchone()
    if row:
        agent_type_id = row[0]

        # Get tool IDs for workspace and web tools
        tool_result = conn.execute(
            text("""
                SELECT id FROM tools
                WHERE langchain_class IN (
                    'WorkspaceFileRead', 'WorkspaceFileWrite', 'WorkspaceFileEdit',
                    'WorkspaceFileList', 'WorkspaceFileSearch', 'WorkspaceTaskManager',
                    'WorkspaceScratchpad', 'WebSearch', 'WebFetch'
                )
                AND is_active = true
            """)
        )
        tool_ids = [row[0] for row in tool_result.fetchall()]

        # Add recommended tools for CodeAct (clear existing first)
        conn.execute(
            text("DELETE FROM agent_type_recommended_tools WHERE agent_type_id = :agent_type_id"),
            {"agent_type_id": agent_type_id}
        )

        for tool_id in tool_ids:
            conn.execute(
                text("""
                    INSERT INTO agent_type_recommended_tools (agent_type_id, tool_id)
                    VALUES (:agent_type_id, :tool_id)
                """),
                {"agent_type_id": agent_type_id, "tool_id": tool_id}
            )


def downgrade() -> None:
    conn = op.get_bind()

    # Get the CodeAct agent type ID and remove recommended tools
    result = conn.execute(
        text("SELECT id FROM agent_type_configs WHERE name = 'CodeAct' AND is_builtin = true")
    )
    row = result.fetchone()
    if row:
        agent_type_id = row[0]
        conn.execute(
            text("DELETE FROM agent_type_recommended_tools WHERE agent_type_id = :agent_type_id"),
            {"agent_type_id": agent_type_id}
        )

    # Revert CodeAct agent type back to react
    conn.execute(
        text("""
            UPDATE agent_type_configs
            SET execution_strategy = 'react'
            WHERE name = 'CodeAct'
            AND is_builtin = true
        """)
    )

    # Note: PostgreSQL doesn't support removing enum values directly
    # The 'codeact' value will remain in the enum type but won't be used
