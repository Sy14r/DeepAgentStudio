# DeepAgentStudio MCP Server Design

**Date:** 2026-01-18
**Status:** Approved
**Branch:** `mcp-server`

## Overview

An embedded MCP server that exposes DeepAgentStudio's configuration capabilities, enabling agents to self-improve, create tools, spawn new agents, and enhance evaluations programmatically.

### Goals

1. **Agent self-improvement**: Agents modify their own prompts, configurations, and tool assignments based on performance analysis
2. **Tool creation**: Agents identify capability gaps and create custom tools to fill them
3. **Agent spawning**: Meta-agents design and create specialized child agents for subtasks
4. **Evaluation enhancement**: Agents add edge cases and examples to evaluation datasets

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    External Agents                          │
│        (Claude, other MCP clients, DeepAgentStudio agents)  │
└─────────────────────┬───────────────────────────────────────┘
                      │ SSE/HTTP Transport
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI Backend                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              MCP Server Module                         │  │
│  │  /api/v1/mcp/sse  ←── SSE endpoint                    │  │
│  │                                                        │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │  │
│  │  │ Auth Layer  │→ │ Permission  │→ │ Tool Router  │  │  │
│  │  │(Session JWT)│  │   Checker   │  │              │  │  │
│  │  └─────────────┘  └─────────────┘  └──────────────┘  │  │
│  │                                           │           │  │
│  │         ┌─────────────────────────────────┼───────┐  │  │
│  │         ▼              ▼              ▼   ▼       │  │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ...   │  │  │
│  │  │  Agent   │  │   Tool   │  │  Prompt  │        │  │  │
│  │  │  Tools   │  │  Tools   │  │  Tools   │        │  │  │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘        │  │  │
│  └───────┼─────────────┼─────────────┼──────────────┘  │  │
│          ▼             ▼             ▼                  │  │
│  ┌─────────────────────────────────────────────────────┐│  │
│  │           Existing Services Layer                   ││  │
│  │  AgentService, ToolService, PromptService, etc.     ││  │
│  └─────────────────────────────────────────────────────┘│  │
└─────────────────────────────────────────────────────────────┘
```

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Deployment | Embedded in FastAPI | Direct access to services, no extra infrastructure |
| Transport | SSE via `/api/v1/mcp/sse` | Works for remote agents, well-supported by MCP SDK |
| Protocol | MCP Python SDK | Handles JSON-RPC, capability negotiation, streaming |
| Auth model | Session-scoped + Agent-scoped | User JWT provides base isolation, agent permissions add granularity |

## Permission System

### Two-Layer Authorization

1. **Session-scoped (base layer)**: All operations filtered by `user_id` from JWT. Agents can never access other users' resources.

2. **Agent-scoped (permission layer)**: Each agent has a permission preset defining what actions it can perform.

### Permission Presets

| Preset | Permissions | Use Case |
|--------|-------------|----------|
| **Observer** | Read-only across all resources | Analysis agents that report but don't modify |
| **Self-Improve** | Observer + update own config, create prompts, add eval examples | Agents that tune themselves based on performance |
| **Tool Creator** | Self-Improve + create/update tools | Agents that build missing capabilities |
| **Meta-Agent** | Full CRUD on all resources | Orchestrators that design and spawn agents |
| **Custom** | User-defined permission list | Advanced use cases |

### Permission Format

Resource:action pattern with wildcards:

```
agents:list          # List agents
agents:read          # Read any agent
agents:update:self   # Update only own agent
agents:update:*      # Update any agent (owned by user)
agents:*             # All agent operations
tools:create         # Create tools
datasets:update:examples  # Add examples to datasets
```

### Database Model

```sql
CREATE TYPE permission_preset AS ENUM (
    'observer', 'self_improve', 'tool_creator', 'meta_agent', 'custom'
);

CREATE TABLE agent_permissions (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER UNIQUE NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    preset permission_preset NOT NULL DEFAULT 'observer',
    custom_permissions JSONB,  -- Only used when preset='custom'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## MCP Tools

### Tool Inventory (~30 tools)

#### Agents Namespace (`deepagent_agents_*`)

| Tool | Permission | Description |
|------|------------|-------------|
| `list` | `agents:list` | List agents with optional search/filter |
| `get` | `agents:read` | Get agent details including current config |
| `create` | `agents:create` | Create new agent with initial config |
| `update` | `agents:update:*` | Update agent config (creates new version) |
| `clone` | `agents:create` | Clone existing agent |
| `delete` | `agents:delete` | Delete agent |
| `assign_tools` | `agents:update:*` | Assign tools to agent |
| `assign_mcp_servers` | `agents:update:*` | Assign MCP servers to agent |

#### Tools Namespace (`deepagent_tools_*`)

| Tool | Permission | Description |
|------|------------|-------------|
| `list` | `tools:list` | List available tools (built-in and custom) |
| `get` | `tools:read` | Get tool details including input/output schema |
| `create` | `tools:create` | Create custom tool from Python code |
| `update` | `tools:update:*` | Update tool code or schema |
| `generate_schema` | `tools:generate_schema` | Generate JSON schema from Python function |

#### Prompts Namespace (`deepagent_prompts_*`)

| Tool | Permission | Description |
|------|------------|-------------|
| `list` | `prompts:list` | List prompt templates |
| `get` | `prompts:read` | Get prompt with extracted variables |
| `create` | `prompts:create` | Create new prompt template |
| `update` | `prompts:update:*` | Update prompt (creates new version) |
| `render` | `prompts:read` | Render prompt with variable substitution |

#### Datasets Namespace (`deepagent_datasets_*`)

| Tool | Permission | Description |
|------|------------|-------------|
| `list` | `datasets:list` | List evaluation datasets |
| `get` | `datasets:read` | Get dataset with examples |
| `create` | `datasets:create` | Create new dataset with schema |
| `add_example` | `datasets:update:examples` | Add example to dataset |
| `remove_example` | `datasets:update:*` | Remove example from dataset |

#### Evaluations Namespace (`deepagent_evaluations_*`)

| Tool | Permission | Description |
|------|------------|-------------|
| `list_evaluators` | `evaluations:list` | List available evaluator types |
| `list_runs` | `evaluations:list` | List evaluation runs for a dataset/agent |
| `run` | `evaluations:create` | Start an evaluation run |
| `get_results` | `evaluations:read` | Get detailed evaluation results |

#### Introspection Namespace (`deepagent_introspect_*`)

| Tool | Permission | Description |
|------|------------|-------------|
| `whoami` | (always allowed) | Get current agent info and effective permissions |
| `get_session` | `sessions:read:own` | Get current session details |
| `get_traces` | `sessions:read:own` | Get execution traces for session |
| `list_my_versions` | `agents:read` | List own agent's version history |

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "permission_denied",
    "message": "Permission denied for action: agents:create",
    "details": {
      "action": "agents:create",
      "resource": null
    }
  }
}
```

### Error Codes

| Code | HTTP Equivalent | Description |
|------|-----------------|-------------|
| `permission_denied` | 403 | Agent lacks required permission |
| `not_found` | 404 | Resource doesn't exist or not owned by user |
| `validation_error` | 400 | Invalid input parameters |
| `conflict` | 409 | Resource already exists (e.g., duplicate name) |
| `internal_error` | 500 | Unexpected server error |

## Security

### Measures

| Concern | Mitigation |
|---------|------------|
| User isolation | All queries filter by `user_id` from JWT |
| Permission escalation | Agents cannot modify their own permissions |
| Tool code injection | Uses existing `validate_function_code` sandbox |
| Audit trail | All MCP tool invocations logged with agent_id, action, result |

### Audit Log Model

```sql
CREATE TABLE mcp_audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    agent_id INTEGER REFERENCES agents(id),
    session_id INTEGER REFERENCES sessions(id),
    tool_name VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    success BOOLEAN NOT NULL,
    error_code VARCHAR(50),
    request_summary JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ix_mcp_audit_logs_user_id ON mcp_audit_logs(user_id);
CREATE INDEX ix_mcp_audit_logs_agent_id ON mcp_audit_logs(agent_id);
CREATE INDEX ix_mcp_audit_logs_created_at ON mcp_audit_logs(created_at);
```

## File Structure

### Backend

```
backend/app/
├── mcp_server/
│   ├── __init__.py
│   ├── server.py              # MCP server setup, tool registration
│   ├── auth.py                # JWT extraction, permission checking
│   ├── permissions.py         # Permission definitions, presets, resolution
│   ├── context.py             # Request context (user_id, agent_id, db)
│   ├── errors.py              # MCP error classes
│   └── tools/
│       ├── __init__.py        # Tool registration
│       ├── agents.py          # Agent CRUD tools
│       ├── tools.py           # Tool management tools
│       ├── prompts.py         # Prompt management tools
│       ├── datasets.py        # Dataset management tools
│       ├── evaluations.py     # Evaluation tools
│       └── introspect.py      # Self-awareness tools
├── models/
│   ├── agent_permission.py    # AgentPermission model
│   └── mcp_audit_log.py       # MCPAuditLog model
├── schemas/
│   └── agent_permission.py    # Pydantic schemas
└── api/v1/
    └── mcp.py                 # FastAPI route for MCP SSE endpoint
```

### Frontend

```
frontend/src/
├── api/
│   ├── hooks/
│   │   └── useAgentPermissions.ts   # React Query hooks
│   └── types.ts                      # Permission types added
└── components/
    └── agents/
        └── AgentPermissionsPanel.tsx # Permission editor UI
```

### Database Migrations

```
alembic/versions/
└── xxxx_add_mcp_server_tables.py    # agent_permissions, mcp_audit_logs
```

## Frontend Integration

### Permission Editor UI

Located in Agent Editor page as a new tab/section:

- Dropdown to select permission preset
- Visual display of effective permissions (checkmarks/x marks)
- "Advanced" toggle to customize individual permissions
- MCP connection info with copyable config for Claude Desktop

### API Endpoints for Permissions

```
GET  /api/v1/agents/{agent_id}/permissions
PUT  /api/v1/agents/{agent_id}/permissions
```

## Implementation Order

1. **Phase 1: Foundation**
   - Database models and migration
   - Permission system (definitions, resolution, checking)
   - MCP server skeleton with auth

2. **Phase 2: Core Tools**
   - Introspection tools (whoami, get_session)
   - Agent tools (list, get, update)
   - Tool tools (list, get, create)

3. **Phase 3: Extended Tools**
   - Prompt tools
   - Dataset tools
   - Evaluation tools
   - Remaining agent tools (create, clone, delete)

4. **Phase 4: Frontend**
   - Permission management UI
   - MCP connection info display

5. **Phase 5: Testing & Polish**
   - Integration tests
   - Audit logging
   - Documentation

## Dependencies

### New Python Package

```
mcp>=1.0.0  # Anthropic MCP SDK
```

## Open Questions

None - design approved for implementation.
