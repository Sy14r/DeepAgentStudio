# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DeepAgentStudio is a web application for building, managing, and interacting with LangChain AI agents. It features a FastAPI backend with PostgreSQL and a React/TypeScript frontend.

## Development Commands

### Starting the Application
```bash
docker-compose up -d                              # Start all services
docker-compose exec backend alembic upgrade head  # Run database migrations
```

### Backend (Python/FastAPI)
```bash
# Tests
docker-compose exec -T backend pytest -v
docker-compose exec -T backend pytest --cov=app --cov-report=html
docker-compose exec -T backend pytest tests/test_specific.py -v  # Single file
docker-compose exec -T backend pytest -k "test_name" -v          # Single test

# Linting
docker-compose exec backend black .
docker-compose exec backend flake8 .
docker-compose exec backend mypy .
```

### Frontend (React/TypeScript/Vite)
```bash
docker-compose exec -T frontend npm run dev       # Dev server (port 5173)
docker-compose exec -T frontend npm run build     # Production build
docker-compose exec -T frontend npm run lint      # ESLint (strict, max-warnings 0)
docker-compose exec -T frontend npm run test      # Vitest
docker-compose exec -T frontend npm run test -- --run  # Run once without watch
```

### Database
```bash
docker-compose exec backend alembic upgrade head                    # Apply migrations
docker-compose exec backend alembic revision --autogenerate -m "description"  # New migration
docker-compose exec backend alembic downgrade -1                    # Rollback
docker-compose exec deepagent_postgres psql -U deepagent -d deepagentstudio   # Connect
```

### Logs and Rebuilding
```bash
docker-compose logs -f backend   # Backend logs
docker-compose logs -f frontend  # Frontend logs
docker-compose up -d --build     # Rebuild and restart
```

## Architecture

### Tech Stack
- **Backend**: FastAPI + Python 3.11, SQLAlchemy 2.0, LangChain, JWT auth
- **Frontend**: React 18 + TypeScript, Vite, Tailwind CSS, shadcn/ui, Zustand, TanStack Query
- **Database**: PostgreSQL 15
- **Containers**: Docker Compose (postgres, backend, frontend)

### Project Structure
```
backend/
├── app/
│   ├── api/v1/         # Route handlers (auth, agents, tools, sessions, evaluations, etc.)
│   ├── models/         # SQLAlchemy models
│   ├── schemas/        # Pydantic validation schemas
│   ├── services/       # Business logic (agent_executor, evaluation_runner, etc.)
│   ├── llm/            # LLM client wrappers
│   └── utils/          # Helpers (tools, workspace, model_pricing)
├── alembic/            # Database migrations
└── tests/              # pytest tests

frontend/
├── src/
│   ├── api/            # Axios client + React Query hooks (useAgents, useSessions, etc.)
│   ├── components/     # React components (ui/, layout/, traces/, etc.)
│   ├── pages/          # Route pages (20 total)
│   └── stores/         # Zustand stores (authStore, spanStore, uiStore)
```

### Key Patterns

**API Communication**: REST endpoints via Axios with React Query for caching. WebSocket for real-time streaming during agent execution and span events.

**Authentication**: JWT tokens (30-min expiry) with bcrypt password hashing. Bearer token in Authorization header.

**Database Sessions**: Backend uses SQLAlchemy sessions. For concurrent async operations (like evaluation runs), create separate `SessionLocal()` instances per task to avoid `IllegalStateChangeError`.

**Frontend State**: Zustand for global state (auth, UI preferences), TanStack Query for server state with automatic cache invalidation.

**Built-in vs Custom**: Tools, agents, and evaluators have `is_builtin` flags. Built-in items are read-only; users can clone them to customize.

### Services Architecture

- `AgentExecutorService`: Runs agents with LangChain, handles tool execution, WebSocket streaming
- `EvaluationRunnerService`: Executes evaluation runs with concurrent example processing
- `WorkspaceService`: Manages agent file workspaces (sandboxed per session)
- `SpanService`: Captures hierarchical execution traces via LangChain callbacks

### Frontend Page Organization

- **Editors**: Full-page editors for agents, tools, prompts, datasets, evaluators (Monaco code editor)
- **Playground**: Chat interface with execution trace panel, WebSocket streaming
- **Trace Explorer**: LangSmith-style hierarchical span visualization (`/sessions/:id/trace`)
- **Evaluations**: Dataset management, evaluator configuration, run results visualization

## Important Conventions

### Backend
- Route handlers in `app/api/v1/` call services in `app/services/`
- Pydantic schemas validate all API requests/responses
- Use `get_db()` dependency for database sessions in route handlers
- Async operations that need their own DB session should create `SessionLocal()` instances

### Frontend
- Custom hooks in `src/api/hooks/` wrap React Query for API calls
- UI components from shadcn/ui in `src/components/ui/`
- Path alias `@/` maps to `src/`
- Forms use React Hook Form + Zod validation

### Database
- Foreign keys cascade on delete where appropriate
- `created_at`/`updated_at` timestamps on most models
- API keys and secrets encrypted with Fernet

## Development Credentials

Test account for local development:
- **Username**: testuser2026
- **Password**: TestPassword123!

## Testing

Backend pytest markers: `unit`, `integration`, `auth`, `security`, `models`, `slow`

```bash
# Run specific marker
docker-compose exec -T backend pytest -m "auth" -v
```

Frontend uses Vitest with React Testing Library.
