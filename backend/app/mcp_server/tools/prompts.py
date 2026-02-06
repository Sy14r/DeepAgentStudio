"""MCP tools for prompt operations."""
from typing import List, Optional, Dict, Any

from mcp.types import TextContent
from sqlalchemy import or_

from ..server import mcp_tool
from ..context import MCPContext
from ..errors import ResourceNotFound, ValidationError
from ...models.prompt import Prompt, PromptVersion


@mcp_tool(
    name="prompts_list",
    description="List all prompts accessible to the user.",
    permission="prompts:list",
    input_schema={
        "type": "object",
        "properties": {
            "use_case": {
                "type": "string",
                "description": "Filter by use case"
            },
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
async def list_prompts(
    ctx: MCPContext,
    use_case: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[TextContent]:
    """List all prompts accessible to the user."""
    query = ctx.db.query(Prompt).filter(
        or_(
            Prompt.user_id == ctx.user_id,
            Prompt.is_builtin == True
        )
    )

    if use_case:
        query = query.filter(Prompt.use_case == use_case)

    total = query.count()
    prompts = query.order_by(Prompt.updated_at.desc()).offset(offset).limit(limit).all()

    result = {
        "total": total,
        "offset": offset,
        "limit": limit,
        "prompts": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "use_case": p.use_case.value if p.use_case else None,
                "is_builtin": p.is_builtin
            }
            for p in prompts
        ]
    }

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="prompts_read",
    description="Get detailed information about a specific prompt.",
    permission="prompts:read",
    input_schema={
        "type": "object",
        "properties": {
            "prompt_id": {
                "type": "integer",
                "description": "ID of the prompt to retrieve"
            }
        },
        "required": ["prompt_id"]
    }
)
async def read_prompt(ctx: MCPContext, prompt_id: int) -> List[TextContent]:
    """Get detailed information about a specific prompt."""
    prompt = ctx.db.query(Prompt).filter(
        Prompt.id == prompt_id,
        or_(
            Prompt.user_id == ctx.user_id,
            Prompt.is_builtin == True
        )
    ).first()

    if not prompt:
        raise ResourceNotFound(resource_type="prompt", resource_id=prompt_id)

    # Get current version
    current_content = None
    if prompt.current_version_id:
        version = ctx.db.query(PromptVersion).filter(
            PromptVersion.id == prompt.current_version_id
        ).first()
        if version:
            current_content = version.content

    result = {
        "id": prompt.id,
        "name": prompt.name,
        "description": prompt.description,
        "use_case": prompt.use_case.value if prompt.use_case else None,
        "message_type": prompt.message_type.value if prompt.message_type else None,
        "is_builtin": prompt.is_builtin,
        "current_version_id": prompt.current_version_id,
        "content": current_content,
        "created_at": prompt.created_at.isoformat() if prompt.created_at else None,
        "updated_at": prompt.updated_at.isoformat() if prompt.updated_at else None
    }

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="prompts_create",
    description="Create a new prompt.",
    permission="prompts:create",
    input_schema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name of the prompt"
            },
            "description": {
                "type": "string",
                "description": "Description"
            },
            "content": {
                "type": "string",
                "description": "Prompt content/template"
            },
            "use_case": {
                "type": "string",
                "description": "Use case for the prompt"
            },
            "message_type": {
                "type": "string",
                "enum": ["system", "human", "ai"],
                "description": "Message type"
            }
        },
        "required": ["name", "content"]
    }
)
async def create_prompt(
    ctx: MCPContext,
    name: str,
    content: str,
    description: Optional[str] = None,
    use_case: Optional[str] = None,
    message_type: Optional[str] = None
) -> List[TextContent]:
    """Create a new prompt."""
    from ...models.prompt import MessageType, PromptUseCase

    # Map strings to enums
    msg_type = MessageType.SYSTEM
    if message_type:
        try:
            msg_type = MessageType(message_type)
        except ValueError:
            pass

    prompt_use_case = None
    if use_case:
        try:
            prompt_use_case = PromptUseCase(use_case)
        except ValueError:
            pass

    prompt = Prompt(
        user_id=ctx.user_id,
        name=name,
        description=description or "",
        use_case=prompt_use_case,
        message_type=msg_type,
        is_builtin=False
    )
    ctx.db.add(prompt)
    ctx.db.flush()

    # Create first version
    version = PromptVersion(
        prompt_id=prompt.id,
        version_number=1,
        content=content,
        config={},
        created_by=ctx.user_id
    )
    ctx.db.add(version)
    ctx.db.flush()

    prompt.current_version_id = version.id
    ctx.db.commit()

    result = {
        "id": prompt.id,
        "name": prompt.name,
        "current_version_id": prompt.current_version_id,
        "created_at": prompt.created_at.isoformat() if prompt.created_at else None
    }

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="prompts_update",
    description="Update an existing prompt. Creates a new version.",
    permission="prompts:update",
    input_schema={
        "type": "object",
        "properties": {
            "prompt_id": {
                "type": "integer",
                "description": "ID of the prompt to update"
            },
            "name": {
                "type": "string",
                "description": "New name"
            },
            "description": {
                "type": "string",
                "description": "New description"
            },
            "content": {
                "type": "string",
                "description": "New content (creates new version)"
            }
        },
        "required": ["prompt_id"]
    }
)
async def update_prompt(
    ctx: MCPContext,
    prompt_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    content: Optional[str] = None
) -> List[TextContent]:
    """Update an existing prompt."""
    # Get prompt (must be owned by user, not builtin)
    prompt = ctx.db.query(Prompt).filter(
        Prompt.id == prompt_id,
        Prompt.user_id == ctx.user_id,
        Prompt.is_builtin == False
    ).first()

    if not prompt:
        raise ResourceNotFound(resource_type="prompt", resource_id=prompt_id)

    # Update basic fields
    if name is not None:
        prompt.name = name
    if description is not None:
        prompt.description = description

    # Create new version if content provided
    if content is not None:
        max_version = ctx.db.query(PromptVersion.version_number).filter(
            PromptVersion.prompt_id == prompt_id
        ).order_by(PromptVersion.version_number.desc()).first()

        next_version = (max_version[0] + 1) if max_version else 1

        version = PromptVersion(
            prompt_id=prompt.id,
            version_number=next_version,
            content=content,
            config={},
            created_by=ctx.user_id
        )
        ctx.db.add(version)
        ctx.db.flush()

        prompt.current_version_id = version.id

    ctx.db.commit()

    result = {
        "id": prompt.id,
        "name": prompt.name,
        "description": prompt.description,
        "current_version_id": prompt.current_version_id,
        "updated_at": prompt.updated_at.isoformat() if prompt.updated_at else None
    }

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="prompts_render",
    description="Render a prompt template with provided variables.",
    permission="prompts:read",
    input_schema={
        "type": "object",
        "properties": {
            "prompt_id": {
                "type": "integer",
                "description": "ID of the prompt to render"
            },
            "variables": {
                "type": "object",
                "description": "Variables to substitute in the template",
                "additionalProperties": {"type": "string"}
            }
        },
        "required": ["prompt_id"]
    }
)
async def render_prompt(
    ctx: MCPContext,
    prompt_id: int,
    variables: Optional[Dict[str, str]] = None
) -> List[TextContent]:
    """Render a prompt template with variables."""
    import re

    # Get prompt
    prompt = ctx.db.query(Prompt).filter(
        Prompt.id == prompt_id,
        or_(
            Prompt.user_id == ctx.user_id,
            Prompt.is_builtin == True
        )
    ).first()

    if not prompt:
        raise ResourceNotFound(resource_type="prompt", resource_id=prompt_id)

    # Get current version content
    if not prompt.current_version_id:
        raise ValidationError(message="Prompt has no content version")

    version = ctx.db.query(PromptVersion).filter(
        PromptVersion.id == prompt.current_version_id
    ).first()

    if not version:
        raise ValidationError(message="Prompt version not found")

    content = version.content
    vars_dict = variables or {}

    # Find all template variables {{var_name}}
    template_vars = set(re.findall(r'\{\{(\w+)\}\}', content))

    # Substitute variables
    rendered = content
    for var in template_vars:
        if var in vars_dict:
            rendered = rendered.replace(f'{{{{{var}}}}}', vars_dict[var])

    # Find missing variables
    missing_vars = template_vars - set(vars_dict.keys())

    result = {
        "prompt_id": prompt_id,
        "rendered_content": rendered,
        "variables_used": list(vars_dict.keys()),
        "missing_variables": list(missing_vars) if missing_vars else None
    }

    return [TextContent(type="text", text=str(result))]


@mcp_tool(
    name="prompts_clone",
    description="Clone a prompt to create an editable copy.",
    permission="prompts:create",
    input_schema={
        "type": "object",
        "properties": {
            "prompt_id": {
                "type": "integer",
                "description": "ID of the prompt to clone"
            },
            "new_name": {
                "type": "string",
                "description": "Name for the cloned prompt"
            }
        },
        "required": ["prompt_id"]
    }
)
async def clone_prompt(
    ctx: MCPContext,
    prompt_id: int,
    new_name: Optional[str] = None
) -> List[TextContent]:
    """Clone a prompt."""
    # Get source prompt
    source = ctx.db.query(Prompt).filter(
        Prompt.id == prompt_id,
        or_(
            Prompt.user_id == ctx.user_id,
            Prompt.is_builtin == True
        )
    ).first()

    if not source:
        raise ResourceNotFound(resource_type="prompt", resource_id=prompt_id)

    # Generate clone name
    clone_name = new_name or f"{source.name} (Copy)"

    # Create cloned prompt
    cloned = Prompt(
        user_id=ctx.user_id,
        name=clone_name,
        description=source.description,
        use_case=source.use_case,
        message_type=source.message_type,
        is_builtin=False
    )
    ctx.db.add(cloned)
    ctx.db.flush()

    # Clone current version
    if source.current_version_id:
        original_version = ctx.db.query(PromptVersion).filter(
            PromptVersion.id == source.current_version_id
        ).first()

        if original_version:
            cloned_version = PromptVersion(
                prompt_id=cloned.id,
                version_number=1,
                content=original_version.content,
                config=original_version.config.copy() if original_version.config else {},
                created_by=ctx.user_id
            )
            ctx.db.add(cloned_version)
            ctx.db.flush()
            cloned.current_version_id = cloned_version.id

    ctx.db.commit()

    result = {
        "id": cloned.id,
        "name": cloned.name,
        "source_prompt_id": prompt_id,
        "created_at": cloned.created_at.isoformat() if cloned.created_at else None
    }

    return [TextContent(type="text", text=str(result))]


# List of all tools in this module for registration
TOOLS = [
    list_prompts,
    read_prompt,
    create_prompt,
    update_prompt,
    render_prompt,
    clone_prompt
]
