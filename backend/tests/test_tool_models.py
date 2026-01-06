"""
Tests for Tool model
"""
import pytest
from sqlalchemy.exc import IntegrityError
from app.models.tool import Tool, ToolType, ToolCategory, agent_tools
from app.models.user import User
from app.models.agent import Agent
from app.security import hash_password


class TestToolModel:
    """Test cases for Tool model"""

    def test_create_builtin_tool(self, db):
        """Test creating a built-in tool"""
        tool = Tool(
            name="DuckDuckGo Search",
            description="Search the web using DuckDuckGo",
            category=ToolCategory.SEARCH,
            tags=["search", "web"],
            tool_type=ToolType.BUILTIN,
            langchain_class="DuckDuckGoSearchRun",
            required_config={}
        )
        db.add(tool)
        db.commit()
        db.refresh(tool)

        assert tool.id is not None
        assert tool.name == "DuckDuckGo Search"
        assert tool.tool_type == ToolType.BUILTIN
        assert tool.category == ToolCategory.SEARCH
        assert tool.langchain_class == "DuckDuckGoSearchRun"
        assert tool.user_id is None
        assert tool.is_active is True

    def test_create_custom_tool(self, db, test_user):
        """Test creating a custom tool"""
        tool = Tool(
            name="My Custom Tool",
            description="A custom tool for testing",
            category=ToolCategory.OTHER,
            tags=["custom"],
            tool_type=ToolType.CUSTOM,
            user_id=test_user.id,
            function_code="def run(input): return input.upper()",
            input_schema={"type": "object", "properties": {"input": {"type": "string"}}},
            output_schema={"type": "string"}
        )
        db.add(tool)
        db.commit()
        db.refresh(tool)

        assert tool.id is not None
        assert tool.tool_type == ToolType.CUSTOM
        assert tool.user_id == test_user.id
        assert tool.function_code is not None
        assert tool.input_schema is not None

    def test_tool_unique_name(self, db):
        """Test that tool names must be unique"""
        tool1 = Tool(
            name="Duplicate Tool",
            description="First tool",
            category=ToolCategory.OTHER,
            tool_type=ToolType.BUILTIN
        )
        db.add(tool1)
        db.commit()

        tool2 = Tool(
            name="Duplicate Tool",
            description="Second tool",
            category=ToolCategory.OTHER,
            tool_type=ToolType.BUILTIN
        )
        db.add(tool2)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_tool_without_name_fails(self, db):
        """Test that tool without name fails"""
        tool = Tool(
            description="No name tool",
            category=ToolCategory.OTHER,
            tool_type=ToolType.BUILTIN
        )
        db.add(tool)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_tool_categories(self, db):
        """Test different tool categories"""
        categories = [
            ToolCategory.SEARCH,
            ToolCategory.CALCULATOR,
            ToolCategory.FILESYSTEM,
            ToolCategory.API,
            ToolCategory.DATABASE,
            ToolCategory.RETRIEVAL,
            ToolCategory.PYTHON,
            ToolCategory.OTHER
        ]

        for category in categories:
            tool = Tool(
                name=f"Tool {category.value}",
                description=f"Tool for {category.value}",
                category=category,
                tool_type=ToolType.BUILTIN
            )
            db.add(tool)
            db.commit()
            db.refresh(tool)
            assert tool.category == category

    def test_query_tools_by_category(self, db):
        """Test querying tools by category"""
        # Create tools in different categories
        search_tool = Tool(
            name="Search Tool",
            description="Search tool",
            category=ToolCategory.SEARCH,
            tool_type=ToolType.BUILTIN
        )
        calc_tool = Tool(
            name="Calc Tool",
            description="Calculator tool",
            category=ToolCategory.CALCULATOR,
            tool_type=ToolType.BUILTIN
        )
        db.add_all([search_tool, calc_tool])
        db.commit()

        search_tools = db.query(Tool).filter(Tool.category == ToolCategory.SEARCH).all()
        assert len(search_tools) == 1
        assert search_tools[0].name == "Search Tool"

    def test_query_tools_by_type(self, db, test_user):
        """Test querying tools by type"""
        builtin = Tool(
            name="Built-in Tool",
            description="Built-in",
            tool_type=ToolType.BUILTIN
        )
        custom = Tool(
            name="Custom Tool",
            description="Custom",
            tool_type=ToolType.CUSTOM,
            user_id=test_user.id
        )
        db.add_all([builtin, custom])
        db.commit()

        builtin_tools = db.query(Tool).filter(Tool.tool_type == ToolType.BUILTIN).all()
        custom_tools = db.query(Tool).filter(Tool.tool_type == ToolType.CUSTOM).all()

        assert len(builtin_tools) == 1
        assert len(custom_tools) == 1

    def test_update_tool(self, db):
        """Test updating tool attributes"""
        tool = Tool(
            name="Original Name",
            description="Original description",
            category=ToolCategory.OTHER,
            tool_type=ToolType.BUILTIN
        )
        db.add(tool)
        db.commit()

        tool.name = "Updated Name"
        tool.description = "Updated description"
        tool.tags = ["updated"]
        db.commit()
        db.refresh(tool)

        assert tool.name == "Updated Name"
        assert tool.description == "Updated description"
        assert tool.tags == ["updated"]

    def test_delete_tool(self, db):
        """Test deleting a tool"""
        tool = Tool(
            name="Delete Me",
            description="To be deleted",
            tool_type=ToolType.BUILTIN
        )
        db.add(tool)
        db.commit()
        tool_id = tool.id

        db.delete(tool)
        db.commit()

        deleted = db.query(Tool).filter(Tool.id == tool_id).first()
        assert deleted is None

    def test_soft_delete_tool(self, db):
        """Test soft deleting a tool"""
        tool = Tool(
            name="Soft Delete",
            description="Soft delete test",
            tool_type=ToolType.BUILTIN
        )
        db.add(tool)
        db.commit()

        tool.is_active = False
        db.commit()
        db.refresh(tool)

        assert tool.is_active is False

    def test_tool_cascade_delete_with_user(self, db):
        """Test that deleting user cascades to custom tools"""
        user = User(
            username="tooluser",
            email="tool@example.com",
            hashed_password=hash_password("password123")
        )
        db.add(user)
        db.commit()

        tool = Tool(
            name="User Tool",
            description="User's custom tool",
            tool_type=ToolType.CUSTOM,
            user_id=user.id
        )
        db.add(tool)
        db.commit()
        tool_id = tool.id

        db.delete(user)
        db.commit()

        deleted_tool = db.query(Tool).filter(Tool.id == tool_id).first()
        assert deleted_tool is None

    def test_tool_repr(self, db):
        """Test tool string representation"""
        tool = Tool(
            name="Test Tool",
            description="Test",
            category=ToolCategory.SEARCH,
            tool_type=ToolType.BUILTIN
        )
        db.add(tool)
        db.commit()

        repr_str = repr(tool)
        assert "Tool" in repr_str
        assert str(tool.id) in repr_str
        assert "Test Tool" in repr_str
        assert "builtin" in repr_str
        assert "search" in repr_str


class TestAgentToolAssociation:
    """Test cases for agent-tool many-to-many relationship"""

    def test_assign_tool_to_agent(self, db, test_user):
        """Test assigning a tool to an agent"""
        # Create agent
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent"
        )
        db.add(agent)
        db.commit()

        # Create tool
        tool = Tool(
            name="Test Tool",
            description="Test",
            tool_type=ToolType.BUILTIN
        )
        db.add(tool)
        db.commit()

        # Assign tool to agent
        from sqlalchemy import insert
        stmt = insert(agent_tools).values(
            agent_id=agent.id,
            tool_id=tool.id,
            config={"test": "config"}
        )
        db.execute(stmt)
        db.commit()

        # Verify assignment
        result = db.execute(
            agent_tools.select().where(agent_tools.c.agent_id == agent.id)
        ).first()

        assert result is not None
        assert result.tool_id == tool.id
        assert result.config == {"test": "config"}

    def test_assign_multiple_tools_to_agent(self, db, test_user):
        """Test assigning multiple tools to an agent"""
        # Create agent
        agent = Agent(
            user_id=test_user.id,
            name="Multi-Tool Agent"
        )
        db.add(agent)
        db.commit()

        # Create tools
        tools = [
            Tool(name=f"Tool {i}", description=f"Tool {i}", tool_type=ToolType.BUILTIN)
            for i in range(3)
        ]
        db.add_all(tools)
        db.commit()

        # Assign all tools
        from sqlalchemy import insert
        for tool in tools:
            stmt = insert(agent_tools).values(
                agent_id=agent.id,
                tool_id=tool.id,
                config={}
            )
            db.execute(stmt)
        db.commit()

        # Verify assignments
        results = db.execute(
            agent_tools.select().where(agent_tools.c.agent_id == agent.id)
        ).all()

        assert len(results) == 3

    def test_agent_tool_cascade_delete(self, db, test_user):
        """Test that deleting agent cascades to agent_tools"""
        # Create agent and tool
        agent = Agent(user_id=test_user.id, name="Delete Agent")
        tool = Tool(name="Delete Tool", description="Test", tool_type=ToolType.BUILTIN)
        db.add_all([agent, tool])
        db.commit()
        agent_id = agent.id

        # Assign tool
        from sqlalchemy import insert
        stmt = insert(agent_tools).values(
            agent_id=agent.id,
            tool_id=tool.id,
            config={}
        )
        db.execute(stmt)
        db.commit()

        # Delete agent
        db.delete(agent)
        db.commit()

        # Verify assignment is deleted (query by saved agent_id)
        result = db.execute(
            agent_tools.select().where(agent_tools.c.agent_id == agent_id)
        ).first()

        assert result is None
