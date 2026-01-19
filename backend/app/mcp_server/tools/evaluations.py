"""MCP tools for evaluation operations."""
from typing import List, Optional

from mcp.types import TextContent

from ..server import mcp_tool
from ..context import MCPContext
from ..errors import ResourceNotFound
from ...models.evaluation import Evaluation, EvaluationRun, Evaluator


@mcp_tool(
    name="evaluations_list",
    description="List all evaluations accessible to the user.",
    permission="evaluations:list",
    input_schema={
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "default": 50,
                "minimum": 1,
                "maximum": 100
            },
            "offset": {
                "type": "integer",
                "default": 0,
                "minimum": 0
            }
        }
    }
)
async def list_evaluations(
    ctx: MCPContext,
    limit: int = 50,
    offset: int = 0
) -> List[TextContent]:
    """List all evaluations."""
    query = ctx.db.query(Evaluation).filter(
        Evaluation.user_id == ctx.user_id
    )

    total = query.count()
    evaluations = query.order_by(Evaluation.updated_at.desc()).offset(offset).limit(limit).all()

    result = {
        "total": total,
        "offset": offset,
        "limit": limit,
        "evaluations": [
            {
                "id": e.id,
                "name": e.name,
                "description": e.description,
                "agent_id": e.agent_id,
                "dataset_id": e.dataset_id
            }
            for e in evaluations
        ]
    }

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="evaluations_read",
    description="Get detailed information about an evaluation including recent runs.",
    permission="evaluations:read",
    input_schema={
        "type": "object",
        "properties": {
            "evaluation_id": {
                "type": "integer",
                "description": "ID of the evaluation to retrieve"
            },
            "include_runs": {
                "type": "boolean",
                "description": "Include recent runs",
                "default": True
            },
            "run_limit": {
                "type": "integer",
                "description": "Maximum number of runs to include",
                "default": 10
            }
        },
        "required": ["evaluation_id"]
    }
)
async def read_evaluation(
    ctx: MCPContext,
    evaluation_id: int,
    include_runs: bool = True,
    run_limit: int = 10
) -> List[TextContent]:
    """Get detailed information about an evaluation."""
    evaluation = ctx.db.query(Evaluation).filter(
        Evaluation.id == evaluation_id,
        Evaluation.user_id == ctx.user_id
    ).first()

    if not evaluation:
        raise ResourceNotFound(resource_type="evaluation", resource_id=evaluation_id)

    result = {
        "id": evaluation.id,
        "name": evaluation.name,
        "description": evaluation.description,
        "agent_id": evaluation.agent_id,
        "dataset_id": evaluation.dataset_id,
        "config": evaluation.config,
        "created_at": evaluation.created_at.isoformat() if evaluation.created_at else None,
        "updated_at": evaluation.updated_at.isoformat() if evaluation.updated_at else None
    }

    if include_runs:
        runs = ctx.db.query(EvaluationRun).filter(
            EvaluationRun.evaluation_id == evaluation_id
        ).order_by(EvaluationRun.created_at.desc()).limit(run_limit).all()

        result["runs"] = [
            {
                "id": r.id,
                "status": r.status.value if r.status else None,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "total_examples": r.total_examples,
                "completed_examples": r.completed_examples
            }
            for r in runs
        ]

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="evaluators_list",
    description="List all evaluators accessible to the user.",
    permission="evaluations:list",
    input_schema={
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Filter by evaluator category"
            },
            "limit": {
                "type": "integer",
                "default": 50,
                "minimum": 1,
                "maximum": 100
            }
        }
    }
)
async def list_evaluators(
    ctx: MCPContext,
    category: Optional[str] = None,
    limit: int = 50
) -> List[TextContent]:
    """List all evaluators."""
    from sqlalchemy import or_

    query = ctx.db.query(Evaluator).filter(
        or_(
            Evaluator.user_id == ctx.user_id,
            Evaluator.is_builtin == True
        )
    )

    if category:
        query = query.filter(Evaluator.category == category)

    evaluators = query.limit(limit).all()

    result = {
        "evaluators": [
            {
                "id": e.id,
                "name": e.name,
                "description": e.description,
                "category": e.category.value if e.category else None,
                "evaluator_type": e.evaluator_type.value if e.evaluator_type else None,
                "is_builtin": e.is_builtin
            }
            for e in evaluators
        ]
    }

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="evaluations_create",
    description="Create a new evaluation configuration.",
    permission="evaluations:create",
    input_schema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name of the evaluation"
            },
            "description": {
                "type": "string",
                "description": "Description"
            },
            "agent_id": {
                "type": "integer",
                "description": "ID of the agent to evaluate"
            },
            "dataset_id": {
                "type": "integer",
                "description": "ID of the dataset to use"
            },
            "config": {
                "type": "object",
                "description": "Evaluation configuration"
            }
        },
        "required": ["name", "agent_id", "dataset_id"]
    }
)
async def create_evaluation(
    ctx: MCPContext,
    name: str,
    agent_id: int,
    dataset_id: int,
    description: Optional[str] = None,
    config: Optional[dict] = None
) -> List[TextContent]:
    """Create a new evaluation."""
    from sqlalchemy import or_
    from ...models.agent import Agent
    from ...models.evaluation import EvaluationDataset

    # Verify agent exists and is accessible
    agent = ctx.db.query(Agent).filter(
        Agent.id == agent_id,
        or_(
            Agent.user_id == ctx.user_id,
            Agent.is_builtin == True
        )
    ).first()

    if not agent:
        raise ResourceNotFound(resource_type="agent", resource_id=agent_id)

    # Verify dataset exists and is owned
    dataset = ctx.db.query(EvaluationDataset).filter(
        EvaluationDataset.id == dataset_id,
        EvaluationDataset.user_id == ctx.user_id
    ).first()

    if not dataset:
        raise ResourceNotFound(resource_type="dataset", resource_id=dataset_id)

    evaluation = Evaluation(
        user_id=ctx.user_id,
        name=name,
        description=description or "",
        agent_id=agent_id,
        dataset_id=dataset_id,
        config=config or {}
    )
    ctx.db.add(evaluation)
    ctx.db.commit()

    result = {
        "id": evaluation.id,
        "name": evaluation.name,
        "agent_id": evaluation.agent_id,
        "dataset_id": evaluation.dataset_id,
        "created_at": evaluation.created_at.isoformat() if evaluation.created_at else None
    }

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="evaluations_run",
    description="Start an evaluation run for a configured evaluation.",
    permission="evaluations:run",
    input_schema={
        "type": "object",
        "properties": {
            "evaluation_id": {
                "type": "integer",
                "description": "ID of the evaluation to run"
            },
            "llm_provider_id": {
                "type": "integer",
                "description": "ID of the LLM provider to use for evaluators (if needed)"
            }
        },
        "required": ["evaluation_id"]
    }
)
async def run_evaluation(
    ctx: MCPContext,
    evaluation_id: int,
    llm_provider_id: Optional[int] = None
) -> List[TextContent]:
    """Start an evaluation run."""
    from ...models.evaluation import EvaluationRunStatus

    # Verify evaluation exists and is owned
    evaluation = ctx.db.query(Evaluation).filter(
        Evaluation.id == evaluation_id,
        Evaluation.user_id == ctx.user_id
    ).first()

    if not evaluation:
        raise ResourceNotFound(resource_type="evaluation", resource_id=evaluation_id)

    # Create a new run
    run = EvaluationRun(
        evaluation_id=evaluation_id,
        status=EvaluationRunStatus.PENDING,
        total_examples=0,
        completed_examples=0,
        config={
            "llm_provider_id": llm_provider_id
        } if llm_provider_id else {}
    )
    ctx.db.add(run)
    ctx.db.commit()

    # Note: Actual execution would be handled by a background service
    # This just creates the run record

    result = {
        "run_id": run.id,
        "evaluation_id": evaluation_id,
        "status": run.status.value if run.status else "pending",
        "message": "Evaluation run created. It will be processed by the background service."
    }

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="evaluations_get_run",
    description="Get details about a specific evaluation run including results.",
    permission="evaluations:read",
    input_schema={
        "type": "object",
        "properties": {
            "run_id": {
                "type": "integer",
                "description": "ID of the evaluation run"
            },
            "include_results": {
                "type": "boolean",
                "description": "Include individual example results",
                "default": True
            },
            "result_limit": {
                "type": "integer",
                "description": "Maximum number of results to return",
                "default": 50
            }
        },
        "required": ["run_id"]
    }
)
async def get_evaluation_run(
    ctx: MCPContext,
    run_id: int,
    include_results: bool = True,
    result_limit: int = 50
) -> List[TextContent]:
    """Get details about an evaluation run."""
    from ...models.evaluation import EvaluationResult

    # Get the run
    run = ctx.db.query(EvaluationRun).filter(
        EvaluationRun.id == run_id
    ).first()

    if not run:
        raise ResourceNotFound(resource_type="evaluation_run", resource_id=run_id)

    # Verify user has access to the evaluation
    evaluation = ctx.db.query(Evaluation).filter(
        Evaluation.id == run.evaluation_id,
        Evaluation.user_id == ctx.user_id
    ).first()

    if not evaluation:
        raise ResourceNotFound(resource_type="evaluation_run", resource_id=run_id)

    result = {
        "id": run.id,
        "evaluation_id": run.evaluation_id,
        "status": run.status.value if run.status else None,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "total_examples": run.total_examples,
        "completed_examples": run.completed_examples,
        "config": run.config
    }

    if include_results:
        results = ctx.db.query(EvaluationResult).filter(
            EvaluationResult.run_id == run_id
        ).limit(result_limit).all()

        result["results"] = [
            {
                "id": r.id,
                "example_id": r.example_id,
                "score": r.score,
                "passed": r.passed,
                "agent_output": r.agent_output,
                "evaluator_output": r.evaluator_output,
                "error": r.error
            }
            for r in results
        ]
        result["result_count"] = len(results)

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="evaluations_list_runs",
    description="List evaluation runs for an evaluation.",
    permission="evaluations:read",
    input_schema={
        "type": "object",
        "properties": {
            "evaluation_id": {
                "type": "integer",
                "description": "ID of the evaluation"
            },
            "limit": {
                "type": "integer",
                "default": 20,
                "minimum": 1,
                "maximum": 100
            },
            "offset": {
                "type": "integer",
                "default": 0,
                "minimum": 0
            }
        },
        "required": ["evaluation_id"]
    }
)
async def list_evaluation_runs(
    ctx: MCPContext,
    evaluation_id: int,
    limit: int = 20,
    offset: int = 0
) -> List[TextContent]:
    """List runs for an evaluation."""
    # Verify evaluation exists and is owned
    evaluation = ctx.db.query(Evaluation).filter(
        Evaluation.id == evaluation_id,
        Evaluation.user_id == ctx.user_id
    ).first()

    if not evaluation:
        raise ResourceNotFound(resource_type="evaluation", resource_id=evaluation_id)

    query = ctx.db.query(EvaluationRun).filter(
        EvaluationRun.evaluation_id == evaluation_id
    )

    total = query.count()
    runs = query.order_by(EvaluationRun.created_at.desc()).offset(offset).limit(limit).all()

    result = {
        "evaluation_id": evaluation_id,
        "total": total,
        "offset": offset,
        "limit": limit,
        "runs": [
            {
                "id": r.id,
                "status": r.status.value if r.status else None,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "total_examples": r.total_examples,
                "completed_examples": r.completed_examples
            }
            for r in runs
        ]
    }

    return [TextContent(type="text", text=str(result))]


# List of all tools in this module for registration
TOOLS = [
    list_evaluations,
    read_evaluation,
    list_evaluators,
    create_evaluation,
    run_evaluation,
    get_evaluation_run,
    list_evaluation_runs
]
