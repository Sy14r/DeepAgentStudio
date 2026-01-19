"""Pydantic schemas for agent permissions."""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.models.agent_permission import PermissionPreset


class AgentPermissionCreate(BaseModel):
    """Schema for creating agent permissions."""
    agent_id: int
    preset: str = PermissionPreset.OBSERVER.value
    custom_permissions: Optional[List[str]] = None

    class Config:
        use_enum_values = True


class AgentPermissionUpdate(BaseModel):
    """Schema for updating agent permissions."""
    preset: Optional[str] = None
    custom_permissions: Optional[List[str]] = None

    class Config:
        use_enum_values = True


class AgentPermissionResponse(BaseModel):
    """Schema for agent permission responses."""
    id: int
    agent_id: int
    preset: str
    custom_permissions: Optional[List[str]]
    effective_permissions: List[str]  # Computed from preset or custom
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True
