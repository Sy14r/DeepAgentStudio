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
            message=f"Validation error on '{field}': {reason}",
            details={"field": field, "reason": reason}
        )


class RateLimitExceeded(MCPError):
    """Raised when rate limit is exceeded."""

    def __init__(self, limit: int, window_seconds: int):
        super().__init__(
            code="rate_limit_exceeded",
            message=f"Rate limit exceeded: {limit} requests per {window_seconds} seconds",
            details={"limit": limit, "window_seconds": window_seconds}
        )


class InternalError(MCPError):
    """Raised for internal server errors."""

    def __init__(self, message: str = "An internal error occurred"):
        super().__init__(
            code="internal_error",
            message=message,
            details={}
        )
