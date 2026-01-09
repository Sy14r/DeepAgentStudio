from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import SessionLocal
from .utils.builtin_tools import seed_builtin_tools
from .utils.power_agent import seed_builtin_agents
from .services.evaluator_service import EvaluatorService
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup: seed built-in tools and agents
    logger.info("Seeding built-in tools...")
    db = SessionLocal()
    try:
        seed_builtin_tools(db)
        logger.info("Built-in tools seeded successfully")

        # Seed built-in agents (after tools so they can reference tool IDs)
        logger.info("Seeding built-in agents...")
        seed_builtin_agents(db)
        logger.info("Built-in agents seeded successfully")

        # Seed built-in evaluators
        logger.info("Seeding built-in evaluators...")
        evaluator_service = EvaluatorService(db)
        evaluator_service.seed_builtin_evaluators()
        logger.info("Built-in evaluators seeded successfully")
    except Exception as e:
        logger.error(f"Failed to seed built-in items: {e}")
    finally:
        db.close()

    yield  # Application runs here

    # Shutdown: cleanup if needed
    logger.info("Application shutdown")


# Create FastAPI application
app = FastAPI(
    title="DeepAgentStudio API",
    description="API for managing LangChain deepagents",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "DeepAgentStudio API",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# API routers
from .api.v1 import auth, agents, agent_types, tools, prompts, sessions, llm_providers, websocket, mcp_servers, spans, evaluations

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(agent_types.router, prefix="/api/v1/agent-types", tags=["agent-types"])
app.include_router(tools.router, prefix="/api/v1/tools", tags=["tools"])
app.include_router(prompts.router, prefix="/api/v1/prompts", tags=["prompts"])
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])
app.include_router(spans.router, prefix="/api/v1/sessions", tags=["spans"])
app.include_router(llm_providers.router, prefix="/api/v1/llm-providers", tags=["llm-providers"])
app.include_router(mcp_servers.router, prefix="/api/v1/mcp-servers", tags=["mcp-servers"])
app.include_router(evaluations.router, prefix="/api/v1/evaluations", tags=["evaluations"])
app.include_router(websocket.router, prefix="/api/v1/ws", tags=["websocket"])
