# MCP Server Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an embedded MCP server exposing DeepAgentStudio's configuration capabilities for agent self-improvement, tool creation, and agent spawning.

**Architecture:** FastAPI-embedded MCP server using the `mcp` Python SDK with SSE transport. Two-layer auth: session-scoped (JWT) + agent-scoped (permission presets). ~30 tools across 6 namespaces.

**Tech Stack:** Python MCP SDK, FastAPI, SQLAlchemy, Pydantic, pytest

**Design Doc:** `docs/plans/2026-01-18-mcp-server-design.md`

---

## Phase 1: Foundation

### Task 1: Add MCP SDK Dependency

**Files:**
- Modify: `backend/requirements.txt`

**Step 1: Add the mcp package**

Add to `backend/requirements.txt`:
```
mcp>=1.0.0
```

**Step 2: Rebuild backend container**

Run: `docker-compose build backend`
Expected: Build completes successfully

**Step 3: Verify installation**

Run: `docker-compose exec backend python -c "import mcp; print(mcp.__version__)"`
Expected: Version number printed (1.x.x)

**Step 4: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add mcp sdk dependency"
```

---

### Task 2: Create Permission Model

**Files:**
- Create: `backend/app/models/agent_permission.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_agent_permission_models.py`

**Step 1: Write the failing test**

Create `backend/tests/test_agent_permission_models.py`:
```python
"""Tests for AgentPermission model."""
import pytest
from sqlalchemy.exc import IntegrityError

from app.models.agent_permission import AgentPermission, PermissionPreset
from app.models.agent import Agent
from app.models.user import User
from app.utils.security import hash_password


class TestAgentPermissionModel:
    """Test cases for AgentPermission model."""

    def test_create_permission_with_preset(self, db, test_user):
        """Test creating a permission with a preset."""
        # Create an agent first
        agent = Agent(
            user_id=test_user.id,
            name="Test Agent",
            description="Test",
            is_active=True
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)

        # Create permission
        permission = AgentPermission(
            agent_id=agent.id,
            preset=PermissionPreset.SELF_IMPROVE
        )
        db.add(permission)
        db.commit()
        db.refresh(permission)

        assert permission.id is not None
        assert permission.preset == PermissionPreset.SELF_IMPROVE
        assert permission.custom_permissions is None
        assert permission.created_at is not None

    def test_create_permission_with_custom(self, db, test_user):
        """Test creating a permission with custom permissions."""
        agent = Agent(
            user_id=test_user.id,
            name="Custom Agent",
            description="Test",
            is_active=True
        )
        db.add(agent)
        db.commit()

        permission = AgentPermission(
            agent_id=agent.id,
            preset=PermissionPreset.CUSTOM,
            custom_permissions=["agents:read", "tools:create"]
        )
        db.add(permission)
        db.commit()
        db.refresh(permission)

        assert permission.preset == PermissionPreset.CUSTOM
        assert permission.custom_permissions == ["agents:read", "tools:create"]

    def test_unique_agent_constraint(self, db, test_user):
        """Test that each agent can only have one permission record."""
        agent = Agent(
            user_id=test_user.id,
            name="Unique Agent",
            description="Test",
            is_active=True
        )
        db.add(agent)
        db.commit()

        perm1 = AgentPermission(agent_id=agent.id, preset=PermissionPreset.OBSERVER)
        db.add(perm1)
        db.commit()

        perm2 = AgentPermission(agent_id=agent.id, preset=PermissionPreset.META_AGENT)
        db.add(perm2)

        with pytest.raises(IntegrityError):
            db.commit()

    def test_cascade_delete_on_agent_delete(self, db, test_user):
        """Test that permission is deleted when agent is deleted."""
        agent = Agent(
            user_id=test_user.id,
            name="Cascade Agent",
            description="Test",
            is_active=True
        )
        db.add(agent)
        db.commit()

        permission = AgentPermission(agent_id=agent.id, preset=PermissionPreset.TOOL_CREATOR)
        db.add(permission)
        db.commit()
        permission_id = permission.id

        # Delete agent
        db.delete(agent)
        db.commit()

        # Permission should be gone
        result = db.query(AgentPermission).filter(AgentPermission.id == permission_id).first()
        assert result is None

    def test_default_preset_is_observer(self, db, test_user):
        """Test that default preset is observer."""
        agent = Agent(
            user_id=test_user.id,
            name="Default Agent",
            description="Test",
            is_active=True
        )
        db.add(agent)
        db.commit()

        permission = AgentPermission(agent_id=agent.id)
        db.add(permission)
        db.commit()
        db.refresh(permission)

        assert permission.preset == PermissionPreset.OBSERVER


class TestPermissionPresetEnum:
    """Test cases for PermissionPreset enum."""

    def test_all_presets_exist(self):
        """Test that all expected presets are defined."""
        assert PermissionPreset.OBSERVER == "observer"
        assert PermissionPreset.SELF_IMPROVE == "self_improve"
        assert PermissionPreset.TOOL_CREATOR == "tool_creator"
        assert PermissionPreset.META_AGENT == "meta_agent"
        assert PermissionPreset.CUSTOM == "custom"
```

**Step 2: Run test to verify it fails**

Run: `docker-compose exec -T backend pytest tests/test_agent_permission_models.py -v`
Expected: FAIL with "cannot import name 'AgentPermission'"

**Step 3: Write the model**

Create `backend/app/models/agent_permission.py`:
```python
"""Agent permission model for MCP access control."""
from enum import Enum
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class PermissionPreset(str, Enum):
    """Permission preset levels for agents."""
    OBSERVER = "observer"
    SELF_IMPROVE = "self_improve"
    TOOL_CREATOR = "tool_creator"
    META_AGENT = "meta_agent"
    CUSTOM = "custom"


class AgentPermission(Base):
    """
    Stores MCP permissions for agents.

    Each agent can have one permission record defining what MCP tools
    it can access. Permissions are either a preset (observer, self_improve,
    tool_creator, meta_agent) or custom (explicit permission list).
    """
    __tablename__ = "agent_permissions"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(
        Integer,
        ForeignKey("agents.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    preset = Column(
        SQLEnum(PermissionPreset),
        nullable=False,
        default=PermissionPreset.OBSERVER
    )
    custom_permissions = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    agent = relationship("Agent", back_populates="mcp_permission")

    def __repr__(self):
        return f"<AgentPermission(agent_id={self.agent_id}, preset={self.preset})>"
```

**Step 4: Update Agent model to add relationship**

Modify `backend/app/models/agent.py`, add to the Agent class relationships:
```python
    # Add this relationship
    mcp_permission = relationship(
        "AgentPermission",
        back_populates="agent",
        uselist=False,
        cascade="all, delete-orphan"
    )
```

**Step 5: Update models __init__.py**

Add to `backend/app/models/__init__.py`:
```python
from app.models.agent_permission import AgentPermission, PermissionPreset
```

**Step 6: Run test to verify it passes**

Run: `docker-compose exec -T backend pytest tests/test_agent_permission_models.py -v`
Expected: All tests PASS

**Step 7: Commit**

```bash
git add backend/app/models/agent_permission.py backend/app/models/agent.py backend/app/models/__init__.py backend/tests/test_agent_permission_models.py
git commit -m "feat: add AgentPermission model for MCP access control"
```

---

### Task 3: Create Database Migration

**Files:**
- Create: `backend/alembic/versions/xxxx_add_agent_permissions.py`

**Step 1: Generate migration**

Run: `docker-compose exec backend alembic revision --autogenerate -m "add_agent_permissions_table"`
Expected: Migration file created in `backend/alembic/versions/`

**Step 2: Review generated migration**

Verify the migration contains:
- CREATE TYPE permission_preset
- CREATE TABLE agent_permissions with all columns
- Index on agent_id
- Foreign key to agents with CASCADE delete

**Step 3: Apply migration**

Run: `docker-compose exec backend alembic upgrade head`
Expected: Migration applied successfully

**Step 4: Verify table exists**

Run: `docker-compose exec deepagent_postgres psql -U deepagent -d deepagentstudio -c "\d agent_permissions"`
Expected: Table structure displayed

**Step 5: Commit**

```bash
git add backend/alembic/versions/*_add_agent_permissions*.py
git commit -m "chore: add migration for agent_permissions table"
```

---

### Task 4: Create MCP Audit Log Model

**Files:**
- Create: `backend/app/models/mcp_audit_log.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_mcp_audit_log_models.py`

**Step 1: Write the failing test**

Create `backend/tests/test_mcp_audit_log_models.py`:
```python
"""Tests for MCPAuditLog model."""
import pytest
from datetime import datetime

from app.models.mcp_audit_log import MCPAuditLog
from app.models.agent import Agent


class TestMCPAuditLogModel:
    """Test cases for MCPAuditLog model."""

    def test_create_audit_log(self, db, test_user):
        """Test creating an audit log entry."""
        log = MCPAuditLog(
            user_id=test_user.id,
            tool_name="deepagent_agents_list",
            action="agents:list",
            success=True,
            request_summary={"limit": 50}
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        assert log.id is not None
        assert log.tool_name == "deepagent_agents_list"
        assert log.success is True
        assert log.created_at is not None

    def test_create_audit_log_with_agent(self, db, test_user):
        """Test creating an audit log with agent context."""
        agent = Agent(
            user_id=test_user.id,
            name="Audit Agent",
            description="Test",
            is_active=True
        )
        db.add(agent)
        db.commit()

        log = MCPAuditLog(
            user_id=test_user.id,
            agent_id=agent.id,
            tool_name="deepagent_agents_update",
            action="agents:update:self",
            resource_type="agent",
            resource_id=agent.id,
            success=True
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        assert log.agent_id == agent.id
        assert log.resource_type == "agent"

    def test_create_audit_log_failure(self, db, test_user):
        """Test creating an audit log for a failed operation."""
        log = MCPAuditLog(
            user_id=test_user.id,
            tool_name="deepagent_agents_create",
            action="agents:create",
            success=False,
            error_code="permission_denied"
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        assert log.success is False
        assert log.error_code == "permission_denied"
```

**Step 2: Run test to verify it fails**

Run: `docker-compose exec -T backend pytest tests/test_mcp_audit_log_models.py -v`
Expected: FAIL with "cannot import name 'MCPAuditLog'"

**Step 3: Write the model**

Create `backend/app/models/mcp_audit_log.py`:
```python
"""MCP audit log model for tracking tool invocations."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class MCPAuditLog(Base):
    """
    Audit log for MCP tool invocations.

    Tracks all MCP tool calls for security auditing and debugging.
    """
    __tablename__ = "mcp_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)

    tool_name = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(Integer, nullable=True)

    success = Column(Boolean, nullable=False)
    error_code = Column(String(50), nullable=True)
    request_summary = Column(JSON, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), index=True)

    # Relationships (optional, for querying)
    user = relationship("User")
    agent = relationship("Agent")

    def __repr__(self):
        return f"<MCPAuditLog(tool={self.tool_name}, success={self.success})>"
```

**Step 4: Update models __init__.py**

Add to `backend/app/models/__init__.py`:
```python
from app.models.mcp_audit_log import MCPAuditLog
```

**Step 5: Run test to verify it passes**

Run: `docker-compose exec -T backend pytest tests/test_mcp_audit_log_models.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add backend/app/models/mcp_audit_log.py backend/app/models/__init__.py backend/tests/test_mcp_audit_log_models.py
git commit -m "feat: add MCPAuditLog model for tracking MCP tool invocations"
```

---

### Task 5: Create Migration for Audit Log

**Files:**
- Create: `backend/alembic/versions/xxxx_add_mcp_audit_logs.py`

**Step 1: Generate migration**

Run: `docker-compose exec backend alembic revision --autogenerate -m "add_mcp_audit_logs_table"`
Expected: Migration file created

**Step 2: Apply migration**

Run: `docker-compose exec backend alembic upgrade head`
Expected: Migration applied successfully

**Step 3: Verify table exists**

Run: `docker-compose exec deepagent_postgres psql -U deepagent -d deepagentstudio -c "\d mcp_audit_logs"`
Expected: Table structure displayed with indexes

**Step 4: Commit**

```bash
git add backend/alembic/versions/*_add_mcp_audit_logs*.py
git commit -m "chore: add migration for mcp_audit_logs table"
```

---

### Task 6: Create Permission Definitions

**Files:**
- Create: `backend/app/mcp_server/__init__.py`
- Create: `backend/app/mcp_server/permissions.py`
- Test: `backend/tests/test_mcp_permissions.py`

**Step 1: Create mcp_server package**

Run: `mkdir -p backend/app/mcp_server/tools`

**Step 2: Write the failing test**

Create `backend/tests/test_mcp_permissions.py`:
```python
"""Tests for MCP permission system."""
import pytest

from app.mcp_server.permissions import (
    PERMISSION_PRESETS,
    resolve_permissions,
    has_permission,
    PermissionPreset
)


class TestPermissionPresets:
    """Test permission preset definitions."""

    def test_observer_permissions(self):
        """Test observer preset has read-only permissions."""
        perms = PERMISSION_PRESETS[PermissionPreset.OBSERVER]

        assert "agents:list" in perms
        assert "agents:read" in perms
        assert "tools:list" in perms
        assert "agents:create" not in perms
        assert "agents:update:self" not in perms

    def test_self_improve_permissions(self):
        """Test self_improve preset includes observer + self-modification."""
        perms = PERMISSION_PRESETS[PermissionPreset.SELF_IMPROVE]

        # Has observer permissions
        assert "agents:list" in perms
        assert "agents:read" in perms

        # Plus self-modification
        assert "agents:update:self" in perms
        assert "prompts:create" in perms
        assert "datasets:update:examples" in perms

        # But not full create
        assert "agents:create" not in perms

    def test_tool_creator_permissions(self):
        """Test tool_creator preset includes self_improve + tool creation."""
        perms = PERMISSION_PRESETS[PermissionPreset.TOOL_CREATOR]

        # Has self_improve permissions
        assert "agents:update:self" in perms

        # Plus tool creation
        assert "tools:create" in perms
        assert "tools:update:own" in perms

        # But not agent creation
        assert "agents:create" not in perms

    def test_meta_agent_permissions(self):
        """Test meta_agent preset has full access."""
        perms = PERMISSION_PRESETS[PermissionPreset.META_AGENT]

        assert "agents:*" in perms
        assert "tools:*" in perms
        assert "prompts:*" in perms
        assert "datasets:*" in perms
        assert "evaluations:*" in perms


class TestResolvePermissions:
    """Test permission resolution."""

    def test_resolve_preset(self):
        """Test resolving a preset to permission list."""
        perms = resolve_permissions(PermissionPreset.OBSERVER, None)

        assert isinstance(perms, set)
        assert "agents:list" in perms

    def test_resolve_custom(self):
        """Test resolving custom permissions."""
        custom = ["agents:read", "tools:create"]
        perms = resolve_permissions(PermissionPreset.CUSTOM, custom)

        assert perms == {"agents:read", "tools:create"}


class TestHasPermission:
    """Test permission checking."""

    def test_exact_match(self):
        """Test exact permission match."""
        perms = {"agents:list", "agents:read"}

        assert has_permission(perms, "agents:list") is True
        assert has_permission(perms, "agents:create") is False

    def test_wildcard_match(self):
        """Test wildcard permission matching."""
        perms = {"agents:*"}

        assert has_permission(perms, "agents:list") is True
        assert has_permission(perms, "agents:create") is True
        assert has_permission(perms, "agents:update:self") is True
        assert has_permission(perms, "tools:create") is False

    def test_self_permission(self):
        """Test :self permission matching."""
        perms = {"agents:update:self"}

        # :self matches :self
        assert has_permission(perms, "agents:update:self") is True
        # :self does NOT match general :*
        assert has_permission(perms, "agents:update:other") is False

    def test_own_permission(self):
        """Test :own permission matching."""
        perms = {"tools:update:own"}

        assert has_permission(perms, "tools:update:own") is True
        assert has_permission(perms, "tools:update:other") is False
```

**Step 3: Run test to verify it fails**

Run: `docker-compose exec -T backend pytest tests/test_mcp_permissions.py -v`
Expected: FAIL with "cannot import name 'PERMISSION_PRESETS'"

**Step 4: Write the permissions module**

Create `backend/app/mcp_server/__init__.py`:
```python
"""MCP Server package for DeepAgentStudio."""
```

Create `backend/app/mcp_server/permissions.py`:
```python
"""Permission definitions and checking for MCP server."""
from typing import Optional, Set, List

from app.models.agent_permission import PermissionPreset


# Permission definitions for each preset
PERMISSION_PRESETS: dict[PermissionPreset, Set[str]] = {
    PermissionPreset.OBSERVER: {
        "agents:list",
        "agents:read",
        "tools:list",
        "tools:read",
        "prompts:list",
        "prompts:read",
        "datasets:list",
        "datasets:read",
        "evaluations:list",
        "evaluations:read",
        "sessions:read:own",
    },

    PermissionPreset.SELF_IMPROVE: {
        # Observer permissions
        "agents:list",
        "agents:read",
        "tools:list",
        "tools:read",
        "prompts:list",
        "prompts:read",
        "datasets:list",
        "datasets:read",
        "evaluations:list",
        "evaluations:read",
        "sessions:read:own",
        # Self-modification permissions
        "agents:update:self",
        "prompts:create",
        "prompts:update:own",
        "datasets:update:examples",
    },

    PermissionPreset.TOOL_CREATOR: {
        # Self-improve permissions
        "agents:list",
        "agents:read",
        "tools:list",
        "tools:read",
        "prompts:list",
        "prompts:read",
        "datasets:list",
        "datasets:read",
        "evaluations:list",
        "evaluations:read",
        "sessions:read:own",
        "agents:update:self",
        "prompts:create",
        "prompts:update:own",
        "datasets:update:examples",
        # Tool creation permissions
        "tools:create",
        "tools:update:own",
        "tools:generate_schema",
    },

    PermissionPreset.META_AGENT: {
        "agents:*",
        "tools:*",
        "prompts:*",
        "datasets:*",
        "evaluations:*",
        "sessions:read:own",
    },

    PermissionPreset.CUSTOM: set(),  # Custom uses custom_permissions field
}


def resolve_permissions(preset: PermissionPreset, custom_permissions: Optional[List[str]]) -> Set[str]:
    """
    Resolve a permission preset (or custom list) to a set of permissions.

    Args:
        preset: The permission preset
        custom_permissions: Custom permissions list (only used if preset is CUSTOM)

    Returns:
        Set of permission strings
    """
    if preset == PermissionPreset.CUSTOM:
        return set(custom_permissions or [])
    return PERMISSION_PRESETS.get(preset, set()).copy()


def has_permission(permissions: Set[str], required: str) -> bool:
    """
    Check if a permission set includes a required permission.

    Supports wildcards:
    - "agents:*" matches "agents:list", "agents:create", etc.
    - Exact matches take precedence

    Args:
        permissions: Set of granted permissions
        required: The permission to check for

    Returns:
        True if permission is granted
    """
    # Exact match
    if required in permissions:
        return True

    # Check for wildcard matches
    parts = required.split(":")
    if len(parts) >= 2:
        resource = parts[0]
        wildcard = f"{resource}:*"
        if wildcard in permissions:
            return True

    return False
```

**Step 5: Run test to verify it passes**

Run: `docker-compose exec -T backend pytest tests/test_mcp_permissions.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add backend/app/mcp_server/ backend/tests/test_mcp_permissions.py
git commit -m "feat: add MCP permission definitions and checking"
```

---

### Task 7: Create Permission Schemas

**Files:**
- Create: `backend/app/schemas/agent_permission.py`
- Modify: `backend/app/schemas/__init__.py`

**Step 1: Write the schemas**

Create `backend/app/schemas/agent_permission.py`:
```python
"""Pydantic schemas for agent permissions."""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.models.agent_permission import PermissionPreset


class AgentPermissionCreate(BaseModel):
    """Schema for creating agent permissions."""
    agent_id: int
    preset: PermissionPreset = PermissionPreset.OBSERVER
    custom_permissions: Optional[List[str]] = None

    class Config:
        use_enum_values = True


class AgentPermissionUpdate(BaseModel):
    """Schema for updating agent permissions."""
    preset: Optional[PermissionPreset] = None
    custom_permissions: Optional[List[str]] = None

    class Config:
        use_enum_values = True


class AgentPermissionResponse(BaseModel):
    """Schema for agent permission responses."""
    id: int
    agent_id: int
    preset: PermissionPreset
    custom_permissions: Optional[List[str]]
    effective_permissions: List[str]  # Computed from preset or custom
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True
```

**Step 2: Update schemas __init__.py**

Add to `backend/app/schemas/__init__.py`:
```python
from app.schemas.agent_permission import (
    AgentPermissionCreate,
    AgentPermissionUpdate,
    AgentPermissionResponse,
)
```

**Step 3: Commit**

```bash
git add backend/app/schemas/agent_permission.py backend/app/schemas/__init__.py
git commit -m "feat: add Pydantic schemas for agent permissions"
```

---

### Task 8: Add Permission API Endpoints

**Files:**
- Modify: `backend/app/api/v1/agents.py`
- Test: `backend/tests/test_agent_permission_api.py`

**Step 1: Write the failing test**

Create `backend/tests/test_agent_permission_api.py`:
```python
"""Tests for agent permission API endpoints."""
import pytest
from fastapi import status

from app.models.agent import Agent
from app.models.agent_permission import AgentPermission, PermissionPreset


class TestGetAgentPermissions:
    """Test GET /api/v1/agents/{agent_id}/permissions"""

    def test_get_permissions_success(self, client, auth_headers, db, test_user):
        """Test getting permissions for an agent."""
        # Create agent with permission
        agent = Agent(user_id=test_user.id, name="Test Agent", description="Test", is_active=True)
        db.add(agent)
        db.commit()

        permission = AgentPermission(agent_id=agent.id, preset=PermissionPreset.SELF_IMPROVE)
        db.add(permission)
        db.commit()

        response = client.get(f"/api/v1/agents/{agent.id}/permissions", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["preset"] == "self_improve"
        assert "agents:update:self" in data["effective_permissions"]

    def test_get_permissions_default_observer(self, client, auth_headers, db, test_user):
        """Test that agents without permissions default to observer."""
        agent = Agent(user_id=test_user.id, name="No Perm Agent", description="Test", is_active=True)
        db.add(agent)
        db.commit()

        response = client.get(f"/api/v1/agents/{agent.id}/permissions", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["preset"] == "observer"

    def test_get_permissions_unauthorized(self, client, db, test_user):
        """Test without authentication."""
        agent = Agent(user_id=test_user.id, name="Agent", description="Test", is_active=True)
        db.add(agent)
        db.commit()

        response = client.get(f"/api/v1/agents/{agent.id}/permissions")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_permissions_not_found(self, client, auth_headers):
        """Test with non-existent agent."""
        response = client.get("/api/v1/agents/99999/permissions", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUpdateAgentPermissions:
    """Test PUT /api/v1/agents/{agent_id}/permissions"""

    def test_update_permissions_success(self, client, auth_headers, db, test_user):
        """Test updating agent permissions."""
        agent = Agent(user_id=test_user.id, name="Update Agent", description="Test", is_active=True)
        db.add(agent)
        db.commit()

        response = client.put(
            f"/api/v1/agents/{agent.id}/permissions",
            json={"preset": "tool_creator"},
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["preset"] == "tool_creator"
        assert "tools:create" in data["effective_permissions"]

    def test_update_permissions_custom(self, client, auth_headers, db, test_user):
        """Test setting custom permissions."""
        agent = Agent(user_id=test_user.id, name="Custom Agent", description="Test", is_active=True)
        db.add(agent)
        db.commit()

        response = client.put(
            f"/api/v1/agents/{agent.id}/permissions",
            json={
                "preset": "custom",
                "custom_permissions": ["agents:read", "tools:create"]
            },
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["preset"] == "custom"
        assert set(data["effective_permissions"]) == {"agents:read", "tools:create"}

    def test_update_permissions_other_user_agent(self, client, auth_headers, db, second_test_user):
        """Test cannot update permissions for another user's agent."""
        agent = Agent(user_id=second_test_user.id, name="Other Agent", description="Test", is_active=True)
        db.add(agent)
        db.commit()

        response = client.put(
            f"/api/v1/agents/{agent.id}/permissions",
            json={"preset": "meta_agent"},
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
```

**Step 2: Run test to verify it fails**

Run: `docker-compose exec -T backend pytest tests/test_agent_permission_api.py -v`
Expected: FAIL with 404 (endpoints don't exist yet)

**Step 3: Add endpoints to agents.py**

Add to `backend/app/api/v1/agents.py`:
```python
from app.models.agent_permission import AgentPermission, PermissionPreset
from app.schemas.agent_permission import AgentPermissionUpdate, AgentPermissionResponse
from app.mcp_server.permissions import resolve_permissions


@router.get("/{agent_id}/permissions", response_model=AgentPermissionResponse)
async def get_agent_permissions(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get MCP permissions for an agent."""
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.user_id == current_user.id
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    permission = db.query(AgentPermission).filter(
        AgentPermission.agent_id == agent_id
    ).first()

    if permission:
        effective = resolve_permissions(permission.preset, permission.custom_permissions)
        return AgentPermissionResponse(
            id=permission.id,
            agent_id=permission.agent_id,
            preset=permission.preset,
            custom_permissions=permission.custom_permissions,
            effective_permissions=sorted(list(effective)),
            created_at=permission.created_at,
            updated_at=permission.updated_at
        )

    # Return default observer permissions
    from datetime import datetime
    effective = resolve_permissions(PermissionPreset.OBSERVER, None)
    return AgentPermissionResponse(
        id=0,
        agent_id=agent_id,
        preset=PermissionPreset.OBSERVER,
        custom_permissions=None,
        effective_permissions=sorted(list(effective)),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@router.put("/{agent_id}/permissions", response_model=AgentPermissionResponse)
async def update_agent_permissions(
    agent_id: int,
    data: AgentPermissionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update MCP permissions for an agent."""
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.user_id == current_user.id
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    permission = db.query(AgentPermission).filter(
        AgentPermission.agent_id == agent_id
    ).first()

    if not permission:
        # Create new permission record
        permission = AgentPermission(
            agent_id=agent_id,
            preset=data.preset or PermissionPreset.OBSERVER,
            custom_permissions=data.custom_permissions
        )
        db.add(permission)
    else:
        # Update existing
        if data.preset is not None:
            permission.preset = data.preset
        if data.custom_permissions is not None:
            permission.custom_permissions = data.custom_permissions

    db.commit()
    db.refresh(permission)

    effective = resolve_permissions(permission.preset, permission.custom_permissions)
    return AgentPermissionResponse(
        id=permission.id,
        agent_id=permission.agent_id,
        preset=permission.preset,
        custom_permissions=permission.custom_permissions,
        effective_permissions=sorted(list(effective)),
        created_at=permission.created_at,
        updated_at=permission.updated_at
    )
```

**Step 4: Run test to verify it passes**

Run: `docker-compose exec -T backend pytest tests/test_agent_permission_api.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add backend/app/api/v1/agents.py backend/tests/test_agent_permission_api.py
git commit -m "feat: add API endpoints for agent MCP permissions"
```

---

## Phase 2: MCP Server Core

### Task 9: Create MCP Server Context

**Files:**
- Create: `backend/app/mcp_server/context.py`
- Test: `backend/tests/test_mcp_context.py`

**Step 1: Write the failing test**

Create `backend/tests/test_mcp_context.py`:
```python
"""Tests for MCP server context."""
import pytest
from unittest.mock import MagicMock

from app.mcp_server.context import MCPContext, create_context, get_context, set_context


class TestMCPContext:
    """Test MCP context management."""

    def test_create_context(self):
        """Test creating a context."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1

        ctx = create_context(user=mock_user, db=mock_db, agent_id=42)

        assert ctx.user_id == 1
        assert ctx.agent_id == 42
        assert ctx.db is mock_db

    def test_context_without_agent(self):
        """Test creating context without agent (direct user call)."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1

        ctx = create_context(user=mock_user, db=mock_db)

        assert ctx.user_id == 1
        assert ctx.agent_id is None

    def test_set_and_get_context(self):
        """Test context variable setting and getting."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 5

        ctx = create_context(user=mock_user, db=mock_db, agent_id=10)
        token = set_context(ctx)

        retrieved = get_context()
        assert retrieved.user_id == 5
        assert retrieved.agent_id == 10
```

**Step 2: Run test to verify it fails**

Run: `docker-compose exec -T backend pytest tests/test_mcp_context.py -v`
Expected: FAIL with "cannot import name 'MCPContext'"

**Step 3: Write the context module**

Create `backend/app/mcp_server/context.py`:
```python
"""Request context for MCP server operations."""
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional, Any

from sqlalchemy.orm import Session


@dataclass
class MCPContext:
    """
    Context for MCP tool operations.

    Provides access to user identity, agent identity (if called by agent),
    and database session.
    """
    user_id: int
    agent_id: Optional[int]
    db: Session
    session_id: Optional[int] = None


# Context variable for async-safe storage
_mcp_context: ContextVar[Optional[MCPContext]] = ContextVar("mcp_context", default=None)


def create_context(
    user: Any,  # User model instance
    db: Session,
    agent_id: Optional[int] = None,
    session_id: Optional[int] = None
) -> MCPContext:
    """
    Create a new MCP context.

    Args:
        user: The authenticated user
        db: Database session
        agent_id: Optional agent ID if called by an agent
        session_id: Optional session ID for tracing

    Returns:
        MCPContext instance
    """
    return MCPContext(
        user_id=user.id,
        agent_id=agent_id,
        db=db,
        session_id=session_id
    )


def set_context(ctx: MCPContext) -> Any:
    """Set the current MCP context. Returns token for reset."""
    return _mcp_context.set(ctx)


def get_context() -> MCPContext:
    """
    Get the current MCP context.

    Raises:
        RuntimeError: If no context is set
    """
    ctx = _mcp_context.get()
    if ctx is None:
        raise RuntimeError("No MCP context set")
    return ctx


def reset_context(token: Any) -> None:
    """Reset context to previous value using token from set_context."""
    _mcp_context.reset(token)
```

**Step 4: Run test to verify it passes**

Run: `docker-compose exec -T backend pytest tests/test_mcp_context.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add backend/app/mcp_server/context.py backend/tests/test_mcp_context.py
git commit -m "feat: add MCP context for request-scoped state"
```

---

### Task 10: Create MCP Error Classes

**Files:**
- Create: `backend/app/mcp_server/errors.py`
- Test: `backend/tests/test_mcp_errors.py`

**Step 1: Write the failing test**

Create `backend/tests/test_mcp_errors.py`:
```python
"""Tests for MCP error classes."""
import pytest

from app.mcp_server.errors import (
    MCPError,
    PermissionDenied,
    ResourceNotFound,
    ValidationError
)


class TestMCPErrors:
    """Test MCP error classes."""

    def test_permission_denied(self):
        """Test PermissionDenied error."""
        error = PermissionDenied(action="agents:create", resource="agent")

        assert error.code == "permission_denied"
        assert "agents:create" in error.message
        assert error.details["action"] == "agents:create"
        assert error.details["resource"] == "agent"

    def test_resource_not_found(self):
        """Test ResourceNotFound error."""
        error = ResourceNotFound(resource_type="agent", resource_id=42)

        assert error.code == "not_found"
        assert "agent" in error.message
        assert error.details["resource_type"] == "agent"
        assert error.details["resource_id"] == 42

    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError(field="name", reason="cannot be empty")

        assert error.code == "validation_error"
        assert "name" in error.message
        assert error.details["field"] == "name"
        assert error.details["reason"] == "cannot be empty"

    def test_mcp_error_to_dict(self):
        """Test error serialization."""
        error = PermissionDenied(action="tools:create")

        result = error.to_dict()

        assert result["error"]["code"] == "permission_denied"
        assert "message" in result["error"]
        assert "details" in result["error"]
```

**Step 2: Run test to verify it fails**

Run: `docker-compose exec -T backend pytest tests/test_mcp_errors.py -v`
Expected: FAIL with "cannot import name 'MCPError'"

**Step 3: Write the errors module**

Create `backend/app/mcp_server/errors.py`:
```python
"""Error classes for MCP server operations."""
from typing import Optional, Dict, Any


class MCPError(Exception):
    """Base MCP error with code and details."""

    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize error to dictionary."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details
            }
        }


class PermissionDenied(MCPError):
    """Raised when agent lacks required permission."""

    def __init__(self, action: str, resource: Optional[str] = None):
        super().__init__(
            code="permission_denied",
            message=f"Permission denied for action: {action}",
            details={"action": action, "resource": resource}
        )


class ResourceNotFound(MCPError):
    """Raised when requested resource doesn't exist."""

    def __init__(self, resource_type: str, resource_id: Any):
        super().__init__(
            code="not_found",
            message=f"{resource_type} not found: {resource_id}",
            details={"resource_type": resource_type, "resource_id": resource_id}
        )


class ValidationError(MCPError):
    """Raised when input validation fails."""

    def __init__(self, field: str, reason: str):
        super().__init__(
            code="validation_error",
            message=f"Invalid {field}: {reason}",
            details={"field": field, "reason": reason}
        )


class ConflictError(MCPError):
    """Raised when resource already exists."""

    def __init__(self, resource_type: str, identifier: str):
        super().__init__(
            code="conflict",
            message=f"{resource_type} already exists: {identifier}",
            details={"resource_type": resource_type, "identifier": identifier}
        )
```

**Step 4: Run test to verify it passes**

Run: `docker-compose exec -T backend pytest tests/test_mcp_errors.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add backend/app/mcp_server/errors.py backend/tests/test_mcp_errors.py
git commit -m "feat: add MCP error classes"
```

---

### Task 11: Create MCP Auth Module

**Files:**
- Create: `backend/app/mcp_server/auth.py`
- Test: `backend/tests/test_mcp_auth.py`

**Step 1: Write the failing test**

Create `backend/tests/test_mcp_auth.py`:
```python
"""Tests for MCP auth and permission checking."""
import pytest
from unittest.mock import MagicMock, patch

from app.mcp_server.auth import require_permission, check_resource_ownership
from app.mcp_server.context import MCPContext
from app.mcp_server.errors import PermissionDenied, ResourceNotFound
from app.models.agent_permission import PermissionPreset


class TestRequirePermission:
    """Test permission requirement checking."""

    def test_allow_with_permission(self, db, test_user):
        """Test allowing action when permission exists."""
        from app.models.agent import Agent
        from app.models.agent_permission import AgentPermission

        agent = Agent(user_id=test_user.id, name="Permitted Agent", description="Test", is_active=True)
        db.add(agent)
        db.commit()

        permission = AgentPermission(agent_id=agent.id, preset=PermissionPreset.TOOL_CREATOR)
        db.add(permission)
        db.commit()

        ctx = MCPContext(user_id=test_user.id, agent_id=agent.id, db=db)

        # Should not raise
        require_permission(ctx, "tools:create")

    def test_deny_without_permission(self, db, test_user):
        """Test denying action when permission missing."""
        from app.models.agent import Agent
        from app.models.agent_permission import AgentPermission

        agent = Agent(user_id=test_user.id, name="Limited Agent", description="Test", is_active=True)
        db.add(agent)
        db.commit()

        permission = AgentPermission(agent_id=agent.id, preset=PermissionPreset.OBSERVER)
        db.add(permission)
        db.commit()

        ctx = MCPContext(user_id=test_user.id, agent_id=agent.id, db=db)

        with pytest.raises(PermissionDenied):
            require_permission(ctx, "agents:create")

    def test_allow_all_for_direct_user_call(self, db, test_user):
        """Test that direct user calls (no agent_id) are allowed."""
        ctx = MCPContext(user_id=test_user.id, agent_id=None, db=db)

        # Should not raise - direct user calls bypass agent permissions
        require_permission(ctx, "agents:create")


class TestCheckResourceOwnership:
    """Test resource ownership verification."""

    def test_allow_owned_resource(self, db, test_user):
        """Test allowing access to owned resource."""
        from app.models.agent import Agent

        agent = Agent(user_id=test_user.id, name="My Agent", description="Test", is_active=True)
        db.add(agent)
        db.commit()

        ctx = MCPContext(user_id=test_user.id, agent_id=None, db=db)

        # Should not raise
        result = check_resource_ownership(ctx, Agent, agent.id)
        assert result.name == "My Agent"

    def test_deny_other_user_resource(self, db, test_user, second_test_user):
        """Test denying access to another user's resource."""
        from app.models.agent import Agent

        other_agent = Agent(user_id=second_test_user.id, name="Other Agent", description="Test", is_active=True)
        db.add(other_agent)
        db.commit()

        ctx = MCPContext(user_id=test_user.id, agent_id=None, db=db)

        with pytest.raises(ResourceNotFound):
            check_resource_ownership(ctx, Agent, other_agent.id)

    def test_not_found_nonexistent(self, db, test_user):
        """Test not found for nonexistent resource."""
        from app.models.agent import Agent

        ctx = MCPContext(user_id=test_user.id, agent_id=None, db=db)

        with pytest.raises(ResourceNotFound):
            check_resource_ownership(ctx, Agent, 99999)
```

**Step 2: Run test to verify it fails**

Run: `docker-compose exec -T backend pytest tests/test_mcp_auth.py -v`
Expected: FAIL with "cannot import name 'require_permission'"

**Step 3: Write the auth module**

Create `backend/app/mcp_server/auth.py`:
```python
"""Authentication and authorization for MCP server."""
from typing import Type, TypeVar, Any

from sqlalchemy.orm import Session

from app.mcp_server.context import MCPContext
from app.mcp_server.permissions import resolve_permissions, has_permission
from app.mcp_server.errors import PermissionDenied, ResourceNotFound
from app.models.agent_permission import AgentPermission, PermissionPreset
from app.db.base_class import Base

T = TypeVar("T", bound=Base)


def require_permission(ctx: MCPContext, permission: str) -> None:
    """
    Check that the current context has the required permission.

    If called directly by user (no agent_id), all permissions are granted.
    If called by an agent, checks agent's permission preset.

    Args:
        ctx: The MCP context
        permission: Required permission string (e.g., "agents:create")

    Raises:
        PermissionDenied: If permission is not granted
    """
    # Direct user calls bypass agent permission checks
    if ctx.agent_id is None:
        return

    # Load agent's permissions
    agent_perm = ctx.db.query(AgentPermission).filter(
        AgentPermission.agent_id == ctx.agent_id
    ).first()

    if agent_perm:
        preset = agent_perm.preset
        custom = agent_perm.custom_permissions
    else:
        # Default to observer if no explicit permissions
        preset = PermissionPreset.OBSERVER
        custom = None

    permissions = resolve_permissions(preset, custom)

    if not has_permission(permissions, permission):
        raise PermissionDenied(action=permission)


def check_resource_ownership(
    ctx: MCPContext,
    model: Type[T],
    resource_id: int,
    user_field: str = "user_id"
) -> T:
    """
    Verify resource exists and belongs to the current user.

    Args:
        ctx: The MCP context
        model: SQLAlchemy model class
        resource_id: ID of the resource
        user_field: Name of the user_id field on the model

    Returns:
        The resource instance

    Raises:
        ResourceNotFound: If resource doesn't exist or doesn't belong to user
    """
    resource = ctx.db.query(model).filter(
        model.id == resource_id,
        getattr(model, user_field) == ctx.user_id
    ).first()

    if not resource:
        raise ResourceNotFound(
            resource_type=model.__tablename__,
            resource_id=resource_id
        )

    return resource


def check_self_or_owned(
    ctx: MCPContext,
    resource_agent_id: int
) -> bool:
    """
    Check if the resource belongs to the calling agent (self) or is owned.

    Used for :self permission checks.

    Args:
        ctx: The MCP context
        resource_agent_id: Agent ID of the resource being accessed

    Returns:
        True if this is a "self" access (agent modifying itself)
    """
    return ctx.agent_id is not None and ctx.agent_id == resource_agent_id
```

**Step 4: Run test to verify it passes**

Run: `docker-compose exec -T backend pytest tests/test_mcp_auth.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add backend/app/mcp_server/auth.py backend/tests/test_mcp_auth.py
git commit -m "feat: add MCP auth and permission checking"
```

---

### Task 12: Create MCP Server Skeleton

**Files:**
- Create: `backend/app/mcp_server/server.py`
- Create: `backend/app/mcp_server/tools/__init__.py`

**Step 1: Create the server module**

Create `backend/app/mcp_server/server.py`:
```python
"""MCP Server setup and configuration."""
from mcp.server import Server

# Create the MCP server instance
server = Server("deepagent-studio")


def get_server() -> Server:
    """Get the MCP server instance."""
    return server
```

**Step 2: Create tools package init**

Create `backend/app/mcp_server/tools/__init__.py`:
```python
"""MCP tools registration."""

def register_all_tools():
    """Register all MCP tools with the server."""
    # Import tool modules to trigger registration
    from . import introspect
    from . import agents
    from . import tools
    from . import prompts
    from . import datasets
    from . import evaluations
```

**Step 3: Commit**

```bash
git add backend/app/mcp_server/server.py backend/app/mcp_server/tools/__init__.py
git commit -m "feat: add MCP server skeleton"
```

---

### Task 13: Create Introspection Tools

**Files:**
- Create: `backend/app/mcp_server/tools/introspect.py`
- Test: `backend/tests/test_mcp_tools_introspect.py`

**Step 1: Write the failing test**

Create `backend/tests/test_mcp_tools_introspect.py`:
```python
"""Tests for MCP introspection tools."""
import pytest
from unittest.mock import MagicMock, patch

from app.mcp_server.tools.introspect import (
    deepagent_introspect_whoami,
    deepagent_introspect_get_session
)
from app.mcp_server.context import MCPContext, set_context
from app.models.agent_permission import PermissionPreset


class TestWhoamiTool:
    """Test the whoami introspection tool."""

    def test_whoami_with_agent(self, db, test_user):
        """Test whoami returns agent info when called by agent."""
        from app.models.agent import Agent
        from app.models.agent_permission import AgentPermission

        agent = Agent(user_id=test_user.id, name="Intro Agent", description="Test", is_active=True)
        db.add(agent)
        db.commit()

        permission = AgentPermission(agent_id=agent.id, preset=PermissionPreset.SELF_IMPROVE)
        db.add(permission)
        db.commit()

        ctx = MCPContext(user_id=test_user.id, agent_id=agent.id, db=db)
        set_context(ctx)

        result = deepagent_introspect_whoami()

        assert result["agent_id"] == agent.id
        assert result["agent_name"] == "Intro Agent"
        assert result["permission_preset"] == "self_improve"
        assert "agents:update:self" in result["effective_permissions"]

    def test_whoami_direct_user(self, db, test_user):
        """Test whoami returns user info when called directly."""
        ctx = MCPContext(user_id=test_user.id, agent_id=None, db=db)
        set_context(ctx)

        result = deepagent_introspect_whoami()

        assert result["agent_id"] is None
        assert result["user_id"] == test_user.id
        assert result["direct_user_access"] is True
```

**Step 2: Run test to verify it fails**

Run: `docker-compose exec -T backend pytest tests/test_mcp_tools_introspect.py -v`
Expected: FAIL with "cannot import name 'deepagent_introspect_whoami'"

**Step 3: Write the introspect tools**

Create `backend/app/mcp_server/tools/introspect.py`:
```python
"""Introspection tools for MCP server."""
from typing import Optional, Dict, Any, List

from app.mcp_server.server import server
from app.mcp_server.context import get_context
from app.mcp_server.permissions import resolve_permissions
from app.models.agent import Agent
from app.models.agent_permission import AgentPermission, PermissionPreset
from app.models.session import Session


@server.tool()
def deepagent_introspect_whoami() -> Dict[str, Any]:
    """
    Get information about the current caller (agent or user).

    Returns agent identity, permission preset, and effective permissions.
    Always allowed - no permission check required.
    """
    ctx = get_context()

    if ctx.agent_id is None:
        # Direct user call
        return {
            "user_id": ctx.user_id,
            "agent_id": None,
            "agent_name": None,
            "direct_user_access": True,
            "permission_preset": "full_access",
            "effective_permissions": ["*"],
            "message": "Direct user access - all permissions granted"
        }

    # Agent call - get agent info
    agent = ctx.db.query(Agent).filter(Agent.id == ctx.agent_id).first()

    # Get permissions
    agent_perm = ctx.db.query(AgentPermission).filter(
        AgentPermission.agent_id == ctx.agent_id
    ).first()

    if agent_perm:
        preset = agent_perm.preset
        custom = agent_perm.custom_permissions
    else:
        preset = PermissionPreset.OBSERVER
        custom = None

    permissions = resolve_permissions(preset, custom)

    return {
        "user_id": ctx.user_id,
        "agent_id": ctx.agent_id,
        "agent_name": agent.name if agent else None,
        "agent_description": agent.description if agent else None,
        "direct_user_access": False,
        "permission_preset": preset.value if isinstance(preset, PermissionPreset) else preset,
        "effective_permissions": sorted(list(permissions)),
        "custom_permissions": custom
    }


@server.tool()
def deepagent_introspect_get_session() -> Dict[str, Any]:
    """
    Get information about the current session.

    Returns session details if a session_id is set in context.
    """
    ctx = get_context()

    if ctx.session_id is None:
        return {
            "session_id": None,
            "message": "No session context"
        }

    session = ctx.db.query(Session).filter(
        Session.id == ctx.session_id,
        Session.user_id == ctx.user_id
    ).first()

    if not session:
        return {
            "session_id": ctx.session_id,
            "message": "Session not found"
        }

    return {
        "session_id": session.id,
        "agent_id": session.agent_id,
        "status": session.status,
        "started_at": session.created_at.isoformat() if session.created_at else None,
        "input_tokens": session.input_tokens,
        "output_tokens": session.output_tokens,
        "total_cost": float(session.total_cost) if session.total_cost else 0.0
    }


@server.tool()
def deepagent_introspect_list_my_versions() -> Dict[str, Any]:
    """
    List version history for the calling agent.

    Only available when called by an agent (not direct user call).
    """
    ctx = get_context()

    if ctx.agent_id is None:
        return {
            "error": "This tool is only available when called by an agent",
            "versions": []
        }

    agent = ctx.db.query(Agent).filter(Agent.id == ctx.agent_id).first()

    if not agent:
        return {
            "error": "Agent not found",
            "versions": []
        }

    versions = []
    for v in agent.versions[:10]:  # Limit to 10 most recent
        versions.append({
            "version_number": v.version_number,
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "is_current": v.id == agent.current_version_id
        })

    return {
        "agent_id": ctx.agent_id,
        "agent_name": agent.name,
        "total_versions": len(agent.versions),
        "versions": versions
    }
```

**Step 4: Run test to verify it passes**

Run: `docker-compose exec -T backend pytest tests/test_mcp_tools_introspect.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add backend/app/mcp_server/tools/introspect.py backend/tests/test_mcp_tools_introspect.py
git commit -m "feat: add MCP introspection tools (whoami, get_session, list_my_versions)"
```

---

## Phase 3: Core Resource Tools

### Task 14: Create Agent Tools

**Files:**
- Create: `backend/app/mcp_server/tools/agents.py`
- Test: `backend/tests/test_mcp_tools_agents.py`

**Step 1: Write the failing test**

Create `backend/tests/test_mcp_tools_agents.py`:
```python
"""Tests for MCP agent tools."""
import pytest
from app.mcp_server.tools.agents import (
    deepagent_agents_list,
    deepagent_agents_get,
    deepagent_agents_update
)
from app.mcp_server.context import MCPContext, set_context
from app.mcp_server.errors import PermissionDenied, ResourceNotFound
from app.models.agent import Agent
from app.models.agent_permission import AgentPermission, PermissionPreset


class TestAgentListTool:
    """Test agent list tool."""

    def test_list_agents(self, db, test_user):
        """Test listing agents."""
        # Create test agents
        agent1 = Agent(user_id=test_user.id, name="Agent 1", description="First", is_active=True)
        agent2 = Agent(user_id=test_user.id, name="Agent 2", description="Second", is_active=True)
        db.add_all([agent1, agent2])
        db.commit()

        ctx = MCPContext(user_id=test_user.id, agent_id=None, db=db)
        set_context(ctx)

        result = deepagent_agents_list()

        assert len(result["agents"]) >= 2
        names = [a["name"] for a in result["agents"]]
        assert "Agent 1" in names
        assert "Agent 2" in names

    def test_list_agents_with_search(self, db, test_user):
        """Test listing agents with search filter."""
        agent1 = Agent(user_id=test_user.id, name="Search Target", description="Find me", is_active=True)
        agent2 = Agent(user_id=test_user.id, name="Other Agent", description="Not this", is_active=True)
        db.add_all([agent1, agent2])
        db.commit()

        ctx = MCPContext(user_id=test_user.id, agent_id=None, db=db)
        set_context(ctx)

        result = deepagent_agents_list(search="Target")

        assert len(result["agents"]) == 1
        assert result["agents"][0]["name"] == "Search Target"


class TestAgentGetTool:
    """Test agent get tool."""

    def test_get_agent(self, db, test_user):
        """Test getting agent details."""
        agent = Agent(user_id=test_user.id, name="Detail Agent", description="Get me", is_active=True)
        db.add(agent)
        db.commit()

        ctx = MCPContext(user_id=test_user.id, agent_id=None, db=db)
        set_context(ctx)

        result = deepagent_agents_get(agent_id=agent.id)

        assert result["id"] == agent.id
        assert result["name"] == "Detail Agent"

    def test_get_agent_not_found(self, db, test_user):
        """Test getting non-existent agent."""
        ctx = MCPContext(user_id=test_user.id, agent_id=None, db=db)
        set_context(ctx)

        with pytest.raises(ResourceNotFound):
            deepagent_agents_get(agent_id=99999)


class TestAgentUpdateTool:
    """Test agent update tool."""

    def test_update_own_agent(self, db, test_user):
        """Test agent updating itself."""
        agent = Agent(user_id=test_user.id, name="Self Update", description="Original", is_active=True)
        db.add(agent)
        db.commit()

        permission = AgentPermission(agent_id=agent.id, preset=PermissionPreset.SELF_IMPROVE)
        db.add(permission)
        db.commit()

        ctx = MCPContext(user_id=test_user.id, agent_id=agent.id, db=db)
        set_context(ctx)

        result = deepagent_agents_update(agent_id=agent.id, description="Updated by self")

        assert result["description"] == "Updated by self"

    def test_update_other_agent_denied(self, db, test_user):
        """Test agent cannot update other agents with self_improve preset."""
        agent1 = Agent(user_id=test_user.id, name="Agent 1", description="Original", is_active=True)
        agent2 = Agent(user_id=test_user.id, name="Agent 2", description="Target", is_active=True)
        db.add_all([agent1, agent2])
        db.commit()

        permission = AgentPermission(agent_id=agent1.id, preset=PermissionPreset.SELF_IMPROVE)
        db.add(permission)
        db.commit()

        ctx = MCPContext(user_id=test_user.id, agent_id=agent1.id, db=db)
        set_context(ctx)

        with pytest.raises(PermissionDenied):
            deepagent_agents_update(agent_id=agent2.id, description="Hacked")
```

**Step 2: Run test to verify it fails**

Run: `docker-compose exec -T backend pytest tests/test_mcp_tools_agents.py -v`
Expected: FAIL with "cannot import name 'deepagent_agents_list'"

**Step 3: Write the agent tools**

Create `backend/app/mcp_server/tools/agents.py`:
```python
"""Agent management tools for MCP server."""
from typing import Optional, Dict, Any, List

from app.mcp_server.server import server
from app.mcp_server.context import get_context
from app.mcp_server.auth import require_permission, check_resource_ownership, check_self_or_owned
from app.mcp_server.errors import PermissionDenied, ResourceNotFound
from app.models.agent import Agent
from app.models.agent_permission import PermissionPreset


@server.tool()
def deepagent_agents_list(
    search: Optional[str] = None,
    include_builtin: bool = False,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """
    List agents accessible to the current user.

    Args:
        search: Optional search string for name/description
        include_builtin: Include built-in agents in results
        limit: Maximum number of results (default 50)
        offset: Offset for pagination

    Returns:
        Dictionary with list of agents and pagination info
    """
    ctx = get_context()
    require_permission(ctx, "agents:list")

    query = ctx.db.query(Agent).filter(Agent.user_id == ctx.user_id)

    if include_builtin:
        query = ctx.db.query(Agent).filter(
            (Agent.user_id == ctx.user_id) | (Agent.is_builtin == True)
        )

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Agent.name.ilike(search_filter)) |
            (Agent.description.ilike(search_filter))
        )

    total = query.count()
    agents = query.offset(offset).limit(limit).all()

    return {
        "agents": [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "is_active": a.is_active,
                "is_builtin": a.is_builtin,
                "created_at": a.created_at.isoformat() if a.created_at else None
            }
            for a in agents
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@server.tool()
def deepagent_agents_get(agent_id: int) -> Dict[str, Any]:
    """
    Get detailed information about an agent.

    Args:
        agent_id: ID of the agent to retrieve

    Returns:
        Agent details including current configuration
    """
    ctx = get_context()
    require_permission(ctx, "agents:read")

    agent = check_resource_ownership(ctx, Agent, agent_id)

    # Get current version config if available
    config = None
    if agent.current_version:
        config = agent.current_version.config

    return {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "is_active": agent.is_active,
        "is_builtin": agent.is_builtin,
        "current_version_id": agent.current_version_id,
        "config": config,
        "tags": agent.tags,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None
    }


@server.tool()
def deepagent_agents_update(
    agent_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    is_active: Optional[bool] = None,
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Update an agent's metadata.

    For config changes, use the config-specific tools.

    Args:
        agent_id: ID of the agent to update
        name: New name (optional)
        description: New description (optional)
        is_active: Active status (optional)
        tags: New tags (optional)

    Returns:
        Updated agent details
    """
    ctx = get_context()

    # Check if this is a self-update
    is_self = check_self_or_owned(ctx, agent_id)

    if is_self:
        require_permission(ctx, "agents:update:self")
    else:
        require_permission(ctx, "agents:update:*")

    agent = check_resource_ownership(ctx, Agent, agent_id)

    if name is not None:
        agent.name = name
    if description is not None:
        agent.description = description
    if is_active is not None:
        agent.is_active = is_active
    if tags is not None:
        agent.tags = tags

    ctx.db.commit()
    ctx.db.refresh(agent)

    return {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "is_active": agent.is_active,
        "tags": agent.tags,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None
    }


@server.tool()
def deepagent_agents_create(
    name: str,
    description: str,
    agent_type_id: Optional[int] = None,
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create a new agent.

    Args:
        name: Agent name
        description: Agent description
        agent_type_id: Optional agent type ID
        tags: Optional tags

    Returns:
        Created agent details
    """
    ctx = get_context()
    require_permission(ctx, "agents:create")

    agent = Agent(
        user_id=ctx.user_id,
        name=name,
        description=description,
        agent_type_id=agent_type_id,
        tags=tags or [],
        is_active=True,
        is_builtin=False
    )

    ctx.db.add(agent)
    ctx.db.commit()
    ctx.db.refresh(agent)

    return {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "is_active": agent.is_active,
        "created_at": agent.created_at.isoformat() if agent.created_at else None
    }


@server.tool()
def deepagent_agents_delete(agent_id: int) -> Dict[str, Any]:
    """
    Delete an agent.

    Args:
        agent_id: ID of the agent to delete

    Returns:
        Confirmation of deletion
    """
    ctx = get_context()
    require_permission(ctx, "agents:delete")

    agent = check_resource_ownership(ctx, Agent, agent_id)

    agent_name = agent.name
    ctx.db.delete(agent)
    ctx.db.commit()

    return {
        "deleted": True,
        "agent_id": agent_id,
        "agent_name": agent_name
    }
```

**Step 4: Run test to verify it passes**

Run: `docker-compose exec -T backend pytest tests/test_mcp_tools_agents.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add backend/app/mcp_server/tools/agents.py backend/tests/test_mcp_tools_agents.py
git commit -m "feat: add MCP agent tools (list, get, create, update, delete)"
```

---

## Remaining Tasks (Phase 3-5)

The following tasks follow the same TDD pattern established above:

### Task 15: Create Tool Management Tools
- File: `backend/app/mcp_server/tools/tools.py`
- Implements: `deepagent_tools_list`, `deepagent_tools_get`, `deepagent_tools_create`, `deepagent_tools_update`, `deepagent_tools_generate_schema`

### Task 16: Create Prompt Tools
- File: `backend/app/mcp_server/tools/prompts.py`
- Implements: `deepagent_prompts_list`, `deepagent_prompts_get`, `deepagent_prompts_create`, `deepagent_prompts_update`, `deepagent_prompts_render`

### Task 17: Create Dataset Tools
- File: `backend/app/mcp_server/tools/datasets.py`
- Implements: `deepagent_datasets_list`, `deepagent_datasets_get`, `deepagent_datasets_create`, `deepagent_datasets_add_example`, `deepagent_datasets_remove_example`

### Task 18: Create Evaluation Tools
- File: `backend/app/mcp_server/tools/evaluations.py`
- Implements: `deepagent_evaluations_list_evaluators`, `deepagent_evaluations_list_runs`, `deepagent_evaluations_run`, `deepagent_evaluations_get_results`

### Task 19: Create MCP SSE Endpoint
- File: `backend/app/api/v1/mcp.py`
- Implements FastAPI route that:
  - Authenticates via JWT
  - Creates MCP context
  - Connects SSE transport
  - Registers tools and runs server

### Task 20: Add Audit Logging
- Modify: `backend/app/mcp_server/server.py`
- Add middleware/decorator to log all tool invocations to MCPAuditLog

### Task 21: Frontend Permission Types
- File: `frontend/src/api/types.ts`
- Add: `PermissionPreset`, `AgentPermission`, `AgentPermissionUpdate`

### Task 22: Frontend Permission Hook
- File: `frontend/src/api/hooks/useAgentPermissions.ts`
- Add React Query hooks for get/update permissions

### Task 23: Frontend Permission Panel
- File: `frontend/src/components/agents/AgentPermissionsPanel.tsx`
- Add UI component for viewing/editing permissions with preset dropdown

### Task 24: Integrate Permission Panel
- Modify: `frontend/src/pages/AgentEditorPage.tsx`
- Add Permissions tab to agent editor

### Task 25: Integration Tests
- File: `backend/tests/test_mcp_integration.py`
- End-to-end tests for MCP SSE connection and tool execution

### Task 26: Documentation
- Update: `README.md` or create `docs/MCP_SERVER.md`
- Document MCP server usage, connection info, permission presets

---

## Execution Notes

- Each task creates one logical unit of functionality
- TDD pattern: write failing test → implement → verify → commit
- Run full test suite periodically: `docker-compose exec -T backend pytest -v`
- Frontend tasks can run in parallel with remaining backend tasks after Task 19
