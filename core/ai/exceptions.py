"""GenAI exceptions proxy for Multi-Agent AI System."""

from app.core.ai.exceptions import (
    GenAIAuthError,
    GenAIClientError,
    GenAIModelError,
    GenAIRateLimitError,
)

__all__ = [
    "GenAIAuthError",
    "GenAIClientError",
    "GenAIModelError",
    "GenAIRateLimitError",
]
