"""
Power Agent Configuration and Demo Scenarios

The Power Agent is a pre-configured agent with access to all advanced tools,
designed to handle complex research and development tasks.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


# ============= POWER AGENT CONFIGURATION =============

POWER_AGENT_CONFIG = {
    "name": "Power Agent",
    "description": """A fully-equipped AI assistant with access to all available tools.

Capabilities:
- Web Research: Search the internet and fetch web content
- File Management: Read, write, edit, and search files in workspace
- Task Planning: Create and track tasks for complex projects
- Code Execution: Run Python code for calculations and data processing
- API Integration: Make HTTP requests to external services
- Note Taking: Use scratchpad for working memory across turns

Best for: Research projects, data analysis, content creation, coding assistance,
and any task requiring multiple tools working together.""",
    "tags": ["power", "research", "development", "full-featured"],
    "agent_type_id": 1,  # ReAct agent
}

POWER_AGENT_LLM_CONFIG = {
    "provider": "openai",
    "model": "gpt-4o",
    "temperature": 0.7,
    "max_tokens": 4000,
}

POWER_AGENT_SYSTEM_PROMPT = """You are a powerful AI research and development assistant with access to a comprehensive toolkit.

## Your Capabilities

### Web Research
- **web_search**: Search the internet for information using DuckDuckGo
- **web_fetch**: Read and extract content from any web page

### File Management (Workspace)
- **file_read**: Read files from your workspace
- **file_write**: Create or overwrite files
- **file_edit**: Make precise edits to existing files
- **file_list**: List files matching patterns
- **file_search**: Search file contents with regex

### Planning & Memory
- **task_manager**: Create, update, and track tasks for complex projects
- **scratchpad**: Store working notes and intermediate results

### Code & APIs
- **python_code_execution**: Execute Python code for calculations and data processing
- **http_request**: Make HTTP requests to external APIs

## Working Guidelines

1. **Plan First**: For complex tasks, use task_manager to break down the work into steps
2. **Research Thoroughly**: Use web_search to find information, then web_fetch to read details
3. **Document Progress**: Use scratchpad to save important findings and intermediate results
4. **Organize Output**: Save final results to files in your workspace
5. **Be Iterative**: Review your work and refine as needed

## Best Practices

- Always verify information from multiple sources when possible
- Save important data to files so it persists across conversations
- Use task_manager to track progress on multi-step projects
- Write clean, well-documented code when using python_code_execution
- Be transparent about limitations and uncertainties

You have a dedicated workspace for this session where you can create and manage files.
All file operations are relative to this workspace directory."""


# ============= DEMO SCENARIOS =============

DEMO_SCENARIOS = [
    {
        "name": "Research Assistant",
        "description": "Research a topic and create a comprehensive summary",
        "example_prompt": "Research the latest developments in quantum computing and create a summary report with key findings, major players, and future predictions. Save the report to a file.",
        "tags": ["research", "writing", "web"],
    },
    {
        "name": "Data Analyst",
        "description": "Analyze data and generate insights",
        "example_prompt": "I have sales data for Q4. Help me analyze trends, calculate key metrics, and create a summary. Use Python for calculations and save results to files.",
        "tags": ["analysis", "python", "data"],
    },
    {
        "name": "Project Planner",
        "description": "Break down a project into actionable tasks",
        "example_prompt": "Help me plan a website redesign project. Create a task list with all the steps needed, dependencies, and priorities. Track our progress as we discuss each item.",
        "tags": ["planning", "tasks", "project"],
    },
    {
        "name": "Code Helper",
        "description": "Help with coding tasks and technical problems",
        "example_prompt": "I need to build a Python script that fetches data from an API, processes it, and saves results to a CSV file. Help me write and test this code.",
        "tags": ["coding", "python", "development"],
    },
    {
        "name": "Content Creator",
        "description": "Create and organize content",
        "example_prompt": "Help me create a blog post about AI tools for productivity. Research current tools, outline the article, and write a draft. Save each section to separate files.",
        "tags": ["writing", "content", "creative"],
    },
]


# ============= UTILITY FUNCTIONS =============

def get_all_tool_ids(db: Session) -> List[int]:
    """Get IDs of all active built-in tools."""
    from ..models.tool import Tool, ToolType

    tools = db.query(Tool).filter(
        Tool.tool_type == ToolType.BUILTIN,
        Tool.is_active == True
    ).all()

    return [t.id for t in tools]


def create_power_agent_for_user(
    db: Session,
    user_id: int,
    provider_id: Optional[int] = None,
    custom_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a Power Agent for a specific user.

    Args:
        db: Database session
        user_id: User ID to create the agent for
        provider_id: Optional LLM provider ID (uses config defaults if not provided)
        custom_name: Optional custom name for the agent

    Returns:
        Dict with agent details or error
    """
    from ..models.agent import Agent, AgentVersion
    from ..models.user import User

    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"success": False, "error": "User not found"}

    # Check if user already has a Power Agent
    existing = db.query(Agent).filter(
        Agent.user_id == user_id,
        Agent.name == (custom_name or POWER_AGENT_CONFIG["name"])
    ).first()

    if existing:
        return {
            "success": False,
            "error": "Power Agent already exists for this user",
            "agent_id": existing.id
        }

    # Get all tool IDs
    tool_ids = get_all_tool_ids(db)
    if not tool_ids:
        return {"success": False, "error": "No tools available"}

    # Build LLM config
    llm_config = POWER_AGENT_LLM_CONFIG.copy()
    if provider_id:
        llm_config["provider_id"] = provider_id

    # Create the agent
    agent = Agent(
        user_id=user_id,
        name=custom_name or POWER_AGENT_CONFIG["name"],
        description=POWER_AGENT_CONFIG["description"],
        agent_type_id=POWER_AGENT_CONFIG["agent_type_id"],
        tags=POWER_AGENT_CONFIG["tags"],
        is_active=True
    )
    db.add(agent)
    db.flush()  # Get the agent ID

    # Create initial version with all tools
    version = AgentVersion(
        agent_id=agent.id,
        version_number=1,
        created_by=user_id,
        config={
            "llm_config": llm_config,
            "tool_ids": tool_ids,
            "system_prompt": POWER_AGENT_SYSTEM_PROMPT,
            "memory_config": {
                "type": "buffer",
                "context_window": 20,  # Larger context for complex tasks
            },
            "reflection_config": {
                "enabled": False,
                "depth": 1,
                "iteration_limit": 3
            }
        }
    )
    db.add(version)
    db.flush()

    # Set current version
    agent.current_version_id = version.id
    db.commit()

    logger.info(f"Created Power Agent (id={agent.id}) for user {user_id} with {len(tool_ids)} tools")

    return {
        "success": True,
        "agent_id": agent.id,
        "version_id": version.id,
        "tool_count": len(tool_ids),
        "tool_ids": tool_ids
    }


def get_demo_scenarios() -> List[Dict[str, Any]]:
    """Get list of demo scenarios for the Power Agent."""
    return DEMO_SCENARIOS


def get_power_agent_config() -> Dict[str, Any]:
    """Get the Power Agent configuration."""
    return {
        "config": POWER_AGENT_CONFIG,
        "llm_config": POWER_AGENT_LLM_CONFIG,
        "system_prompt": POWER_AGENT_SYSTEM_PROMPT,
        "demo_scenarios": DEMO_SCENARIOS
    }


def seed_builtin_agents(db: Session) -> None:
    """
    Seed built-in agents into the database.

    Built-in agents are visible to all users and cannot be modified.
    They serve as ready-to-use templates.

    Args:
        db: Database session
    """
    from ..models.agent import Agent, AgentVersion

    # Check if Power Agent already exists as built-in
    existing = db.query(Agent).filter(
        Agent.name == POWER_AGENT_CONFIG["name"],
        Agent.is_builtin == True
    ).first()

    if existing:
        # Update tool_ids in case new tools were added
        tool_ids = get_all_tool_ids(db)
        if existing.current_version and tool_ids:
            config = existing.current_version.config.copy()
            if config.get("tool_ids") != tool_ids:
                config["tool_ids"] = tool_ids
                existing.current_version.config = config
                db.commit()
                logger.info(f"Updated Power Agent tools to {len(tool_ids)} tools")
        return

    # Get all tool IDs
    tool_ids = get_all_tool_ids(db)
    if not tool_ids:
        logger.warning("No tools available for Power Agent")
        return

    # Create built-in Power Agent (no user_id)
    agent = Agent(
        user_id=None,  # Built-in agents have no owner
        name=POWER_AGENT_CONFIG["name"],
        description=POWER_AGENT_CONFIG["description"],
        agent_type_id=POWER_AGENT_CONFIG["agent_type_id"],
        tags=POWER_AGENT_CONFIG["tags"],
        is_active=True,
        is_builtin=True
    )
    db.add(agent)
    db.flush()

    # Create initial version
    # Note: created_by is required, we use 0 or create a system user
    # For simplicity, we'll need to handle this - let's check if there's a user
    from ..models.user import User
    system_user = db.query(User).first()
    created_by_id = system_user.id if system_user else 1

    version = AgentVersion(
        agent_id=agent.id,
        version_number=1,
        created_by=created_by_id,
        config={
            "llm_config": POWER_AGENT_LLM_CONFIG,
            "tool_ids": tool_ids,
            "system_prompt": POWER_AGENT_SYSTEM_PROMPT,
            "memory_config": {
                "type": "buffer",
                "context_window": 20,
            },
            "reflection_config": {
                "enabled": False,
                "depth": 1,
                "iteration_limit": 3
            }
        }
    )
    db.add(version)
    db.flush()

    # Set current version
    agent.current_version_id = version.id
    db.commit()

    logger.info(f"Created built-in Power Agent (id={agent.id}) with {len(tool_ids)} tools")
