"""Core exceptions for Multi-Agent AI System."""


class ApplicationError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class ConfigurationError(ApplicationError):
    """Raised when there is an error in application configuration."""

    pass


class AgentInitializationError(ApplicationError):
    """Raised when an agent fails to initialize."""

    pass


class ToolExecutionError(ApplicationError):
    """Raised when tool execution fails or violates security constraints."""

    pass


class DatabaseError(ApplicationError):
    """Raised when a database operation fails."""

    pass
