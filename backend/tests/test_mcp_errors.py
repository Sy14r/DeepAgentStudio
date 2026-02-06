"""Tests for MCP error classes."""
import pytest

from app.mcp_server.errors import (
    MCPError,
    PermissionDenied,
    ResourceNotFound,
    ValidationError,
    RateLimitExceeded,
    InternalError
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

    def test_permission_denied_without_resource(self):
        """Test PermissionDenied error without resource."""
        error = PermissionDenied(action="tools:create")

        assert error.code == "permission_denied"
        assert error.details["resource"] is None

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

    def test_rate_limit_exceeded(self):
        """Test RateLimitExceeded error."""
        error = RateLimitExceeded(limit=100, window_seconds=60)

        assert error.code == "rate_limit_exceeded"
        assert "100" in error.message
        assert error.details["limit"] == 100
        assert error.details["window_seconds"] == 60

    def test_internal_error(self):
        """Test InternalError."""
        error = InternalError()

        assert error.code == "internal_error"
        assert "internal error" in error.message.lower()

    def test_internal_error_with_message(self):
        """Test InternalError with custom message."""
        error = InternalError(message="Database connection failed")

        assert error.code == "internal_error"
        assert "Database connection failed" in error.message

    def test_mcp_error_to_dict(self):
        """Test error serialization."""
        error = PermissionDenied(action="tools:create")

        result = error.to_dict()

        assert result["error"]["code"] == "permission_denied"
        assert "message" in result["error"]
        assert "details" in result["error"]

    def test_mcp_error_is_exception(self):
        """Test that MCPError can be raised and caught."""
        with pytest.raises(MCPError) as exc_info:
            raise PermissionDenied(action="test:action")

        assert exc_info.value.code == "permission_denied"
