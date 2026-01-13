# DeepAgentStudio

A comprehensive web application for building, managing, and interacting with LangChain AI agents.

## Overview

DeepAgentStudio provides developers and AI/ML engineers with a complete platform for agent development, including:

- **Agent Catalog**: Create, version, and manage AI agents with different architectures (ReAct, Plan-and-Execute, Conversational)
- **Built-in Power Agent**: Pre-configured agent with all 12 tools, ready to use out of the box
- **Tool Library**: 12 built-in tools (code execution, web research, file management, task tracking, image generation) plus custom tool builder
- **Multimodal Output**: Agents can generate and return images, audio, video, and files inline in chat
- **MCP Server Integration**: Connect to Model Context Protocol servers to extend agent capabilities
- **Prompt Management**: Full-page editor with version history, side-by-side diff comparison, and rollback
- **Interactive Playground**: Chat interface with WebSocket streaming and real-time trace visualization
- **Session Recording**: Complete conversation history, execution traces, and performance metrics
- **Trace Explorer**: Full-page hierarchical trace visualization with filtering, search, and export (LangSmith/Langfuse-style)
- **Evaluation System**: Test agents against datasets with 17 built-in evaluators (output matching, LLM judge, run metadata analysis)
- **LLM Provider Integration**: Support for OpenAI, Anthropic, (Google, Azure OpenAI, Ollama, and LlamaCPP coming soon)

## Current Status

**MVP Completion: 100%** | **Evaluation System: In Progress**

| Component | Status | Tests |
|-----------|--------|-------|
| Backend (7 phases) | Complete | 385+ passing |
| Frontend (2 phases) | Complete | 135 passing |
| Advanced Toolkit (6 phases) | Complete | Integrated |
| Evaluation System | Backend Complete, Frontend In Progress | 33 test files |
| **Total** | **Active Development** | **520+ passing** |

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

The backend will automatically:
- Wait for PostgreSQL to be ready
- Run database migrations
- Seed built-in tools and agents
- Start the API server

You can monitor startup progress with:
```bash
docker-compose logs -f backend
```

### 4. Access the Application

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |

### 5. Create an Account

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

### 6. Start Using the Power Agent

Once logged in, the **Power Agent** is immediately available:
- Navigate to **Agents** page
- Find "Power Agent" with the "Built-in" badge
- Click to open in Playground and start chatting
- The agent has access to all 12 built-in tools including image generation

## Features

### Built-in Power Agent

A pre-configured, full-featured AI assistant available to all users:
- Access to all 12 built-in tools including DALL-E image generation
- **Vision support**: Analyze images with GPT-4o or other vision models
- **Image generation**: Create images from text descriptions using DALL-E 2
- Optimized for research and development tasks
- Cannot be modified (clone to customize)
- Uses ReAct execution strategy with gpt-4o

### Built-in Tools (12 Total)

| Tool | Category | Description |
|------|----------|-------------|
| Python Code Execution | Code | Execute Python code in sandbox |
| HTTP Request | API | Make HTTP requests to external APIs |
| DALL-E Image Generation | Creative | Generate images from text prompts using DALL-E 2 |
| File Read | Workspace | Read files from agent workspace |
| File Write | Workspace | Write/create files in workspace |
| File Edit | Workspace | Edit files with string replacement |
| File List | Workspace | List files matching glob patterns |
| File Search | Workspace | Search file contents with regex |
| Task Manager | Planning | Track tasks and progress |
| Scratchpad | Memory | Store working notes by section |
| Web Search | Research | Search web via DuckDuckGo |
| Web Fetch | Research | Fetch and parse web pages |

### Agent Management
- Create agents with different types: ReAct, Plan-and-Execute, Conversational
- Version control with rollback capability
- Clone existing agents (including built-in Power Agent)
- Configure LLM settings (provider, model, temperature, max tokens)
- Assign tools and MCP servers to agents
- Integrated test chat panel with WebSocket streaming
- **Multimodal support**: Agents with vision-capable models can process image attachments

### Tool Library
- **Built-in tool protection**: Read-only with "Clone to Edit" option
- Full-page tool editor with Monaco code editor
- Custom tool builder with Python function definitions
- Auto-generated input schemas from function signatures
- **Unified Tools UI**: Single page for both Python tools and MCP servers

### Prompt Management
- **Full-page editor**: Dedicated `PromptEditorPage` with split-view layout
- **Version history panel**: View all versions with metadata (date, usage count, variables)
- **Version comparison**: Side-by-side diff showing template changes between versions
- **Rollback support**: Restore any previous version with one click
- **Variable detection**: Automatic `{variable}` syntax detection with preview
- **Template preview**: Live rendering with variable substitution
- **A/B testing support**: Mark versions active/inactive for testing

### MCP Server Integration
- Connect to Model Context Protocol (MCP) servers
- Support for stdio (local subprocess) and SSE (HTTP) transports
- Test connection and discover available tools
- Assign MCP servers to agents for extended capabilities
- Environment variable support (encrypted at rest)

### Playground
- Interactive chat interface with markdown rendering
- **WebSocket streaming**: Real-time tool calls and results
- **Image attachments**: Upload images for vision-capable models (GPT-4o, Claude 3)
- **Multimodal output**: View generated images, audio, video inline in chat
- **Memory integration**: Conversation history persists across turns
- **Session continuation**: Resume previous sessions with full context
- Real-time execution trace panel
- Multi-line chat input with auto-resize
- Drag-and-drop file attachment support

### Session & Observability
- Complete conversation history
- Step-by-step execution traces
- Performance metrics (latency, token usage, cost calculated from spans)
- **Session detail dialog** with:
  - Rename sessions inline via edit icon
  - Resume in Playground with play button
  - Delete sessions with confirmation
  - Auto-refresh during execution
- **View mode persistence**: Grid/list preference saved to localStorage
- Grid and list view options with filtering by agent and status

### Trace Explorer (LangSmith/Langfuse-style)
- **Hierarchical Spans**: Tree view of all LangChain operations (LLM calls, tool invocations, chains, retrievers)
- **Real-time Updates**: WebSocket streaming of spans during execution with live indicators
- **11 Span Types**: agent, chain, llm, tool, retriever, embedding, parser, prompt, memory, thought, error
- **Detailed Metrics**: Per-span token usage, cost calculation (25+ model pricing), timing
- **Full-Page Explorer**: Dedicated `/sessions/:id/trace` route with resizable split view
- **Filtering & Search**: Filter by span type, status, duration; text search with match highlighting
- **Statistics Dashboard**: Token breakdown, cost summary, span count by type
- **Export Options**: JSON (hierarchical) and CSV (flattened) export
- **Keyboard Navigation**: Cmd/Ctrl+F for search, arrow keys for tree navigation
- **Deep Linking**: URL params for selected span, shareable links

## API Endpoints

**105+ REST endpoints + WebSocket** organized by resource:

| Router | Endpoints | Description |
|--------|-----------|-------------|
| `/api/v1/auth` | 4 | Register, login, token refresh, current user |
| `/api/v1/agents` | 13 | CRUD, versions, rollback, tool/MCP assignment, invoke, clone |
| `/api/v1/agent-types` | 9 | CRUD, clone, recommended tools |
| `/api/v1/tools` | 8 | CRUD, schema generation |
| `/api/v1/prompts` | 10 | CRUD, versions, rollback, preview |
| `/api/v1/sessions` | 14 | CRUD, messages, traces, statistics, backfill-costs |
| `/api/v1/sessions/.../spans` | 5 | Span list, tree, stats, traces, detail |
| `/api/v1/llm-providers` | 8 | CRUD, test connection |
| `/api/v1/mcp-servers` | 7 | CRUD, test connection, discover tools |
| `/api/v1/evaluations` | 24 | Datasets, evaluators, runs, results, comparison |
| `/api/v1/ws` | 1 | WebSocket streaming + real-time span events |

Full documentation available at http://localhost:8000/docs

## Development

### Project Structure

```
DeepAgentStudio/
├── backend/
│   ├── app/
│   │   ├── api/v1/        # API route handlers (incl. spans.py, evaluations.py)
│   │   ├── models/        # SQLAlchemy models (11 model files)
│   │   ├── schemas/       # Pydantic schemas (incl. span.py, evaluation.py)
│   │   ├── services/      # Business logic (incl. evaluation_runner.py, evaluator_engine.py)
│   │   ├── llm/           # LLM client wrappers
│   │   └── utils/         # Utilities (tools, workspace, model_pricing)
│   ├── alembic/           # Database migrations (15 total)
│   └── tests/             # pytest test files (33 test files)
├── frontend/
│   ├── src/
│   │   ├── api/           # API client and hooks (incl. useSpans.ts, useEvaluations.ts)
│   │   ├── components/    # React components (incl. traces/ directory)
│   │   ├── pages/         # Route pages (20 total incl. evaluation pages)
│   │   └── stores/        # Zustand stores (incl. spanStore.ts)
│   └── tests/             # Vitest test files
├── docker-compose.yml
├── STATUS.md              # Development status
├── SECURITY.md            # Security notes
├── LICENSE.md             # Project Licensing Terms
├── CLAUDE.md              # AI assistant guidelines
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
```

### Database Operations

Migrations run automatically on backend startup. For manual operations:

```bash
# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "description"

# Rollback one migration
docker-compose exec backend alembic downgrade -1

# Connect to database
docker-compose exec deepagent_postgres psql -U deepagent -d deepagentstudio
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
```

## Testing Agent Invocation

```bash
# Get auth token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=<your-username>&password=<your-password>" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Invoke an agent (use the Power Agent ID from your database)
curl -X POST http://localhost:8000/api/v1/agents/17/invoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Search the web for the latest news about AI"}'
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
- Backend foundation & authentication
- Agent, tool, prompt, session management
- LLM provider integration (OpenAI, Anthropic)
- Agent execution engine with tool-calling
- Full React frontend with CRUD interfaces
- Playground with WebSocket streaming
- Memory integration (buffer memory)
- Full-page editors (Agent, Tool, MCP Server, Prompt)
- 12 built-in tools (code, API, workspace, web, image generation)
- Built-in Power Agent
- Agent cloning
- MCP server integration
- Agent type system with custom code support
- **Multimodal image input** for vision-capable models
- **Multimodal output** (images, audio, video, files) with content block rendering
- **DALL-E image generation** tool with inline display
- **Prompt version management** with history, comparison, and rollback
- **Enhanced Tracing System** (LangSmith/Langfuse-style) with:
  - Hierarchical span capture via LangChain callbacks
  - 11 span types (agent, chain, llm, tool, retriever, embedding, parser, prompt, memory, thought, error)
  - Real-time WebSocket span streaming during execution
  - Full-page Trace Explorer with tree view, filtering, search, and export
  - Per-span token usage and cost calculation (25+ model pricing)
- **Session management improvements**:
  - Rename, delete, resume sessions from detail popup
  - Cost tracking from span data with backfill support
  - View mode persistence (grid/list preference)
- **Evaluation System Backend**:
  - Datasets with input/output test examples
  - 17 built-in evaluators in 2 categories (output & run metadata)
  - Output evaluators: exact match, contains, regex, JSON match, semantic similarity, LLM judge
  - Run metadata evaluators: token efficiency, latency, cost, chain length, tool success rate, error rate
  - Async evaluation runner with progress tracking
  - Run comparison and aggregate metrics
  - 24 REST API endpoints

### In Progress
- **Evaluation System Frontend**:
  - EvaluationsPage with tabbed interface (Datasets, Evaluators, Runs)
  - DatasetEditorPage with examples table and import/export
  - EvaluatorEditorPage with type-specific configuration
  - RunDetailPage with results visualization

### Planned
- Summary memory (LLM-based summarization)
- Vector memory (semantic search)
- Vector database support (Pinecone, Weaviate, Chroma)
- Additional LLM provider clients (Google, Azure, Ollama)
- LangSmith integration
- Import/export functionality
- Agent templates library

## Documentation

| Document | Description |
|----------|-------------|
| [STATUS.md](./STATUS.md) | Development status and progress |
| [SECURITY.md](./SECURITY.md) | Security considerations and deployment guide |
| [CLAUDE.md](./CLAUDE.md) | AI assistant guidelines and project conventions |
| [backend/docs/LLM_PROVIDER_INTEGRATION.md](./backend/docs/LLM_PROVIDER_INTEGRATION.md) | LLM provider integration guide |

## License

[AGPLv3 License](./LICENSE.md)
