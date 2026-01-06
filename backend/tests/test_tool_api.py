"""
Tests for Tool API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from app.models.tool import Tool, ToolType, ToolCategory
from app.models.agent import Agent


class TestToolAPIEndpoints:
    """Test cases for Tool CRUD API endpoints"""

    def test_create_builtin_tool(self, client, auth_headers, db):
        """Test creating a built-in tool via API"""
        tool_data = {
            "name": "API Test Built-in Tool",
            "description": "A built-in tool created via API",
            "category": "search",
            "tags": ["test", "api"],
            "langchain_class": "TestTool",
            "required_config": {}
        }

        response = client.post(
            "/api/v1/tools/builtin",
            json=tool_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == tool_data["name"]
        assert data["tool_type"] == "builtin"
        assert data["category"] == "search"
        assert data["user_id"] is None

    def test_create_custom_tool(self, client, auth_headers, db):
        """Test creating a custom tool via API"""
        tool_data = {
            "name": "API Test Custom Tool",
            "description": "A custom tool created via API",
            "category": "other",
            "tags": ["custom", "test"],
            "function_code": "def run(input): return input.upper()",
            "input_schema": {"type": "object", "properties": {"input": {"type": "string"}}},
            "output_schema": {"type": "string"}
        }

        response = client.post(
            "/api/v1/tools/custom",
            json=tool_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == tool_data["name"]
        assert data["tool_type"] == "custom"
        assert data["function_code"] == tool_data["function_code"]
        assert data["user_id"] is not None

    def test_create_tool_duplicate_name(self, client, auth_headers, db):
        """Test that creating tool with duplicate name fails"""
        # Create first tool
        tool = Tool(
            name="Duplicate Name Tool",
            description="First tool",
            category=ToolCategory.OTHER,
            tool_type=ToolType.BUILTIN
        )
        db.add(tool)
        db.commit()

        # Try to create second tool with same name
        tool_data = {
            "name": "Duplicate Name Tool",
            "description": "Second tool",
            "category": "other",
            "tags": [],
            "langchain_class": "TestTool",
            "required_config": {}
        }

        response = client.post(
            "/api/v1/tools/builtin",
            json=tool_data,
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_list_tools(self, client, auth_headers, test_user, db):
        """Test listing tools"""
        # Create some test tools
        builtin_tool = Tool(
            name="Built-in List Tool",
            description="Built-in tool",
            category=ToolCategory.SEARCH,
            tool_type=ToolType.BUILTIN
        )
        custom_tool = Tool(
            name="Custom List Tool",
            description="Custom tool",
            category=ToolCategory.OTHER,
            tool_type=ToolType.CUSTOM,
            user_id=test_user.id
        )
        db.add_all([builtin_tool, custom_tool])
        db.commit()

        response = client.get("/api/v1/tools", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert "total" in data
        assert data["total"] >= 2
        assert len(data["tools"]) >= 2

    def test_list_tools_filter_by_category(self, client, auth_headers, db):
        """Test filtering tools by category"""
        # Create tools in different categories
        search_tool = Tool(
            name="Search Filter Tool",
            description="Search tool",
            category=ToolCategory.SEARCH,
            tool_type=ToolType.BUILTIN
        )
        calc_tool = Tool(
            name="Calc Filter Tool",
            description="Calculator tool",
            category=ToolCategory.CALCULATOR,
            tool_type=ToolType.BUILTIN
        )
        db.add_all([search_tool, calc_tool])
        db.commit()

        response = client.get(
            "/api/v1/tools?category=search",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        for tool in data["tools"]:
            assert tool["category"] == "search"

    def test_list_tools_filter_by_type(self, client, auth_headers, test_user, db):
        """Test filtering tools by type"""
        # Create tools of different types
        builtin_tool = Tool(
            name="Type Filter Built-in",
            description="Built-in",
            tool_type=ToolType.BUILTIN
        )
        custom_tool = Tool(
            name="Type Filter Custom",
            description="Custom",
            tool_type=ToolType.CUSTOM,
            user_id=test_user.id
        )
        db.add_all([builtin_tool, custom_tool])
        db.commit()

        response = client.get(
            "/api/v1/tools?tool_type=builtin",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        for tool in data["tools"]:
            assert tool["tool_type"] == "builtin"

    def test_get_tool_by_id(self, client, auth_headers, db):
        """Test getting tool by ID"""
        tool = Tool(
            name="Get Tool Test",
            description="Test tool",
            category=ToolCategory.OTHER,
            tool_type=ToolType.BUILTIN
        )
        db.add(tool)
        db.commit()

        response = client.get(
            f"/api/v1/tools/{tool.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == tool.id
        assert data["name"] == "Get Tool Test"

    def test_get_tool_not_found(self, client, auth_headers):
        """Test getting non-existent tool returns 404"""
        response = client.get(
            "/api/v1/tools/99999",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_get_custom_tool_forbidden(self, client, auth_headers, second_test_user, db):
        """Test that users cannot access other users' custom tools"""
        # Create tool for a different user
        other_tool = Tool(
            name="Other User Tool",
            description="Tool owned by different user",
            category=ToolCategory.OTHER,
            tool_type=ToolType.CUSTOM,
            user_id=second_test_user.id
        )
        db.add(other_tool)
        db.commit()

        response = client.get(
            f"/api/v1/tools/{other_tool.id}",
            headers=auth_headers
        )

        assert response.status_code == 403

    def test_update_custom_tool(self, client, auth_headers, test_user, db):
        """Test updating a custom tool"""
        tool = Tool(
            name="Update Test Tool",
            description="Original description",
            category=ToolCategory.OTHER,
            tool_type=ToolType.CUSTOM,
            user_id=test_user.id,
            function_code="def run(x): return x"
        )
        db.add(tool)
        db.commit()

        update_data = {
            "description": "Updated description",
            "tags": ["updated"]
        }

        response = client.put(
            f"/api/v1/tools/{tool.id}",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"
        assert data["tags"] == ["updated"]

    def test_update_builtin_tool_allowed(self, client, auth_headers, db):
        """Test that built-in tools can be updated (for metadata updates)"""
        tool = Tool(
            name="Builtin Update Test",
            description="Built-in tool",
            tool_type=ToolType.BUILTIN
        )
        db.add(tool)
        db.commit()

        update_data = {"description": "Updated description"}

        response = client.put(
            f"/api/v1/tools/{tool.id}",
            json=update_data,
            headers=auth_headers
        )

        # Built-in tools can be updated (API allows this for metadata updates)
        assert response.status_code == 200
        assert response.json()["description"] == "Updated description"

    def test_delete_custom_tool(self, client, auth_headers, test_user, db):
        """Test deleting a custom tool"""
        tool = Tool(
            name="Delete Test Tool",
            description="To be deleted",
            tool_type=ToolType.CUSTOM,
            user_id=test_user.id
        )
        db.add(tool)
        db.commit()
        tool_id = tool.id

        response = client.delete(
            f"/api/v1/tools/{tool_id}",
            headers=auth_headers
        )

        assert response.status_code == 204

        # Verify tool is deleted
        deleted = db.query(Tool).filter(Tool.id == tool_id).first()
        assert deleted is None

    def test_delete_builtin_tool_fails(self, client, auth_headers, db):
        """Test that built-in tools cannot be deleted"""
        tool = Tool(
            name="Builtin Delete Test",
            description="Built-in tool",
            tool_type=ToolType.BUILTIN
        )
        db.add(tool)
        db.commit()

        response = client.delete(
            f"/api/v1/tools/{tool.id}",
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "cannot be deleted" in response.json()["detail"]

    def test_unauthorized_access(self, client):
        """Test that endpoints require authentication"""
        response = client.get("/api/v1/tools")
        assert response.status_code == 401


class TestAgentToolAssociationAPI:
    """Test cases for agent-tool association API endpoints"""

    def test_assign_tools_to_agent(self, client, auth_headers, test_user, db):
        """Test assigning tools to an agent"""
        # Create agent
        agent = Agent(user_id=test_user.id, name="Tool Test Agent")
        db.add(agent)
        db.commit()

        # Create tools
        tool1 = Tool(name="Assign Tool 1", description="Test", tool_type=ToolType.BUILTIN)
        tool2 = Tool(name="Assign Tool 2", description="Test", tool_type=ToolType.BUILTIN)
        db.add_all([tool1, tool2])
        db.commit()

        # Assign tools
        assignment_data = {
            "tool_ids": [tool1.id, tool2.id],
            "config": {
                tool1.id: {"param": "value1"},
                tool2.id: {"param": "value2"}
            }
        }

        response = client.post(
            f"/api/v1/agents/{agent.id}/tools",
            json=assignment_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["tool_id"] == tool1.id
        assert data[0]["tool_name"] == "Assign Tool 1"
        assert data[0]["config"] == {"param": "value1"}

    def test_assign_tools_replaces_existing(self, client, auth_headers, test_user, db):
        """Test that assigning tools replaces existing assignments"""
        # Create agent and tools
        agent = Agent(user_id=test_user.id, name="Replace Test Agent")
        tool1 = Tool(name="Replace Tool 1", description="Test", tool_type=ToolType.BUILTIN)
        tool2 = Tool(name="Replace Tool 2", description="Test", tool_type=ToolType.BUILTIN)
        db.add_all([agent, tool1, tool2])
        db.commit()

        # First assignment
        client.post(
            f"/api/v1/agents/{agent.id}/tools",
            json={"tool_ids": [tool1.id]},
            headers=auth_headers
        )

        # Second assignment (should replace)
        response = client.post(
            f"/api/v1/agents/{agent.id}/tools",
            json={"tool_ids": [tool2.id]},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["tool_id"] == tool2.id

    def test_assign_tools_agent_not_found(self, client, auth_headers):
        """Test assigning tools to non-existent agent"""
        response = client.post(
            "/api/v1/agents/99999/tools",
            json={"tool_ids": [1]},
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_assign_invalid_tool(self, client, auth_headers, test_user, db):
        """Test assigning non-existent tool to agent"""
        agent = Agent(user_id=test_user.id, name="Invalid Tool Agent")
        db.add(agent)
        db.commit()

        response = client.post(
            f"/api/v1/agents/{agent.id}/tools",
            json={"tool_ids": [99999]},
            headers=auth_headers
        )

        assert response.status_code == 404
        assert "Tool with ID 99999 not found" in response.json()["detail"]

    def test_assign_other_users_custom_tool(self, client, auth_headers, test_user, second_test_user, db):
        """Test that users cannot assign other users' custom tools"""
        agent = Agent(user_id=test_user.id, name="Access Test Agent")
        other_tool = Tool(
            name="Other User Custom Tool",
            description="Test",
            tool_type=ToolType.CUSTOM,
            user_id=second_test_user.id
        )
        db.add_all([agent, other_tool])
        db.commit()

        response = client.post(
            f"/api/v1/agents/{agent.id}/tools",
            json={"tool_ids": [other_tool.id]},
            headers=auth_headers
        )

        assert response.status_code == 403

    def test_get_agent_tools(self, client, auth_headers, test_user, db):
        """Test getting tools assigned to an agent"""
        # Create agent and tools
        agent = Agent(user_id=test_user.id, name="Get Tools Agent")
        tool1 = Tool(name="Get Tool 1", description="Test", tool_type=ToolType.BUILTIN)
        tool2 = Tool(name="Get Tool 2", description="Test", tool_type=ToolType.BUILTIN)
        db.add_all([agent, tool1, tool2])
        db.commit()

        # Assign tools
        client.post(
            f"/api/v1/agents/{agent.id}/tools",
            json={"tool_ids": [tool1.id, tool2.id]},
            headers=auth_headers
        )

        # Get tools
        response = client.get(
            f"/api/v1/agents/{agent.id}/tools",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        tool_ids = [t["tool_id"] for t in data]
        assert tool1.id in tool_ids
        assert tool2.id in tool_ids

    def test_get_tools_for_other_users_agent(self, client, auth_headers, second_test_user, db):
        """Test that users cannot get tools for other users' agents"""
        # Create agent for different user
        other_agent = Agent(user_id=second_test_user.id, name="Other User Agent")
        db.add(other_agent)
        db.commit()

        response = client.get(
            f"/api/v1/agents/{other_agent.id}/tools",
            headers=auth_headers
        )

        # Returns 404 instead of 403 to not reveal other users' agents exist
        assert response.status_code == 404

    def test_remove_tool_from_agent(self, client, auth_headers, test_user, db):
        """Test removing a tool from an agent"""
        # Create and setup
        agent = Agent(user_id=test_user.id, name="Remove Tool Agent")
        tool = Tool(name="Remove Tool", description="Test", tool_type=ToolType.BUILTIN)
        db.add_all([agent, tool])
        db.commit()

        # Assign tool
        client.post(
            f"/api/v1/agents/{agent.id}/tools",
            json={"tool_ids": [tool.id]},
            headers=auth_headers
        )

        # Remove tool
        response = client.delete(
            f"/api/v1/agents/{agent.id}/tools/{tool.id}",
            headers=auth_headers
        )

        assert response.status_code == 204

        # Verify tool is removed
        get_response = client.get(
            f"/api/v1/agents/{agent.id}/tools",
            headers=auth_headers
        )
        assert len(get_response.json()) == 0

    def test_remove_tool_not_assigned(self, client, auth_headers, test_user, db):
        """Test removing tool that wasn't assigned returns 404"""
        agent = Agent(user_id=test_user.id, name="No Tool Agent")
        tool = Tool(name="Unassigned Tool", description="Test", tool_type=ToolType.BUILTIN)
        db.add_all([agent, tool])
        db.commit()

        response = client.delete(
            f"/api/v1/agents/{agent.id}/tools/{tool.id}",
            headers=auth_headers
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
