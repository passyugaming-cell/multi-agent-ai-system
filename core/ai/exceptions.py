"""Exceptions for Google GenAI client and interactions."""

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
