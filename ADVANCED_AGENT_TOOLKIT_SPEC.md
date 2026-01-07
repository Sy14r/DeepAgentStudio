# Advanced Agent Toolkit Specification

**Version**: 1.0
**Created**: 2026-01-06
**Status**: Draft

## Executive Summary

This specification defines a comprehensive set of built-in tools and a default "Power Agent" that enables DeepAgentStudio agents to perform long, multi-turn autonomous tasks. The toolkit follows 2025 best practices from Anthropic, LangChain, and production agent frameworks.

### Goals

1. Enable agents to work autonomously on complex, multi-step tasks
2. Provide essential tools for file operations, task management, and web research
3. Create a showcase "Power Agent" demonstrating platform capabilities
4. Maintain security through sandboxed execution

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| File Scope | Sandboxed workspace per session | Security isolation, prevents system access |
| Web Search | Real search API integration | Production-ready, real-world utility |
| Persistence | Database + workspace files | Durability + agent file access |
| Security Model | Docker sandbox | Consistent with existing Python tool |

---

## Architecture Overview

### The Agent Loop

Based on Anthropic's Claude Agent SDK pattern:

```
┌─────────────────────────────────────────────────────────┐
│                    AGENT LOOP                           │
│                                                         │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐          │
│   │  GATHER  │ → │   ACT    │ → │  VERIFY  │ → repeat │
│   │ CONTEXT  │   │          │   │   WORK   │          │
│   └──────────┘   └──────────┘   └──────────┘          │
│        │              │              │                 │
│        ▼              ▼              ▼                 │
│   file_search    file_write    task_manager           │
│   content_search python_exec   scratchpad             │
│   web_search     file_edit                            │
│   web_fetch      http_request                         │
│   file_read                                           │
└─────────────────────────────────────────────────────────┘
```

### Session Workspace

Each agent session gets an isolated workspace directory:

```
/workspace/
└── {session_id}/
    ├── _tasks.md          # Task manager file (synced to DB)
    ├── _scratchpad.md     # Working notes (synced to DB)
    ├── _progress.md       # Auto-generated progress log
    └── {user_files}/      # Files created by agent
```

---

## New Built-in Tools

### Tool Summary

| Tool | Category | Priority | Description |
|------|----------|----------|-------------|
| `file_read` | File Ops | P0 | Read file contents from workspace |
| `file_write` | File Ops | P0 | Create/overwrite files in workspace |
| `file_edit` | File Ops | P0 | Targeted string replacement |
| `file_list` | File Ops | P1 | List files matching glob pattern |
| `file_search` | File Ops | P1 | Search file contents with regex |
| `task_manager` | Planning | P0 | Manage task list with status tracking |
| `scratchpad` | Memory | P0 | Read/write working notes |
| `web_search` | Research | P1 | Search the web for information |
| `web_fetch` | Research | P1 | Fetch and extract URL content |

### Existing Tools (Enhanced)

| Tool | Enhancement |
|------|-------------|
| `python_code_execution` | Add workspace path as working directory |
| `http_request` | No changes needed |

---

## Tool Specifications

### 1. file_read

**Purpose**: Read contents of a file from the session workspace.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "Relative path to file within workspace"
    },
    "start_line": {
      "type": "integer",
      "description": "Starting line number (1-indexed, optional)"
    },
    "end_line": {
      "type": "integer",
      "description": "Ending line number (inclusive, optional)"
    }
  },
  "required": ["path"]
}
```

**Output**: File contents as string, with line numbers if range specified.

**Example**:
```json
// Input
{"path": "report.md", "start_line": 1, "end_line": 50}

// Output
"1: # Research Report\n2: \n3: ## Introduction\n..."
```

**Security**:
- Path must be relative (no `..` traversal)
- Resolved against session workspace root
- Executed in Docker sandbox

---

### 2. file_write

**Purpose**: Create or overwrite a file in the session workspace.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "Relative path for the file"
    },
    "content": {
      "type": "string",
      "description": "Content to write to the file"
    },
    "create_dirs": {
      "type": "boolean",
      "description": "Create parent directories if needed (default: true)"
    }
  },
  "required": ["path", "content"]
}
```

**Output**: Confirmation with file path and size.

**Example**:
```json
// Input
{"path": "reports/summary.md", "content": "# Summary\n\nKey findings..."}

// Output
"Successfully wrote 45 bytes to reports/summary.md"
```

**Security**:
- Path validation (no traversal)
- File size limits (configurable, default 10MB)
- Executed in Docker sandbox

---

### 3. file_edit

**Purpose**: Make targeted edits to existing files using string replacement.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "Relative path to the file"
    },
    "old_string": {
      "type": "string",
      "description": "Exact string to find and replace"
    },
    "new_string": {
      "type": "string",
      "description": "Replacement string"
    },
    "replace_all": {
      "type": "boolean",
      "description": "Replace all occurrences (default: false, replaces first only)"
    }
  },
  "required": ["path", "old_string", "new_string"]
}
```

**Output**: Confirmation with number of replacements made.

**Example**:
```json
// Input
{
  "path": "config.json",
  "old_string": "\"debug\": false",
  "new_string": "\"debug\": true"
}

// Output
"Replaced 1 occurrence in config.json"
```

**Error Handling**:
- Error if `old_string` not found
- Error if `old_string` found multiple times and `replace_all` is false
- Returns diff preview on success

---

### 4. file_list

**Purpose**: List files in workspace matching a glob pattern.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "pattern": {
      "type": "string",
      "description": "Glob pattern (e.g., '*.md', 'src/**/*.py')"
    },
    "include_hidden": {
      "type": "boolean",
      "description": "Include hidden files (default: false)"
    }
  },
  "required": ["pattern"]
}
```

**Output**: List of matching file paths with metadata.

**Example**:
```json
// Input
{"pattern": "**/*.md"}

// Output
[
  {"path": "README.md", "size": 1234, "modified": "2026-01-06T10:30:00Z"},
  {"path": "docs/guide.md", "size": 5678, "modified": "2026-01-06T09:15:00Z"}
]
```

---

### 5. file_search

**Purpose**: Search file contents using regex pattern.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "pattern": {
      "type": "string",
      "description": "Regex pattern to search for"
    },
    "file_pattern": {
      "type": "string",
      "description": "Glob pattern for files to search (default: '**/*')"
    },
    "max_results": {
      "type": "integer",
      "description": "Maximum results to return (default: 50)"
    },
    "context_lines": {
      "type": "integer",
      "description": "Lines of context around matches (default: 2)"
    }
  },
  "required": ["pattern"]
}
```

**Output**: List of matches with file, line number, and context.

**Example**:
```json
// Input
{"pattern": "def \\w+\\(", "file_pattern": "**/*.py"}

// Output
[
  {
    "file": "utils.py",
    "line": 15,
    "match": "def calculate(",
    "context": "...\n14: # Helper function\n15: def calculate(x, y):\n16:     return x + y\n..."
  }
]
```

---

### 6. task_manager

**Purpose**: Manage a persistent task list for tracking progress on complex tasks.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": ["list", "add", "update", "complete", "remove", "clear"],
      "description": "Action to perform"
    },
    "task_id": {
      "type": "integer",
      "description": "Task ID (for update/complete/remove)"
    },
    "title": {
      "type": "string",
      "description": "Task title (for add)"
    },
    "description": {
      "type": "string",
      "description": "Task description (for add/update)"
    },
    "status": {
      "type": "string",
      "enum": ["pending", "in_progress", "completed", "blocked"],
      "description": "Task status (for update)"
    },
    "notes": {
      "type": "string",
      "description": "Notes to append (for update)"
    }
  },
  "required": ["action"]
}
```

**Output**: Current task list or confirmation of action.

**Example**:
```json
// Input - Add task
{"action": "add", "title": "Research Python frameworks", "description": "Compare Django, FastAPI, Flask"}

// Output
{
  "message": "Task #1 created",
  "tasks": [
    {"id": 1, "title": "Research Python frameworks", "status": "pending", "created": "2026-01-06T10:30:00Z"}
  ]
}

// Input - Complete task
{"action": "complete", "task_id": 1, "notes": "Completed research, FastAPI recommended"}

// Output
{
  "message": "Task #1 marked complete",
  "tasks": [
    {"id": 1, "title": "Research Python frameworks", "status": "completed", "completed_at": "2026-01-06T11:45:00Z"}
  ]
}
```

**Persistence**:
- Primary storage: Database `session_tasks` table
- Secondary: `_tasks.md` file in workspace (auto-synced)
- Task list survives context window resets

---

### 7. scratchpad

**Purpose**: Read and write working notes for intermediate thoughts and context.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": ["read", "write", "append", "clear"],
      "description": "Action to perform"
    },
    "content": {
      "type": "string",
      "description": "Content to write/append"
    },
    "section": {
      "type": "string",
      "description": "Named section to read/write (optional)"
    }
  },
  "required": ["action"]
}
```

**Output**: Current scratchpad contents or confirmation.

**Example**:
```json
// Input - Append notes
{
  "action": "append",
  "section": "research_notes",
  "content": "## FastAPI Findings\n- Modern async support\n- Auto OpenAPI docs\n- High performance"
}

// Output
"Appended 67 characters to section 'research_notes'"

// Input - Read all
{"action": "read"}

// Output
"# Scratchpad\n\n## research_notes\n\n## FastAPI Findings\n- Modern async support\n..."
```

**Persistence**:
- Primary storage: Database `session_scratchpad` table
- Secondary: `_scratchpad.md` file in workspace
- Preserved across agent turns within session

---

### 8. web_search

**Purpose**: Search the web for current information.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Search query"
    },
    "num_results": {
      "type": "integer",
      "description": "Number of results (default: 5, max: 10)"
    }
  },
  "required": ["query"]
}
```

**Output**: List of search results with title, URL, and snippet.

**Example**:
```json
// Input
{"query": "Python FastAPI vs Django 2025 comparison", "num_results": 5}

// Output
{
  "results": [
    {
      "title": "FastAPI vs Django in 2025: Complete Comparison",
      "url": "https://example.com/fastapi-vs-django",
      "snippet": "FastAPI has emerged as the go-to choice for API development..."
    },
    // ... more results
  ]
}
```

**Implementation**:
- Integrate with search API provider (Serper, Tavily, or SerpAPI)
- Requires `SEARCH_API_KEY` environment variable
- Graceful error if API not configured

**Provider Configuration** (in Settings):
```json
{
  "search_provider": "serper",  // or "tavily", "serpapi"
  "search_api_key": "encrypted_key"
}
```

---

### 9. web_fetch

**Purpose**: Fetch and extract content from a URL.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "url": {
      "type": "string",
      "description": "URL to fetch"
    },
    "extract_mode": {
      "type": "string",
      "enum": ["text", "markdown", "html", "raw"],
      "description": "Content extraction mode (default: markdown)"
    },
    "max_length": {
      "type": "integer",
      "description": "Maximum content length (default: 50000 chars)"
    }
  },
  "required": ["url"]
}
```

**Output**: Extracted content from the URL.

**Example**:
```json
// Input
{"url": "https://docs.python.org/3/library/asyncio.html", "extract_mode": "markdown"}

// Output
{
  "url": "https://docs.python.org/3/library/asyncio.html",
  "title": "asyncio - Asynchronous I/O",
  "content": "# asyncio - Asynchronous I/O\n\nasyncio is a library to write concurrent code...",
  "word_count": 2500
}
```

**Implementation**:
- Use httpx for fetching
- Use trafilatura or similar for content extraction
- Respect robots.txt
- Timeout: 30 seconds
- Handle redirects gracefully

---

## Database Schema Changes

### New Tables

```sql
-- Session workspace metadata
CREATE TABLE session_workspaces (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    workspace_path VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    total_size_bytes BIGINT DEFAULT 0,
    file_count INTEGER DEFAULT 0,
    UNIQUE(session_id)
);

-- Task manager storage
CREATE TABLE session_tasks (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    task_number INTEGER NOT NULL,  -- Per-session task ID
    title VARCHAR(500) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    UNIQUE(session_id, task_number)
);

-- Scratchpad storage
CREATE TABLE session_scratchpads (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    section VARCHAR(100) DEFAULT 'default',
    content TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(session_id, section)
);

-- Search provider configuration
CREATE TABLE search_provider_configs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    provider_type VARCHAR(50) NOT NULL,  -- 'serper', 'tavily', 'serpapi'
    api_key_encrypted VARCHAR(500) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id)
);
```

---

## Security Model

### Docker Sandbox Architecture

All file operations execute within the existing Docker sandbox:

```
┌─────────────────────────────────────────────────────────┐
│                    HOST SYSTEM                          │
│                                                         │
│   ┌─────────────────────────────────────────────────┐  │
│   │              DOCKER SANDBOX                      │  │
│   │                                                  │  │
│   │   /workspace/{session_id}/  ← Volume mount      │  │
│   │       ├── _tasks.md                             │  │
│   │       ├── _scratchpad.md                        │  │
│   │       └── {user_files}/                         │  │
│   │                                                  │  │
│   │   - No network access (except web tools)        │  │
│   │   - No access outside /workspace                │  │
│   │   - Resource limits (CPU, memory, time)         │  │
│   │   - Non-root user                               │  │
│   │                                                  │  │
│   └─────────────────────────────────────────────────┘  │
│                                                         │
│   /var/lib/deepagent/workspaces/  ← Host storage       │
│       └── {session_id}/                                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Security Constraints

| Constraint | Implementation |
|------------|----------------|
| Path traversal | Validate relative paths, reject `..` |
| File size | Max 10MB per file, 100MB per workspace |
| Execution time | 60 second timeout per tool call |
| Network | Disabled for file tools, allowed for web tools |
| Permissions | Non-root user, workspace directory only |

---

## Power Agent Configuration

### Default Agent Definition

```json
{
  "name": "Research & Execute Agent",
  "description": "An autonomous agent capable of research, planning, code execution, and file management. Ideal for complex multi-step tasks.",
  "agent_type": "react",
  "is_builtin": true,
  "config": {
    "llm_config": {
      "provider": "openai",
      "model": "gpt-4o",
      "temperature": 0.7,
      "max_tokens": 4096
    },
    "tool_ids": [
      "file_read",
      "file_write",
      "file_edit",
      "file_list",
      "file_search",
      "task_manager",
      "scratchpad",
      "web_search",
      "web_fetch",
      "python_code_execution",
      "http_request"
    ],
    "system_prompt": "SEE BELOW",
    "timeout_seconds": 300,
    "max_iterations": 50
  }
}
```

### System Prompt

```markdown
You are an autonomous research and execution agent with access to file operations, web research, code execution, and task management tools.

## Your Workflow

Follow this systematic approach for complex tasks:

### 1. PLAN
- Break down the task into clear, actionable steps
- Use `task_manager` to create a task list
- Identify what information you need to gather

### 2. RESEARCH
- Use `web_search` to find relevant information
- Use `web_fetch` to read detailed content from URLs
- Take notes using `scratchpad` to preserve important findings

### 3. EXECUTE
- Work through tasks one at a time
- Use `file_write` to create outputs
- Use `python_code_execution` for calculations, data processing, or analysis
- Use `file_edit` for targeted modifications

### 4. VERIFY
- Review your work before marking tasks complete
- Test code outputs when possible
- Update task status with notes on what was accomplished

### 5. DOCUMENT
- Keep your scratchpad updated with key findings
- Write clear, well-structured output files
- Summarize results when completing the overall task

## Best Practices

- **Be methodical**: Complete one task fully before moving to the next
- **Preserve context**: Use scratchpad liberally to maintain continuity
- **Verify work**: Don't assume - check that files were created correctly
- **Handle errors gracefully**: If something fails, note it and try an alternative approach
- **Ask for clarification**: If requirements are ambiguous, ask before proceeding

## File Organization

Your workspace is at `/workspace/`. Organize outputs logically:
- `reports/` - Final reports and documentation
- `data/` - Data files and analysis outputs
- `scripts/` - Generated code and scripts
- `research/` - Research notes and references

## Important Notes

- All file paths are relative to your workspace
- Your task list and scratchpad persist across conversation turns
- Web search requires an API key to be configured
- Code execution runs in a sandboxed environment
```

---

## Demo Scenarios

### Scenario 1: Research Report

**Prompt**: "Research the top 3 Python web frameworks in 2025, compare their pros/cons, and write a detailed report to `reports/framework_comparison.md`"

**Expected Behavior**:
1. Create tasks: Research Django, Research FastAPI, Research Flask, Write comparison, Write report
2. Use web_search for each framework
3. Use web_fetch to read detailed documentation
4. Take notes in scratchpad
5. Use python_code_execution to create comparison table
6. Write final report with file_write

### Scenario 2: Data Analysis

**Prompt**: "Analyze the attached sales data, identify trends, create visualizations, and summarize findings"

**Expected Behavior**:
1. Read data file with file_read
2. Create analysis tasks
3. Use python_code_execution with pandas/matplotlib
4. Write visualizations to workspace
5. Create summary report

### Scenario 3: Code Generation

**Prompt**: "Create a Python CLI tool that monitors a URL for changes and sends notifications. Include tests and documentation."

**Expected Behavior**:
1. Plan project structure
2. Research best practices with web_search
3. Write main script with file_write
4. Write tests
5. Write README documentation
6. Verify with python_code_execution

---

## Implementation Phases

### Phase 1: Core Infrastructure (P0)

**Duration**: 1-2 weeks

| Task | Description |
|------|-------------|
| Workspace service | Create/manage session workspace directories |
| Database migrations | Add new tables for tasks, scratchpad, workspaces |
| Sandbox integration | Extend Docker sandbox for file operations |
| Base tool framework | Common validation, error handling, logging |

**Deliverables**:
- `WorkspaceService` class
- Database migrations
- Updated `SandboxService` with file operation support

### Phase 2: File Operation Tools (P0)

**Duration**: 1 week

| Task | Description |
|------|-------------|
| `file_read` | Implement with line range support |
| `file_write` | Implement with directory creation |
| `file_edit` | Implement string replacement |
| Unit tests | Full test coverage |

**Deliverables**:
- 3 new built-in tools
- Tool tests
- API integration

### Phase 3: Planning Tools (P0)

**Duration**: 1 week

| Task | Description |
|------|-------------|
| `task_manager` | Implement with DB + file sync |
| `scratchpad` | Implement with sections |
| Sync logic | Auto-sync DB ↔ workspace files |
| Unit tests | Full test coverage |

**Deliverables**:
- 2 new built-in tools
- Sync service
- Tool tests

### Phase 4: Discovery Tools (P1)

**Duration**: 3-4 days

| Task | Description |
|------|-------------|
| `file_list` | Implement glob matching |
| `file_search` | Implement regex search |
| Unit tests | Full test coverage |

**Deliverables**:
- 2 new built-in tools
- Tool tests

### Phase 5: Web Tools (P1)

**Duration**: 1 week

| Task | Description |
|------|-------------|
| Search provider config | Settings UI, encrypted storage |
| `web_search` | Implement with Serper/Tavily |
| `web_fetch` | Implement with content extraction |
| Unit tests | Full test coverage |

**Deliverables**:
- Search provider configuration in Settings
- 2 new built-in tools
- Tool tests

### Phase 6: Power Agent & Demos (P2)

**Duration**: 3-4 days

| Task | Description |
|------|-------------|
| Power Agent | Create default agent configuration |
| Demo scenarios | Create example prompts |
| Documentation | Update README, create usage guide |
| Integration tests | End-to-end agent tests |

**Deliverables**:
- Default "Research & Execute Agent"
- Demo scenario library
- Updated documentation

---

## API Endpoints

### New Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/sessions/{id}/workspace` | Get workspace info |
| GET | `/api/v1/sessions/{id}/workspace/files` | List workspace files |
| GET | `/api/v1/sessions/{id}/tasks` | Get task list |
| GET | `/api/v1/sessions/{id}/scratchpad` | Get scratchpad contents |
| POST | `/api/v1/search-providers` | Configure search provider |
| GET | `/api/v1/search-providers` | Get search provider config |
| POST | `/api/v1/search-providers/test` | Test search provider |

---

## Frontend Changes

### Settings Page

Add "Search Provider" section:
- Provider type dropdown (Serper, Tavily, SerpAPI)
- API key input (encrypted)
- Test connection button

### Session Detail Dialog

Add "Workspace" tab:
- File tree view
- Download files
- View task list
- View scratchpad

### Playground

- Show workspace files panel (collapsible)
- Display task progress indicator
- Show scratchpad preview

---

## Configuration

### Environment Variables

```bash
# Workspace configuration
WORKSPACE_BASE_PATH=/var/lib/deepagent/workspaces
WORKSPACE_MAX_SIZE_MB=100
WORKSPACE_FILE_MAX_SIZE_MB=10

# Search provider (optional, can be configured per-user in UI)
DEFAULT_SEARCH_PROVIDER=serper
DEFAULT_SEARCH_API_KEY=your_key_here

# Sandbox configuration
SANDBOX_TIMEOUT_SECONDS=60
SANDBOX_MEMORY_LIMIT_MB=512
```

---

## Success Criteria

### Functional Requirements

- [ ] All 9 new tools implemented and tested
- [ ] Tools execute in Docker sandbox
- [ ] Task manager persists across turns
- [ ] Scratchpad syncs to workspace files
- [ ] Web search returns real results
- [ ] Power Agent can complete demo scenarios

### Performance Requirements

- [ ] File operations complete in < 1 second
- [ ] Web search returns in < 5 seconds
- [ ] Workspace initialization < 500ms

### Security Requirements

- [ ] No path traversal vulnerabilities
- [ ] File size limits enforced
- [ ] Sandbox isolation verified
- [ ] API keys encrypted at rest

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Sandbox escape | High | Security audit, limit syscalls, regular updates |
| Search API costs | Medium | Rate limiting, usage tracking, cost alerts |
| Large workspaces | Medium | Size limits, cleanup policies, monitoring |
| Tool abuse | Medium | Rate limiting, logging, anomaly detection |

---

## Future Enhancements

Post-MVP features to consider:

1. **Workspace Templates**: Pre-configured workspace structures for common tasks
2. **Tool Composition**: Allow tools to call other tools
3. **Workspace Sharing**: Share workspace between sessions
4. **Version Control**: Git integration for workspace files
5. **Collaborative Editing**: Multiple agents working on same workspace
6. **Custom Tool Builder**: UI for creating new tools without code

---

## References

- [Anthropic - Building Agents with Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
- [Anthropic - Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Anthropic - Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Anthropic - Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [LangChain/LangGraph 1.0](https://blog.langchain.com/langchain-langgraph-1dot0/)
- [LangGraph ReAct Agent Guide](https://langchain-ai.github.io/langgraph/how-tos/react-agent-from-scratch/)
