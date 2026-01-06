"""
MCP Server Configuration models for connecting to Model Context Protocol servers.
"""
from enum import Enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import Enum as SQLEnum

from ..database import Base


class MCPTransportType(str, Enum):
    """MCP transport types"""
    STDIO = "stdio"  # Local subprocess via stdin/stdout
    SSE = "sse"  # HTTP + Server-Sent Events (remote)
    STREAMABLE_HTTP = "streamable_http"  # HTTP streaming transport


# Association table for agent-MCP server many-to-many relationship
agent_mcp_servers = Table(
    'agent_mcp_servers',
    Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('agent_id', Integer, ForeignKey('agents.id', ondelete='CASCADE'), nullable=False, index=True),
    Column('mcp_server_id', Integer, ForeignKey('mcp_server_configs.id', ondelete='CASCADE'), nullable=False, index=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False)
)


class MCPServerConfig(Base):
    """
    MCP Server Configuration model.

    Stores configuration for connecting to MCP (Model Context Protocol) servers.
    Supports both local (stdio) and remote (SSE/HTTP) transports.

    Security:
    - Environment variables may contain secrets and are encrypted at rest
    - HTTP headers may contain auth tokens and are stored in http_config
    """
    __tablename__ = "mcp_server_configs"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Server identification
    name = Column(String(255), nullable=False)  # User-defined name
    description = Column(Text, nullable=True)

    # Transport configuration
    # Use values_callable to ensure PostgreSQL enum uses lowercase values
    transport_type = Column(
        SQLEnum(MCPTransportType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )

    # For STDIO transport: command and args to spawn subprocess
    # Example: {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"]}
    stdio_config = Column(JSON, nullable=True)

    # For SSE/HTTP transport: URL endpoint and optional headers
    # Example: {"url": "http://localhost:3000/mcp", "headers": {"Authorization": "Bearer ..."}}
    http_config = Column(JSON, nullable=True)

    # Environment variables to pass to subprocess (for stdio) - may contain secrets
    # Stored as encrypted JSON string using the same encryption as API keys
    encrypted_env_vars = Column(Text, nullable=True)

    # General configuration (additional MCP-specific settings)
    config = Column(JSON, default=dict, nullable=False)

    # Tool caching - cached list of discovered tools (refreshed on connect/test)
    cached_tools = Column(JSON, nullable=True)
    tools_last_discovered_at = Column(DateTime(timezone=True), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_connected_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="mcp_server_configs")
    agents = relationship(
        "Agent",
        secondary=agent_mcp_servers,
        back_populates="mcp_servers"
    )

    def __repr__(self):
        return f"<MCPServerConfig(id={self.id}, transport={self.transport_type.value}, name='{self.name}')>"
