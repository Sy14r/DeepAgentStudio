"""
Tests for MCP Server models
"""
import pytest
import json
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.models.mcp_server import MCPServerConfig, MCPTransportType, agent_mcp_servers
from app.models.agent import Agent, AgentType
from app.encryption import encrypt_api_key, decrypt_api_key


class TestMCPServerConfigModel:
    """Test cases for MCPServerConfig model"""

    def test_create_stdio_mcp_server(self, db, test_user):
        """Test creating a stdio MCP server configuration"""
        server = MCPServerConfig(
            user_id=test_user.id,
            name="Filesystem Server",
            description="Access local filesystem",
            transport_type=MCPTransportType.STDIO,
            stdio_config={
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home"]
            },
            config={},
            is_active=True
        )
        db.add(server)
        db.commit()
        db.refresh(server)

        assert server.id is not None
        assert server.name == "Filesystem Server"
        assert server.transport_type == MCPTransportType.STDIO
        assert server.stdio_config["command"] == "npx"
        assert server.is_active is True
        assert server.created_at is not None

    def test_create_sse_mcp_server(self, db, test_user):
        """Test creating an SSE MCP server configuration"""
        server = MCPServerConfig(
            user_id=test_user.id,
            name="Remote Server",
            transport_type=MCPTransportType.SSE,
            http_config={
                "url": "http://localhost:8080/mcp",
                "headers": {"Authorization": "Bearer token123"}
            },
            config={"timeout": 30}
        )
        db.add(server)
        db.commit()
        db.refresh(server)

        assert server.transport_type == MCPTransportType.SSE
        assert server.http_config["url"] == "http://localhost:8080/mcp"
        assert server.config["timeout"] == 30

    def test_create_streamable_http_server(self, db, test_user):
        """Test creating a streamable HTTP MCP server"""
        server = MCPServerConfig(
            user_id=test_user.id,
            name="HTTP Stream Server",
            transport_type=MCPTransportType.STREAMABLE_HTTP,
            http_config={
                "url": "https://api.example.com/mcp/v1"
            }
        )
        db.add(server)
        db.commit()
        db.refresh(server)

        assert server.transport_type == MCPTransportType.STREAMABLE_HTTP

    def test_encrypted_env_vars(self, db, test_user):
        """Test that environment variables are properly encrypted"""
        env_vars = {"API_KEY": "secret-123", "DEBUG": "true"}
        encrypted = encrypt_api_key(json.dumps(env_vars))

        server = MCPServerConfig(
            user_id=test_user.id,
            name="Server With Secrets",
            transport_type=MCPTransportType.STDIO,
            stdio_config={"command": "test"},
            encrypted_env_vars=encrypted
        )
        db.add(server)
        db.commit()
        db.refresh(server)

        # Verify encryption
        assert server.encrypted_env_vars is not None
        assert server.encrypted_env_vars != json.dumps(env_vars)

        # Verify decryption works
        decrypted = json.loads(decrypt_api_key(server.encrypted_env_vars))
        assert decrypted["API_KEY"] == "secret-123"
        assert decrypted["DEBUG"] == "true"

    def test_cached_tools(self, db, test_user):
        """Test caching discovered tools"""
        tools = [
            {"name": "read_file", "description": "Read file content", "input_schema": {"type": "object"}},
            {"name": "write_file", "description": "Write to file", "input_schema": {"type": "object"}},
        ]

        server = MCPServerConfig(
            user_id=test_user.id,
            name="Server With Cache",
            transport_type=MCPTransportType.STDIO,
            stdio_config={"command": "test"},
            cached_tools=tools,
            tools_last_discovered_at=datetime.utcnow()
        )
        db.add(server)
        db.commit()
        db.refresh(server)

        assert len(server.cached_tools) == 2
        assert server.cached_tools[0]["name"] == "read_file"
        assert server.tools_last_discovered_at is not None

    def test_server_user_relationship(self, db, test_user):
        """Test relationship with User"""
        server = MCPServerConfig(
            user_id=test_user.id,
            name="Test Server",
            transport_type=MCPTransportType.STDIO,
            stdio_config={"command": "test"}
        )
        db.add(server)
        db.commit()
        db.refresh(server)

        assert server.user.id == test_user.id
        assert server.user.username == test_user.username

    def test_cascade_delete_on_user(self, db, test_user):
        """Test that MCP servers are deleted when user is deleted"""
        server = MCPServerConfig(
            user_id=test_user.id,
            name="Test Server",
            transport_type=MCPTransportType.STDIO,
            stdio_config={"command": "test"}
        )
        db.add(server)
        db.commit()
        server_id = server.id

        # Delete user
        db.delete(test_user)
        db.commit()

        # Verify server is deleted
        deleted_server = db.query(MCPServerConfig).filter(
            MCPServerConfig.id == server_id
        ).first()
        assert deleted_server is None

    def test_update_connection_status(self, db, test_user):
        """Test updating connection status fields"""
        server = MCPServerConfig(
            user_id=test_user.id,
            name="Test Server",
            transport_type=MCPTransportType.STDIO,
            stdio_config={"command": "test"}
        )
        db.add(server)
        db.commit()

        # Update status
        server.last_connected_at = datetime.utcnow()
        server.last_error = None
        db.commit()
        db.refresh(server)

        assert server.last_connected_at is not None
        assert server.last_error is None

        # Simulate error
        server.last_error = "Connection timeout"
        db.commit()
        db.refresh(server)

        assert server.last_error == "Connection timeout"

    def test_server_repr(self, db, test_user):
        """Test server string representation"""
        server = MCPServerConfig(
            user_id=test_user.id,
            name="My Server",
            transport_type=MCPTransportType.SSE,
            http_config={"url": "http://test.com"}
        )
        db.add(server)
        db.commit()
        db.refresh(server)

        repr_str = repr(server)
        assert "MCPServerConfig" in repr_str
        assert "sse" in repr_str
        assert "My Server" in repr_str


class TestAgentMCPServerAssociation:
    """Test cases for Agent-MCP Server many-to-many relationship"""

    def test_assign_mcp_server_to_agent(self, db, test_user):
        """Test assigning an MCP server to an agent"""
        # Create server
        server = MCPServerConfig(
            user_id=test_user.id,
            name="Test Server",
            transport_type=MCPTransportType.STDIO,
            stdio_config={"command": "test"}
        )
        db.add(server)

        # Create agent
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.commit()

        # Assign server to agent
        agent.mcp_servers.append(server)
        db.commit()
        db.refresh(agent)

        assert len(agent.mcp_servers) == 1
        assert agent.mcp_servers[0].name == "Test Server"

    def test_multiple_servers_per_agent(self, db, test_user):
        """Test assigning multiple MCP servers to an agent"""
        # Create servers
        server1 = MCPServerConfig(
            user_id=test_user.id,
            name="Server 1",
            transport_type=MCPTransportType.STDIO,
            stdio_config={"command": "test1"}
        )
        server2 = MCPServerConfig(
            user_id=test_user.id,
            name="Server 2",
            transport_type=MCPTransportType.SSE,
            http_config={"url": "http://test.com"}
        )
        db.add_all([server1, server2])

        # Create agent
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.commit()

        # Assign both servers
        agent.mcp_servers.extend([server1, server2])
        db.commit()
        db.refresh(agent)

        assert len(agent.mcp_servers) == 2

    def test_server_shared_by_agents(self, db, test_user):
        """Test that an MCP server can be used by multiple agents"""
        # Create server
        server = MCPServerConfig(
            user_id=test_user.id,
            name="Shared Server",
            transport_type=MCPTransportType.STDIO,
            stdio_config={"command": "test"}
        )
        db.add(server)

        # Create agents
        agent1 = Agent(
            user_id=test_user.id,
            name="Agent 1",
            agent_type=AgentType.REACT
        )
        agent2 = Agent(
            user_id=test_user.id,
            name="Agent 2",
            agent_type=AgentType.REACT
        )
        db.add_all([agent1, agent2])
        db.commit()

        # Assign same server to both
        agent1.mcp_servers.append(server)
        agent2.mcp_servers.append(server)
        db.commit()

        db.refresh(server)
        assert len(server.agents) == 2

    def test_remove_mcp_server_from_agent(self, db, test_user):
        """Test removing an MCP server from an agent"""
        # Create and assign server
        server = MCPServerConfig(
            user_id=test_user.id,
            name="Test Server",
            transport_type=MCPTransportType.STDIO,
            stdio_config={"command": "test"}
        )
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent",
            agent_type=AgentType.REACT
        )
        db.add_all([server, agent])
        db.commit()

        agent.mcp_servers.append(server)
        db.commit()
        assert len(agent.mcp_servers) == 1

        # Remove server
        agent.mcp_servers.remove(server)
        db.commit()
        db.refresh(agent)

        assert len(agent.mcp_servers) == 0

    def test_cascade_delete_server_removes_associations(self, db, test_user):
        """Test that deleting a server removes agent associations"""
        # Create and assign server
        server = MCPServerConfig(
            user_id=test_user.id,
            name="Test Server",
            transport_type=MCPTransportType.STDIO,
            stdio_config={"command": "test"}
        )
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent",
            agent_type=AgentType.REACT
        )
        db.add_all([server, agent])
        db.commit()

        agent.mcp_servers.append(server)
        db.commit()

        # Delete server
        db.delete(server)
        db.commit()
        db.refresh(agent)

        assert len(agent.mcp_servers) == 0

    def test_cascade_delete_agent_removes_associations(self, db, test_user):
        """Test that deleting an agent removes server associations"""
        # Create and assign server
        server = MCPServerConfig(
            user_id=test_user.id,
            name="Test Server",
            transport_type=MCPTransportType.STDIO,
            stdio_config={"command": "test"}
        )
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent",
            agent_type=AgentType.REACT
        )
        db.add_all([server, agent])
        db.commit()

        agent.mcp_servers.append(server)
        db.commit()

        # Delete agent
        db.delete(agent)
        db.commit()
        db.refresh(server)

        assert len(server.agents) == 0


class TestMCPTransportType:
    """Test cases for MCPTransportType enum"""

    def test_transport_types(self):
        """Test all transport type values"""
        assert MCPTransportType.STDIO.value == "stdio"
        assert MCPTransportType.SSE.value == "sse"
        assert MCPTransportType.STREAMABLE_HTTP.value == "streamable_http"

    def test_transport_type_from_string(self):
        """Test creating transport type from string"""
        assert MCPTransportType("stdio") == MCPTransportType.STDIO
        assert MCPTransportType("sse") == MCPTransportType.SSE
        assert MCPTransportType("streamable_http") == MCPTransportType.STREAMABLE_HTTP

    def test_invalid_transport_type(self):
        """Test that invalid transport type raises error"""
        with pytest.raises(ValueError):
            MCPTransportType("invalid")
