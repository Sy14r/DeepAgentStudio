"""MCP tools registration."""
from ..server import register_tool


def register_all_tools():
    """Register all MCP tools with the server."""
    # Import and register agent tools
    from . import agents
    for tool in agents.TOOLS:
        register_tool(tool)

    # Import and register tool tools
    from . import tools
    for tool in tools.TOOLS:
        register_tool(tool)

    # Import and register prompt tools
    from . import prompts
    for tool in prompts.TOOLS:
        register_tool(tool)

    # Import and register dataset tools
    from . import datasets
    for tool in datasets.TOOLS:
        register_tool(tool)

    # Import and register evaluation tools
    from . import evaluations
    for tool in evaluations.TOOLS:
        register_tool(tool)

    # Import and register session/introspection tools
    from . import sessions
    for tool in sessions.TOOLS:
        register_tool(tool)
