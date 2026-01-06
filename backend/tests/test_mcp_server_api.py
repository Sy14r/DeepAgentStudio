"""
Tests for MCP Server API endpoints
"""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.models.mcp_server import MCPServerConfig, MCPTransportType
from app.models.agent import Agent, AgentType


class TestMCPServerAPIEndpoints:
    """Test cases for MCP Server CRUD API endpoints"""

    def test_create_stdio_mcp_server(self, client, auth_headers, db):
        """Test creating a stdio MCP server via API"""
        server_data = {
            "name": "Test Filesystem Server",
            "description": "A filesystem MCP server",
            "transport_type": "stdio",
            "stdio_config": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
            },
            "config": {}
        }

        response = client.post(
            "/api/v1/mcp-servers",
            json=server_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == server_data["name"]
        assert data["transport_type"] == "stdio"
        assert data["stdio_config"]["command"] == "npx"
        assert data["has_env_vars"] is False
        assert data["is_active"] is True

    def test_create_stdio_mcp_server_with_env_vars(self, client, auth_headers, db):
        """Test creating a stdio MCP server with environment variables"""
        server_data = {
            "name": "Server With Env",
            "description": "Has environment variables",
            "transport_type": "stdio",
            "stdio_config": {
                "command": "python",
                "args": ["-m", "my_mcp_server"]
            },
            "env_vars": {
                "API_KEY": "secret-key-123",
                "DEBUG": "true"
            },
            "config": {}
        }

        response = client.post(
            "/api/v1/mcp-servers",
            json=server_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["has_env_vars"] is True
        # Env vars should NOT be returned in response
        assert "env_vars" not in data
        assert "encrypted_env_vars" not in data

    def test_create_sse_mcp_server(self, client, auth_headers, db):
        """Test creating an SSE MCP server via API"""
        server_data = {
            "name": "Remote MCP Server",
            "description": "A remote SSE MCP server",
            "transport_type": "sse",
            "http_config": {
                "url": "http://localhost:8080/mcp",
                "headers": {"Authorization": "Bearer my-token"}
            },
            "config": {}
        }

        response = client.post(
            "/api/v1/mcp-servers",
            json=server_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == server_data["name"]
        assert data["transport_type"] == "sse"
        assert data["http_config"]["url"] == "http://localhost:8080/mcp"

    def test_create_streamable_http_server(self, client, auth_headers, db):
        """Test creating a streamable HTTP MCP server via API"""
        server_data = {
            "name": "HTTP Stream Server",
            "description": "A streamable HTTP MCP server",
            "transport_type": "streamable_http",
            "http_config": {
                "url": "http://api.example.com/mcp/v1"
            },
            "config": {}
        }

        response = client.post(
            "/api/v1/mcp-servers",
            json=server_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["transport_type"] == "streamable_http"

    def test_create_stdio_server_missing_command(self, client, auth_headers, db):
        """Test that creating stdio server without command fails"""
        server_data = {
            "name": "Bad Server",
            "transport_type": "stdio",
            "stdio_config": {
                "args": ["some", "args"]
            },
            "config": {}
        }

        response = client.post(
            "/api/v1/mcp-servers",
            json=server_data,
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "stdio_config with 'command'" in response.json()["detail"]

    def test_create_sse_server_missing_url(self, client, auth_headers, db):
        """Test that creating SSE server without URL fails"""
        server_data = {
            "name": "Bad SSE Server",
            "transport_type": "sse",
            "http_config": {
                "headers": {"X-Api-Key": "test"}
            },
            "config": {}
        }

        response = client.post(
            "/api/v1/mcp-servers",
            json=server_data,
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "http_config with 'url'" in response.json()["detail"]

    def test_list_mcp_servers(self, client, auth_headers, test_user, test_mcp_server_stdio, test_mcp_server_sse, db):
        """Test listing MCP servers"""
        response = client.get(
            "/api/v1/mcp-servers",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["servers"]) == 2
        assert data["page"] == 1

    def test_list_mcp_servers_active_only(self, client, auth_headers, test_user, db):
        """Test listing only active MCP servers"""
        # Create an active server
        active_server = MCPServerConfig(
            user_id=test_user.id,
            name="Active Server",
            transport_type=MCPTransportType.STDIO,
            stdio_config={"command": "test", "args": []},
            is_active=True
        )
        db.add(active_server)

        # Create an inactive server
        inactive_server = MCPServerConfig(
            user_id=test_user.id,
            name="Inactive Server",
            transport_type=MCPTransportType.STDIO,
            stdio_config={"command": "test", "args": []},
            is_active=False
        )
        db.add(inactive_server)
        db.commit()

        response = client.get(
            "/api/v1/mcp-servers?active_only=true",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["servers"][0]["name"] == "Active Server"

    def test_list_mcp_servers_pagination(self, client, auth_headers, test_user, db):
        """Test MCP servers pagination"""
        # Create multiple servers
        for i in range(5):
            server = MCPServerConfig(
                user_id=test_user.id,
                name=f"Server {i}",
                transport_type=MCPTransportType.STDIO,
                stdio_config={"command": "test", "args": []},
            )
            db.add(server)
        db.commit()

        # Get first page
        response = client.get(
            "/api/v1/mcp-servers?limit=2",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["servers"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2

        # Get second page
        response = client.get(
            "/api/v1/mcp-servers?skip=2&limit=2",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["servers"]) == 2
        assert data["page"] == 2

    def test_get_mcp_server(self, client, auth_headers, test_mcp_server_stdio, db):
        """Test getting a single MCP server"""
        response = client.get(
            f"/api/v1/mcp-servers/{test_mcp_server_stdio.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_mcp_server_stdio.id
        assert data["name"] == "Test Stdio MCP Server"
        assert data["transport_type"] == "stdio"
        assert data["has_env_vars"] is True

    def test_get_mcp_server_not_found(self, client, auth_headers, db):
        """Test getting non-existent MCP server returns 404"""
        response = client.get(
            "/api/v1/mcp-servers/99999",
            headers=auth_headers
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_mcp_server_other_user(self, client, auth_headers, second_test_user, db):
        """Test that users cannot access other users' MCP servers"""
        # Create server for second user
        server = MCPServerConfig(
            user_id=second_test_user.id,
            name="Other User Server",
            transport_type=MCPTransportType.STDIO,
            stdio_config={"command": "test", "args": []},
        )
        db.add(server)
        db.commit()

        # Try to access with first user's auth
        response = client.get(
            f"/api/v1/mcp-servers/{server.id}",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_update_mcp_server(self, client, auth_headers, test_mcp_server_stdio, db):
        """Test updating an MCP server"""
        update_data = {
            "name": "Updated Server Name",
            "description": "Updated description",
            "is_active": False
        }

        response = client.put(
            f"/api/v1/mcp-servers/{test_mcp_server_stdio.id}",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Server Name"
        assert data["description"] == "Updated description"
        assert data["is_active"] is False

    def test_update_mcp_server_stdio_config(self, client, auth_headers, test_mcp_server_stdio, db):
        """Test updating stdio config"""
        update_data = {
            "stdio_config": {
                "command": "python",
                "args": ["-m", "new_server"]
            }
        }

        response = client.put(
            f"/api/v1/mcp-servers/{test_mcp_server_stdio.id}",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["stdio_config"]["command"] == "python"
        assert data["stdio_config"]["args"] == ["-m", "new_server"]

    def test_update_mcp_server_clear_env_vars(self, client, auth_headers, test_mcp_server_stdio, db):
        """Test clearing environment variables"""
        # First verify it has env vars
        response = client.get(
            f"/api/v1/mcp-servers/{test_mcp_server_stdio.id}",
            headers=auth_headers
        )
        assert response.json()["has_env_vars"] is True

        # Clear env vars
        update_data = {
            "env_vars": {}
        }

        response = client.put(
            f"/api/v1/mcp-servers/{test_mcp_server_stdio.id}",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["has_env_vars"] is False

    def test_update_mcp_server_not_found(self, client, auth_headers, db):
        """Test updating non-existent server returns 404"""
        update_data = {"name": "New Name"}

        response = client.put(
            "/api/v1/mcp-servers/99999",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_delete_mcp_server(self, client, auth_headers, test_mcp_server_stdio, db):
        """Test deleting an MCP server"""
        server_id = test_mcp_server_stdio.id

        response = client.delete(
            f"/api/v1/mcp-servers/{server_id}",
            headers=auth_headers
        )

        assert response.status_code == 204

        # Verify it's deleted
        response = client.get(
            f"/api/v1/mcp-servers/{server_id}",
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_delete_mcp_server_not_found(self, client, auth_headers, db):
        """Test deleting non-existent server returns 404"""
        response = client.delete(
            "/api/v1/mcp-servers/99999",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_unauthorized_access(self, client, db):
        """Test that unauthenticated requests are rejected"""
        response = client.get("/api/v1/mcp-servers")
        assert response.status_code == 401

        response = client.post(
            "/api/v1/mcp-servers",
            json={"name": "test", "transport_type": "stdio"}
        )
        assert response.status_code == 401


class TestMCPServerTestEndpoint:
    """Test cases for MCP Server connection testing"""

    @patch('app.api.v1.mcp_servers.test_mcp_connection')
    def test_test_mcp_server_success(self, mock_test, client, auth_headers, test_mcp_server_stdio, db):
        """Test successful MCP server connection test"""
        mock_test.return_value = {
            "success": True,
            "message": "Connected successfully",
            "tools_count": 3,
            "tools": [
                {"name": "read_file", "description": "Read a file", "input_schema": {}},
                {"name": "write_file", "description": "Write a file", "input_schema": {}},
                {"name": "list_dir", "description": "List directory", "input_schema": {}},
            ],
            "latency_ms": 150
        }

        response = client.post(
            f"/api/v1/mcp-servers/{test_mcp_server_stdio.id}/test",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["tools_count"] == 3
        assert data["latency_ms"] == 150

    @patch('app.api.v1.mcp_servers.test_mcp_connection')
    def test_test_mcp_server_failure(self, mock_test, client, auth_headers, test_mcp_server_stdio, db):
        """Test failed MCP server connection test"""
        mock_test.return_value = {
            "success": False,
            "message": "Connection refused",
            "tools_count": 0
        }

        response = client.post(
            f"/api/v1/mcp-servers/{test_mcp_server_stdio.id}/test",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Connection refused" in data["message"]
        assert data["tools_count"] == 0

    def test_test_mcp_server_not_found(self, client, auth_headers, db):
        """Test testing non-existent server returns 404"""
        response = client.post(
            "/api/v1/mcp-servers/99999/test",
            headers=auth_headers
        )

        assert response.status_code == 404


class TestMCPServerToolsEndpoint:
    """Test cases for MCP Server tools discovery"""

    def test_get_cached_tools(self, client, auth_headers, test_mcp_server_stdio, db):
        """Test getting cached tools"""
        # Add cached tools to the server
        test_mcp_server_stdio.cached_tools = [
            {"name": "tool1", "description": "First tool", "input_schema": {}},
            {"name": "tool2", "description": "Second tool", "input_schema": {}},
        ]
        db.commit()

        response = client.get(
            f"/api/v1/mcp-servers/{test_mcp_server_stdio.id}/tools",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["cached"] is True
        assert len(data["tools"]) == 2
        assert data["server_id"] == test_mcp_server_stdio.id

    @patch('app.api.v1.mcp_servers.test_mcp_connection')
    def test_refresh_tools(self, mock_test, client, auth_headers, test_mcp_server_stdio, db):
        """Test refreshing tools from server"""
        mock_test.return_value = {
            "success": True,
            "message": "Connected",
            "tools_count": 2,
            "tools": [
                {"name": "new_tool", "description": "New tool", "input_schema": {}},
                {"name": "another_tool", "description": "Another tool", "input_schema": {}},
            ]
        }

        response = client.get(
            f"/api/v1/mcp-servers/{test_mcp_server_stdio.id}/tools?refresh=true",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["cached"] is False
        assert len(data["tools"]) == 2
        assert data["tools"][0]["name"] == "new_tool"

    @patch('app.api.v1.mcp_servers.test_mcp_connection')
    def test_get_tools_no_cache_triggers_refresh(self, mock_test, client, auth_headers, test_mcp_server_sse, db):
        """Test that requesting tools without cache triggers refresh"""
        mock_test.return_value = {
            "success": True,
            "message": "Connected",
            "tools_count": 1,
            "tools": [
                {"name": "remote_tool", "description": "Remote tool", "input_schema": {}},
            ]
        }

        # test_mcp_server_sse has no cached tools
        response = client.get(
            f"/api/v1/mcp-servers/{test_mcp_server_sse.id}/tools",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["cached"] is False
        assert len(data["tools"]) == 1

    @patch('app.api.v1.mcp_servers.test_mcp_connection')
    def test_get_tools_connection_failure(self, mock_test, client, auth_headers, test_mcp_server_sse, db):
        """Test tools request when connection fails"""
        mock_test.return_value = {
            "success": False,
            "message": "Server unreachable",
            "tools_count": 0
        }

        response = client.get(
            f"/api/v1/mcp-servers/{test_mcp_server_sse.id}/tools?refresh=true",
            headers=auth_headers
        )

        assert response.status_code == 502
        assert "Failed to connect" in response.json()["detail"]


class TestAgentMCPServerAssignment:
    """Test cases for Agent-MCP Server assignment endpoints"""

    def test_assign_mcp_servers_to_agent(self, client, auth_headers, test_user, test_mcp_server_stdio, test_mcp_server_sse, db):
        """Test assigning MCP servers to an agent"""
        # Create an agent
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.commit()

        # Assign MCP servers
        response = client.post(
            f"/api/v1/agents/{agent.id}/mcp-servers",
            json={"mcp_server_ids": [test_mcp_server_stdio.id, test_mcp_server_sse.id]},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_get_agent_mcp_servers(self, client, auth_headers, test_user, test_mcp_server_stdio, db):
        """Test getting MCP servers assigned to an agent"""
        # Create an agent with MCP server
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent",
            agent_type=AgentType.REACT
        )
        agent.mcp_servers.append(test_mcp_server_stdio)
        db.add(agent)
        db.commit()

        response = client.get(
            f"/api/v1/agents/{agent.id}/mcp-servers",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Stdio MCP Server"

    def test_remove_mcp_server_from_agent(self, client, auth_headers, test_user, test_mcp_server_stdio, db):
        """Test removing an MCP server from an agent"""
        # Create an agent with MCP server
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent",
            agent_type=AgentType.REACT
        )
        agent.mcp_servers.append(test_mcp_server_stdio)
        db.add(agent)
        db.commit()

        response = client.delete(
            f"/api/v1/agents/{agent.id}/mcp-servers/{test_mcp_server_stdio.id}",
            headers=auth_headers
        )

        assert response.status_code == 204

        # Verify it's removed
        response = client.get(
            f"/api/v1/agents/{agent.id}/mcp-servers",
            headers=auth_headers
        )
        assert len(response.json()) == 0

    def test_assign_nonexistent_mcp_server(self, client, auth_headers, test_user, db):
        """Test assigning non-existent MCP server fails"""
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent",
            agent_type=AgentType.REACT
        )
        db.add(agent)
        db.commit()

        response = client.post(
            f"/api/v1/agents/{agent.id}/mcp-servers",
            json={"mcp_server_ids": [99999]},
            headers=auth_headers
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
