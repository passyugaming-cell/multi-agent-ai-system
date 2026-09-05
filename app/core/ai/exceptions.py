"""Exceptions for Google GenAI client and interactions."""

try:
    from app.core.exceptions import ApplicationError
except ImportError:
    from core.exceptions import ApplicationError


class GenAIClientError(ApplicationError):
    """Base exception for GenAI client operations."""

    pass


class GenAIAuthError(GenAIClientError):
    """Raised when authentication with Google GenAI API fails."""

    pass


class GenAIModelError(GenAIClientError):
    """Raised when GenAI model execution or structured output validation fails."""

    pass


class GenAIRateLimitError(GenAIClientError):
    """Raised when GenAI API rate limit or quota is exceeded."""

    pass
