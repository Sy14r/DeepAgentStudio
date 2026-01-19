# DeepAgentStudio MCP Server API Documentation

**Version:** 1.0.0
**Base URL:** `/api/v1/mcp`

## Overview

The MCP (Model Context Protocol) server enables external agents to programmatically interact with DeepAgentStudio. This allows agents to:

- **Self-improve**: Modify their own prompts and configurations
- **Create tools**: Build new capabilities when gaps are identified
- **Spawn agents**: Design and create specialized child agents
- **Enhance evaluations**: Add examples and edge cases to datasets

## Authentication

All MCP endpoints require JWT authentication via Bearer token:

```bash
curl -H "Authorization: Bearer <your-token>" http://localhost:8000/api/v1/mcp/capabilities
```

## Endpoints

### Server Capabilities

```
GET /api/v1/mcp/capabilities
```

Returns server information and capabilities.

**Response:**
```json
{
  "protocolVersion": "2024-11-05",
  "capabilities": {
    "tools": { "listChanged": false }
  },
  "serverInfo": {
    "name": "deepagent-studio",
    "version": "1.0.0"
  },
  "toolCount": 39
}
```

### List Available Tools

```
GET /api/v1/mcp/tools
```

Returns all tools available to the authenticated user.

**Response:**
```json
{
  "tools": [
    {
      "name": "agents_list",
      "description": "List all agents accessible to the user.",
      "inputSchema": { ... }
    }
  ],
  "total": 39
}
```

### Execute Tool

```
POST /api/v1/mcp/tools/{tool_name}
```

Execute a specific MCP tool.

**Request Body:**
```json
{
  "name": "agents_list",
  "arguments": {
    "limit": 10
  }
}
```

**Response:**
```json
{
  "success": true,
  "content": [
    {
      "type": "text",
      "text": "{'total': 3, 'agents': [...]}"
    }
  ]
}
```

### SSE Endpoint

```
GET /api/v1/mcp/sse
```

Server-Sent Events endpoint for MCP protocol communication.

---

## Tools Reference

### Agents Namespace (10 tools)

#### `agents_list`
List all agents accessible to the user.

**Permission:** `agents:list`

**Arguments:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `include_inactive` | boolean | No | false | Include inactive agents |
| `agent_type_id` | integer | No | - | Filter by agent type ID |
| `limit` | integer | No | 50 | Max results (1-100) |
| `offset` | integer | No | 0 | Pagination offset |

---

#### `agents_read`
Get detailed information about a specific agent.

**Permission:** `agents:read`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `agent_id` | integer | Yes | ID of the agent |

---

#### `agents_create`
Create a new agent with the specified configuration.

**Permission:** `agents:create`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | Yes | Name of the agent (1-100 chars) |
| `description` | string | No | Description |
| `agent_type_id` | integer | Yes | Agent type ID |
| `tags` | array[string] | No | Tags for categorization |
| `config` | object | Yes | Agent configuration (LLM settings) |

---

#### `agents_update`
Update an existing agent's configuration. Creates a new version.

**Permission:** `agents:update:self` (own agent) or `agents:update:*` (any agent)

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `agent_id` | integer | Yes | ID of the agent |
| `name` | string | No | New name |
| `description` | string | No | New description |
| `tags` | array[string] | No | New tags |
| `config` | object | No | New configuration |

---

#### `agents_delete`
Delete an agent (soft delete by default).

**Permission:** `agents:delete`

**Arguments:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `agent_id` | integer | Yes | - | ID of the agent |
| `hard_delete` | boolean | No | false | Permanently delete |

---

#### `agents_clone`
Clone an existing agent to create an editable copy.

**Permission:** `agents:create`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `agent_id` | integer | Yes | ID of the agent to clone |
| `new_name` | string | No | Name for the cloned agent |

---

#### `agents_assign_tools`
Assign tools to an agent. Replaces existing tool assignments.

**Permission:** `agents:update:tools`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `agent_id` | integer | Yes | ID of the agent |
| `tool_ids` | array[integer] | Yes | Tool IDs to assign |

---

#### `agents_assign_mcp_servers`
Assign MCP servers to an agent. Replaces existing server assignments.

**Permission:** `agents:update:mcp_servers`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `agent_id` | integer | Yes | ID of the agent |
| `mcp_server_ids` | array[integer] | Yes | MCP server IDs to assign |

---

#### `agents_get_tools`
Get the list of tools assigned to an agent.

**Permission:** `agents:read`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `agent_id` | integer | Yes | ID of the agent |

---

#### `agents_list_versions`
List version history for an agent.

**Permission:** `agents:read`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `agent_id` | integer | No | Agent ID (defaults to current agent) |
| `limit` | integer | No | Max versions (default 20) |

---

### Tools Namespace (5 tools)

#### `tools_list`
List all tools accessible to the user.

**Permission:** `tools:list`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `tool_type` | string | No | Filter: "builtin" or "custom" |
| `category` | string | No | Filter by category |
| `limit` | integer | No | Max results (default 50) |
| `offset` | integer | No | Pagination offset |

---

#### `tools_read`
Get detailed information about a specific tool.

**Permission:** `tools:read`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `tool_id` | integer | Yes | ID of the tool |

---

#### `tools_create`
Create a new custom tool.

**Permission:** `tools:create`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | Yes | Tool name (1-100 chars) |
| `description` | string | Yes | Tool description |
| `category` | string | No | Category (web, file, code, etc.) |
| `implementation` | string | Yes | Python code |
| `config_schema` | object | No | JSON Schema for config |
| `default_config` | object | No | Default config values |

---

#### `tools_update`
Update an existing custom tool.

**Permission:** `tools:update`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `tool_id` | integer | Yes | ID of the tool |
| `name` | string | No | New name |
| `description` | string | No | New description |
| `implementation` | string | No | New implementation |
| `config_schema` | object | No | New config schema |
| `default_config` | object | No | New default config |
| `is_active` | boolean | No | Active status |

---

#### `tools_delete`
Delete a custom tool.

**Permission:** `tools:delete`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `tool_id` | integer | Yes | ID of the tool |

---

### Prompts Namespace (6 tools)

#### `prompts_list`
List all prompts accessible to the user.

**Permission:** `prompts:list`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `use_case` | string | No | Filter by use case |
| `limit` | integer | No | Max results (default 50) |
| `offset` | integer | No | Pagination offset |

---

#### `prompts_read`
Get detailed information about a specific prompt.

**Permission:** `prompts:read`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `prompt_id` | integer | Yes | ID of the prompt |

---

#### `prompts_create`
Create a new prompt.

**Permission:** `prompts:create`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | Yes | Prompt name |
| `content` | string | Yes | Prompt content/template |
| `description` | string | No | Description |
| `use_case` | string | No | Use case |
| `message_type` | string | No | "system", "human", or "ai" |

---

#### `prompts_update`
Update an existing prompt. Creates a new version.

**Permission:** `prompts:update`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `prompt_id` | integer | Yes | ID of the prompt |
| `name` | string | No | New name |
| `description` | string | No | New description |
| `content` | string | No | New content (creates version) |

---

#### `prompts_render`
Render a prompt template with provided variables.

**Permission:** `prompts:read`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `prompt_id` | integer | Yes | ID of the prompt |
| `variables` | object | No | Variables to substitute |

**Example:**
```json
{
  "prompt_id": 1,
  "variables": {
    "name": "John",
    "task": "summarize documents"
  }
}
```

---

#### `prompts_clone`
Clone a prompt to create an editable copy.

**Permission:** `prompts:create`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `prompt_id` | integer | Yes | ID to clone |
| `new_name` | string | No | Name for clone |

---

### Datasets Namespace (7 tools)

#### `datasets_list`
List all evaluation datasets.

**Permission:** `datasets:list`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `limit` | integer | No | Max results (default 50) |
| `offset` | integer | No | Pagination offset |

---

#### `datasets_read`
Get detailed information about a dataset including examples.

**Permission:** `datasets:read`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `dataset_id` | integer | Yes | ID of the dataset |
| `include_examples` | boolean | No | Include examples (default true) |
| `example_limit` | integer | No | Max examples (default 100) |

---

#### `datasets_create`
Create a new evaluation dataset.

**Permission:** `datasets:create`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | Yes | Dataset name |
| `description` | string | No | Description |
| `input_schema` | object | No | JSON schema for inputs |
| `output_schema` | object | No | JSON schema for outputs |

---

#### `datasets_add_example`
Add a new example to a dataset.

**Permission:** `datasets:update:examples`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `dataset_id` | integer | Yes | ID of the dataset |
| `input_data` | object | Yes | Input data |
| `expected_output` | object | No | Expected output |
| `tags` | array[string] | No | Tags for the example |

---

#### `datasets_remove_example`
Remove an example from a dataset.

**Permission:** `datasets:update:examples`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `dataset_id` | integer | Yes | ID of the dataset |
| `example_id` | integer | Yes | ID of the example |

---

#### `datasets_update`
Update a dataset's metadata.

**Permission:** `datasets:update`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `dataset_id` | integer | Yes | ID of the dataset |
| `name` | string | No | New name |
| `description` | string | No | New description |
| `input_schema` | object | No | New input schema |
| `output_schema` | object | No | New output schema |

---

#### `datasets_update_example`
Update an existing example in a dataset.

**Permission:** `datasets:update:examples`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `dataset_id` | integer | Yes | ID of the dataset |
| `example_id` | integer | Yes | ID of the example |
| `input_data` | object | No | New input data |
| `expected_output` | object | No | New expected output |
| `tags` | array[string] | No | New tags |

---

### Evaluations Namespace (7 tools)

#### `evaluations_list`
List all evaluations.

**Permission:** `evaluations:list`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `limit` | integer | No | Max results (default 50) |
| `offset` | integer | No | Pagination offset |

---

#### `evaluations_read`
Get detailed information about an evaluation.

**Permission:** `evaluations:read`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `evaluation_id` | integer | Yes | ID of the evaluation |
| `include_runs` | boolean | No | Include recent runs (default true) |
| `run_limit` | integer | No | Max runs (default 10) |

---

#### `evaluators_list`
List all available evaluators.

**Permission:** `evaluations:list`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `category` | string | No | Filter by category |
| `limit` | integer | No | Max results (default 50) |

---

#### `evaluations_create`
Create a new evaluation configuration.

**Permission:** `evaluations:create`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | Yes | Evaluation name |
| `agent_id` | integer | Yes | Agent to evaluate |
| `dataset_id` | integer | Yes | Dataset to use |
| `description` | string | No | Description |
| `config` | object | No | Evaluation config |

---

#### `evaluations_run`
Start an evaluation run.

**Permission:** `evaluations:run`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `evaluation_id` | integer | Yes | ID of the evaluation |
| `llm_provider_id` | integer | No | LLM provider for evaluators |

---

#### `evaluations_get_run`
Get details about a specific evaluation run.

**Permission:** `evaluations:read`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `run_id` | integer | Yes | ID of the run |
| `include_results` | boolean | No | Include results (default true) |
| `result_limit` | integer | No | Max results (default 50) |

---

#### `evaluations_list_runs`
List evaluation runs for an evaluation.

**Permission:** `evaluations:read`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `evaluation_id` | integer | Yes | ID of the evaluation |
| `limit` | integer | No | Max results (default 20) |
| `offset` | integer | No | Pagination offset |

---

### Introspection & Sessions Namespace (4 tools)

#### `introspect_whoami`
Get current agent info and effective permissions.

**Permission:** Always allowed

**Arguments:** None

**Response includes:**
- `user_id`: Current user ID
- `agent_id`: Current agent ID (if called from agent context)
- `session_id`: Current session ID (if in session)
- `is_direct_user_call`: Whether this is a direct API call vs agent call
- `effective_permissions`: List of permissions

---

#### `sessions_get_current`
Get details about the current session.

**Permission:** `sessions:read:own`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `include_messages` | boolean | No | Include message history (default true) |
| `message_limit` | integer | No | Max messages (default 50) |

---

#### `sessions_list`
List sessions for the current user.

**Permission:** `sessions:list`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `agent_id` | integer | No | Filter by agent |
| `status` | string | No | Filter by status |
| `limit` | integer | No | Max results (default 20) |
| `offset` | integer | No | Pagination offset |

---

#### `sessions_get_traces`
Get execution traces for a session.

**Permission:** `sessions:read:own`

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `session_id` | integer | No | Session ID (defaults to current) |
| `limit` | integer | No | Max trace steps (default 100) |

---

## Permission System

### Permission Presets

| Preset | Description | Typical Permissions |
|--------|-------------|---------------------|
| **observer** | Read-only access | `*:list`, `*:read` |
| **self_improve** | Can modify own config | Observer + `agents:update:self`, `prompts:create`, `datasets:update:examples` |
| **tool_creator** | Can create tools | Self-improve + `tools:create`, `tools:update` |
| **meta_agent** | Full access | All permissions |
| **custom** | User-defined | Specified list |

### Permission Format

```
resource:action[:scope]
```

Examples:
- `agents:list` - List agents
- `agents:read` - Read any agent
- `agents:update:self` - Update only own agent
- `agents:update:*` - Update any owned agent
- `tools:*` - All tool operations
- `*` - Full access (direct user calls)

---

## Error Handling

### Error Response Format

```json
{
  "success": false,
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

| Code | Description |
|------|-------------|
| `permission_denied` | Agent lacks required permission |
| `not_found` | Resource doesn't exist or not owned |
| `validation_error` | Invalid input parameters |
| `rate_limit_exceeded` | Too many requests |
| `internal_error` | Unexpected server error |

---

## Usage Examples

### List Agents with curl

```bash
# Get auth token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=testuser2026&password=TestPassword123!" \
  | jq -r '.access_token')

# List agents
curl -s -X POST "http://localhost:8000/api/v1/mcp/tools/agents_list" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"agents_list","arguments":{"limit":5}}'
```

### Create a Tool

```bash
curl -s -X POST "http://localhost:8000/api/v1/mcp/tools/tools_create" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "tools_create",
    "arguments": {
      "name": "my_custom_tool",
      "description": "A custom tool that does something useful",
      "implementation": "def run(input_data):\n    return {\"result\": input_data[\"value\"] * 2}"
    }
  }'
```

### Render a Prompt

```bash
curl -s -X POST "http://localhost:8000/api/v1/mcp/tools/prompts_render" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "prompts_render",
    "arguments": {
      "prompt_id": 1,
      "variables": {
        "user_name": "Alice",
        "task": "analyze sales data"
      }
    }
  }'
```

---

## Integration with Claude Desktop

Add to your Claude Desktop config:

```json
{
  "mcpServers": {
    "deepagent-studio": {
      "url": "http://localhost:8000/api/v1/mcp/sse",
      "headers": {
        "Authorization": "Bearer <your-token>"
      }
    }
  }
}
```

---

## Changelog

### v1.0.0 (2026-01-18)
- Initial release with 39 tools
- Agents, Tools, Prompts, Datasets, Evaluations, and Introspection namespaces
- Permission-based access control with presets
- SSE and direct HTTP endpoints
