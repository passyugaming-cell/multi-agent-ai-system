"""Core exceptions proxy for Multi-Agent AI System."""

from app.core.exceptions import (
    AgentExecutionError,
    AgentInitializationError,
    AgentNotFoundError,
    ApplicationError,
    ConfigurationError,
    DatabaseError,
    DuplicateAgentError,
    MessageDeliveryError,
    MessageValidationError,
    ToolExecutionError,
)

__all__ = [
    "AgentExecutionError",
    "AgentInitializationError",
    "AgentNotFoundError",
    "ApplicationError",
    "ConfigurationError",
    "DatabaseError",
    "DuplicateAgentError",
    "MessageDeliveryError",
    "MessageValidationError",
    "ToolExecutionError",
]
