# DeepAgentStudio

A comprehensive web application for building, managing, and interacting with LangChain deepagents.

## Overview

DeepAgentStudio provides developers and AI/ML engineers with a complete platform for agent development, including:

- **Agent Catalog**: Create, version, and manage AI agents with different architectures (ReAct, Plan-and-Execute, Conversational)
- **Tool Library**: Built-in tools (Python Code Execution, HTTP Requests) plus custom tool builder with Monaco code editor
- **MCP Server Integration**: Connect to Model Context Protocol servers to extend agent capabilities with external tools
- **Prompt Management**: Template library with variable substitution, versioning, and A/B testing
- **Interactive Playground**: Chat interface with WebSocket streaming and real-time trace visualization
- **Session Recording**: Complete conversation history, execution traces, and performance metrics
- **LLM Provider Integration**: Support for OpenAI, Anthropic, Google, Azure OpenAI, Ollama, and LlamaCPP

## Current Status

**MVP Completion: 100%**

| Component | Status | Tests |
|-----------|--------|-------|
| Backend (7 phases) | Complete | 385 passing |
| Frontend (2 phases) | Complete | 135 passing |
| **Total** | **Complete** | **520 passing** |

**Agentic Behavior**: ✅ Validated - agents can take multiple autonomous tool calls before returning control.

**WebSocket Streaming**: ✅ UI-verified - real-time tool calls and results appear in Playground as they execute.

**MCP Integration**: ✅ Complete - register MCP servers, test connections, assign to agents, use MCP tools in execution.

See [STATUS.md](./STATUS.md) for detailed progress tracking.

## Tech Stack

### Backend
- **Framework**: FastAPI + Python 3.11
- **Database**: PostgreSQL + SQLAlchemy ORM
- **Migrations**: Alembic
- **Agent Framework**: LangChain
- **Authentication**: JWT tokens with bcrypt password hashing

### Frontend
- **Framework**: React 18 + TypeScript + Vite
- **UI Components**: shadcn/ui + Tailwind CSS
- **State Management**: Zustand + TanStack Query
- **Code Editor**: Monaco Editor
- **Forms**: React Hook Form + Zod validation

### Deployment
- **Containerization**: Docker Compose
- **Services**: PostgreSQL, FastAPI backend, React frontend

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### 1. Clone and Setup

```bash
git clone <repository-url>
cd DeepAgentStudio
```

### 2. Generate Encryption Key

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Update the `ENCRYPTION_KEY` in `docker-compose.yml` or create a `.env` file.

### 3. Start Services

```bash
docker-compose up -d
```

### 4. Run Database Migrations

```bash
docker-compose exec backend alembic upgrade head
```

### 5. Access the Application

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |

### 6. Test User (Development)

For development and testing, use the pre-configured test account:

| Field | Value |
|-------|-------|
| **Username** | `demo` |
| **Password** | `demodemo1234` |
| **Email** | `demo@example.com` |

Login via UI at http://localhost:5173 or via API:

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=demo&password=demodemo1234"
```

### 7. Create Your Own Account

Register via the UI at http://localhost:5173 or via API:

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "myuser",
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

> **Note**: Passwords must be at least 12 characters long.

## Features

### Dashboard
- Real-time statistics cards showing counts for Agents, Tools, Prompts, Sessions
- Recent Activity section with last 5 sessions (title, timestamp, status badge)
- Quick Start links to Playground and other key areas
- Loading spinners while fetching data

### Agent Management
- Create agents with different types: ReAct, Plan-and-Execute, Conversational, Custom
- Version control with rollback capability
- Clone existing agents
- Configure LLM settings (provider, model, temperature, max tokens)
- Assign Python tools and MCP servers to agents
- Integrated test chat panel in agent editor

### Tool Library
- **Built-in tools**: Python Code Execution (sandboxed), HTTP Requests
- **Built-in tool protection**: Read-only editor with "Clone to Edit" option
- Full-page tool editor with Monaco code editor
- Custom tool builder with Python function definitions
- Auto-generated input schemas from function signatures
- Tool categories, search, and filtering
- Tools use snake_case names for OpenAI function calling compatibility
- **Unified Tools UI**: Single page for both Python tools and MCP servers with Type filter

### MCP Server Integration
- Connect to Model Context Protocol (MCP) servers
- Support for stdio (local subprocess) and SSE (HTTP) transports
- Full-page MCP server editor with connection configuration
- Test connection and discover available tools
- Assign MCP servers to agents for extended capabilities
- Environment variable support (encrypted at rest)

### Prompt Templates
- Create reusable prompts with `{variable}` syntax
- Version history with rollback
- Use cases: research, coding, analysis, writing
- Message types: system, user, assistant
- Tag-based organization

### Playground
- Interactive chat interface with markdown rendering
- Agent selection dropdown
- **WebSocket streaming**: Real-time tool calls and results as they happen
- Streaming toggle with connection status indicator
- **Memory integration**: Conversation history persists across turns
- **Session continuation**: Resume previous sessions with full context
- Real-time execution trace panel showing thought/action/observation steps
- Memory status indicator
- **Multi-line chat input**: Auto-resizing textarea (Shift+Enter for new line, Enter to send)

### Session & Observability
- Complete conversation history
- Step-by-step execution traces (thought, tool_call, tool_result, error, final_answer)
- Performance metrics (latency, token usage, cost)
- Filter by agent or status
- Session statistics dashboard
- **Session detail dialog** with scroll indicator for overflow content

### LLM Provider Configuration
- Support for 6 provider types
- Encrypted API key storage (Fernet)
- Connection testing
- Custom model configuration

### User Interface
- **Theme persistence**: Light/dark mode preference persists across page reloads
- System theme auto-detection option
- Responsive layout with collapsible sidebar
- Loading states with spinners throughout

## API Endpoints

**63+ REST endpoints + WebSocket** organized by resource:

| Router | Endpoints | Description |
|--------|-----------|-------------|
| `/api/v1/auth` | 4 | Register, login, token refresh, current user |
| `/api/v1/agents` | 12 | CRUD, versions, rollback, tool/MCP assignment, invoke |
| `/api/v1/tools` | 8 | CRUD, schema generation, builtin/custom |
| `/api/v1/prompts` | 10 | CRUD, versions, rollback, preview |
| `/api/v1/sessions` | 13 | CRUD, messages, traces, statistics, timeline |
| `/api/v1/llm-providers` | 8 | CRUD, test connection, update API key |
| `/api/v1/mcp-servers` | 7 | CRUD, test connection, discover tools |
| `/api/v1/ws` | 1 | WebSocket streaming for real-time agent execution |

Full documentation available at http://localhost:8000/docs

## Development

### Project Structure

```
DeepAgentStudio/
├── backend/
│   ├── app/
│   │   ├── api/v1/        # API route handlers
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic (agent executor, session recorder)
│   │   ├── llm/           # LLM client wrappers
│   │   └── utils/         # Utilities
│   ├── alembic/           # Database migrations
│   ├── tests/             # pytest test files
│   └── docs/              # Backend documentation
├── frontend/
│   ├── src/
│   │   ├── api/           # API client and TanStack Query hooks
│   │   ├── components/    # React components (ui, layout, forms)
│   │   ├── pages/         # Route pages
│   │   └── stores/        # Zustand stores
│   └── tests/             # Vitest test files
├── docker-compose.yml
├── SPEC.md                # Product specification
├── STATUS.md              # Development status
└── README.md              # This file
```

### Running Tests

```bash
# Backend tests
docker-compose exec -T backend pytest -v

# Frontend tests
docker-compose exec -T frontend npm run test -- --run

# With coverage
docker-compose exec -T backend pytest --cov=app --cov-report=html
docker-compose exec -T frontend npm run test:coverage
```

### Database Operations

```bash
# Apply migrations
docker-compose exec backend alembic upgrade head

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "description"

# Rollback one migration
docker-compose exec backend alembic downgrade -1

# Connect to database
docker-compose exec postgres psql -U deepagent -d deepagentstudio
```

### Rebuilding Services

```bash
# Rebuild and restart
docker-compose up -d --build

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## Testing Agent Invocation

```bash
# Get auth token (using test user credentials)
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=demo&password=demodemo1234" | jq -r '.access_token')

# Invoke an agent
curl -X POST http://localhost:8000/api/v1/agents/1/invoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the capital of France?"}'
```

## Environment Variables

Key configuration (see `backend/.env.example`):

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET_KEY` | Secret for JWT token signing |
| `ENCRYPTION_KEY` | Fernet key for API key encryption |
| `CORS_ORIGINS` | Allowed origins for CORS |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT expiration time |

## Roadmap

### Completed
- Backend foundation & authentication (JWT, bcrypt)
- Agent, tool, prompt, session management with full CRUD
- LLM provider integration (OpenAI, Anthropic)
- Agent execution engine with tool-calling (GPT-4, Claude 3 support)
- Full React frontend with CRUD interfaces
- Playground with chat and trace visualization
- **Memory integration**: Buffer memory for conversation context
- **Full-page editors**: Agent, Tool, and MCP Server editors with Monaco
- **Built-in tools**: Python Code Execution, HTTP Requests (with read-only protection)
- **Agentic behavior**: Multi-step autonomous execution validated
- **Real-time streaming**: WebSocket-based tool call/result streaming
- **MCP server integration**: Full backend API, frontend UI, agent tool integration
- **Unified Tools UI**: Single page for Python tools and MCP servers with type filtering
- **Dashboard**: Real-time stats, recent activity, quick start links
- **Theme persistence**: User preferences saved across sessions
- **Multi-line chat input**: Enhanced text input with auto-resize

### Planned
- Summary memory (LLM-based summarization for long conversations)
- Vector memory (semantic search for relevant context)
- Vector database support (Pinecone, Weaviate, Chroma)
- Additional LLM provider clients (Google, Azure, Ollama)
- LangSmith integration
- Import/export functionality
- Agent templates library

## Documentation

| Document | Description |
|----------|-------------|
| [SPEC.md](./SPEC.md) | Full product specification |
| [STATUS.md](./STATUS.md) | Development status and progress |
| [FRONTEND-SPEC.md](./FRONTEND-SPEC.md) | Frontend implementation details |
| [TESTING.md](./TESTING.md) | Testing guide |
| [MULTI_TURN_AGENT_TEST_PLAN.md](./MULTI_TURN_AGENT_TEST_PLAN.md) | Agentic behavior validation & test results |
| [backend/docs/LLM_PROVIDER_INTEGRATION.md](./backend/docs/LLM_PROVIDER_INTEGRATION.md) | LLM provider setup guide |

## Contributing

This project follows the phased development approach outlined in SPEC.md. Please refer to STATUS.md for current priorities.

## License

[Add license information]
