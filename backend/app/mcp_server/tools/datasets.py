"""MCP tools for dataset operations."""
from typing import List, Optional, Dict, Any

from mcp.types import TextContent
from sqlalchemy import or_

from ..server import mcp_tool
from ..context import MCPContext
from ..errors import ResourceNotFound, ValidationError
from ...models.evaluation import EvaluationDataset, DatasetExample


@mcp_tool(
    name="datasets_list",
    description="List all evaluation datasets accessible to the user.",
    permission="datasets:list",
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
async def list_datasets(
    ctx: MCPContext,
    limit: int = 50,
    offset: int = 0
) -> List[TextContent]:
    """List all evaluation datasets."""
    query = ctx.db.query(EvaluationDataset).filter(
        EvaluationDataset.user_id == ctx.user_id
    )

    total = query.count()
    datasets = query.order_by(EvaluationDataset.updated_at.desc()).offset(offset).limit(limit).all()

    result = {
        "total": total,
        "offset": offset,
        "limit": limit,
        "datasets": [
            {
                "id": d.id,
                "name": d.name,
                "description": d.description,
                "example_count": len(d.examples) if d.examples else 0
            }
            for d in datasets
        ]
    }

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="datasets_read",
    description="Get detailed information about a dataset including its examples.",
    permission="datasets:read",
    input_schema={
        "type": "object",
        "properties": {
            "dataset_id": {
                "type": "integer",
                "description": "ID of the dataset to retrieve"
            },
            "include_examples": {
                "type": "boolean",
                "description": "Include examples in the response",
                "default": True
            },
            "example_limit": {
                "type": "integer",
                "description": "Maximum number of examples to return",
                "default": 100
            }
        },
        "required": ["dataset_id"]
    }
)
async def read_dataset(
    ctx: MCPContext,
    dataset_id: int,
    include_examples: bool = True,
    example_limit: int = 100
) -> List[TextContent]:
    """Get detailed information about a dataset."""
    dataset = ctx.db.query(EvaluationDataset).filter(
        EvaluationDataset.id == dataset_id,
        EvaluationDataset.user_id == ctx.user_id
    ).first()

    if not dataset:
        raise ResourceNotFound(resource_type="dataset", resource_id=dataset_id)

    result = {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "input_schema": dataset.input_schema,
        "output_schema": dataset.output_schema,
        "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
        "updated_at": dataset.updated_at.isoformat() if dataset.updated_at else None
    }

    if include_examples:
        examples = ctx.db.query(DatasetExample).filter(
            DatasetExample.dataset_id == dataset_id
        ).limit(example_limit).all()

        result["examples"] = [
            {
                "id": e.id,
                "input_data": e.input_data,
                "expected_output": e.expected_output,
                "tags": e.tags
            }
            for e in examples
        ]
        result["example_count"] = len(examples)

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="datasets_add_example",
    description="Add a new example to an evaluation dataset.",
    permission="datasets:update:examples",
    input_schema={
        "type": "object",
        "properties": {
            "dataset_id": {
                "type": "integer",
                "description": "ID of the dataset"
            },
            "input_data": {
                "type": "object",
                "description": "Input data for the example"
            },
            "expected_output": {
                "type": "object",
                "description": "Expected output for the example"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags for categorizing the example"
            }
        },
        "required": ["dataset_id", "input_data"]
    }
)
async def add_dataset_example(
    ctx: MCPContext,
    dataset_id: int,
    input_data: Dict[str, Any],
    expected_output: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None
) -> List[TextContent]:
    """Add a new example to a dataset."""
    # Verify dataset exists and user owns it
    dataset = ctx.db.query(EvaluationDataset).filter(
        EvaluationDataset.id == dataset_id,
        EvaluationDataset.user_id == ctx.user_id
    ).first()

    if not dataset:
        raise ResourceNotFound(resource_type="dataset", resource_id=dataset_id)

    example = DatasetExample(
        dataset_id=dataset_id,
        input_data=input_data,
        expected_output=expected_output,
        tags=tags or []
    )
    ctx.db.add(example)
    ctx.db.commit()

    result = {
        "id": example.id,
        "dataset_id": dataset_id,
        "input_data": example.input_data,
        "expected_output": example.expected_output,
        "tags": example.tags,
        "created_at": example.created_at.isoformat() if example.created_at else None
    }

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="datasets_create",
    description="Create a new evaluation dataset.",
    permission="datasets:create",
    input_schema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name of the dataset"
            },
            "description": {
                "type": "string",
                "description": "Description of the dataset"
            },
            "input_schema": {
                "type": "object",
                "description": "JSON schema for input data"
            },
            "output_schema": {
                "type": "object",
                "description": "JSON schema for output/expected data"
            }
        },
        "required": ["name"]
    }
)
async def create_dataset(
    ctx: MCPContext,
    name: str,
    description: Optional[str] = None,
    input_schema: Optional[Dict[str, Any]] = None,
    output_schema: Optional[Dict[str, Any]] = None
) -> List[TextContent]:
    """Create a new evaluation dataset."""
    dataset = EvaluationDataset(
        user_id=ctx.user_id,
        name=name,
        description=description or "",
        input_schema=input_schema,
        output_schema=output_schema
    )
    ctx.db.add(dataset)
    ctx.db.commit()

    result = {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "created_at": dataset.created_at.isoformat() if dataset.created_at else None
    }

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="datasets_remove_example",
    description="Remove an example from an evaluation dataset.",
    permission="datasets:update:examples",
    input_schema={
        "type": "object",
        "properties": {
            "dataset_id": {
                "type": "integer",
                "description": "ID of the dataset"
            },
            "example_id": {
                "type": "integer",
                "description": "ID of the example to remove"
            }
        },
        "required": ["dataset_id", "example_id"]
    }
)
async def remove_dataset_example(
    ctx: MCPContext,
    dataset_id: int,
    example_id: int
) -> List[TextContent]:
    """Remove an example from a dataset."""
    # Verify dataset exists and user owns it
    dataset = ctx.db.query(EvaluationDataset).filter(
        EvaluationDataset.id == dataset_id,
        EvaluationDataset.user_id == ctx.user_id
    ).first()

    if not dataset:
        raise ResourceNotFound(resource_type="dataset", resource_id=dataset_id)

    # Get the example
    example = ctx.db.query(DatasetExample).filter(
        DatasetExample.id == example_id,
        DatasetExample.dataset_id == dataset_id
    ).first()

    if not example:
        raise ResourceNotFound(resource_type="example", resource_id=example_id)

    ctx.db.delete(example)
    ctx.db.commit()

    return [TextContent(type="text", text=f"Example {example_id} removed from dataset {dataset_id}")]


@mcp_tool(
    name="datasets_update",
    description="Update an evaluation dataset's metadata.",
    permission="datasets:update",
    input_schema={
        "type": "object",
        "properties": {
            "dataset_id": {
                "type": "integer",
                "description": "ID of the dataset to update"
            },
            "name": {
                "type": "string",
                "description": "New name"
            },
            "description": {
                "type": "string",
                "description": "New description"
            },
            "input_schema": {
                "type": "object",
                "description": "New input schema"
            },
            "output_schema": {
                "type": "object",
                "description": "New output schema"
            }
        },
        "required": ["dataset_id"]
    }
)
async def update_dataset(
    ctx: MCPContext,
    dataset_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    input_schema: Optional[Dict[str, Any]] = None,
    output_schema: Optional[Dict[str, Any]] = None
) -> List[TextContent]:
    """Update a dataset's metadata."""
    dataset = ctx.db.query(EvaluationDataset).filter(
        EvaluationDataset.id == dataset_id,
        EvaluationDataset.user_id == ctx.user_id
    ).first()

    if not dataset:
        raise ResourceNotFound(resource_type="dataset", resource_id=dataset_id)

    if name is not None:
        dataset.name = name
    if description is not None:
        dataset.description = description
    if input_schema is not None:
        dataset.input_schema = input_schema
    if output_schema is not None:
        dataset.output_schema = output_schema

    ctx.db.commit()

    result = {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "updated_at": dataset.updated_at.isoformat() if dataset.updated_at else None
    }

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="datasets_update_example",
    description="Update an existing example in a dataset.",
    permission="datasets:update:examples",
    input_schema={
        "type": "object",
        "properties": {
            "dataset_id": {
                "type": "integer",
                "description": "ID of the dataset"
            },
            "example_id": {
                "type": "integer",
                "description": "ID of the example to update"
            },
            "input_data": {
                "type": "object",
                "description": "New input data"
            },
            "expected_output": {
                "type": "object",
                "description": "New expected output"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "New tags"
            }
        },
        "required": ["dataset_id", "example_id"]
    }
)
async def update_dataset_example(
    ctx: MCPContext,
    dataset_id: int,
    example_id: int,
    input_data: Optional[Dict[str, Any]] = None,
    expected_output: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None
) -> List[TextContent]:
    """Update an existing example in a dataset."""
    # Verify dataset exists and user owns it
    dataset = ctx.db.query(EvaluationDataset).filter(
        EvaluationDataset.id == dataset_id,
        EvaluationDataset.user_id == ctx.user_id
    ).first()

    if not dataset:
        raise ResourceNotFound(resource_type="dataset", resource_id=dataset_id)

    # Get the example
    example = ctx.db.query(DatasetExample).filter(
        DatasetExample.id == example_id,
        DatasetExample.dataset_id == dataset_id
    ).first()

    if not example:
        raise ResourceNotFound(resource_type="example", resource_id=example_id)

    if input_data is not None:
        example.input_data = input_data
    if expected_output is not None:
        example.expected_output = expected_output
    if tags is not None:
        example.tags = tags

    ctx.db.commit()

    result = {
        "id": example.id,
        "dataset_id": dataset_id,
        "input_data": example.input_data,
        "expected_output": example.expected_output,
        "tags": example.tags
    }

    return [TextContent(type="text", text=str(result))]


# List of all tools in this module for registration
TOOLS = [
    list_datasets,
    read_dataset,
    add_dataset_example,
    create_dataset,
    remove_dataset_example,
    update_dataset,
    update_dataset_example
]
