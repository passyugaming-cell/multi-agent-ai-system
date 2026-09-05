"""Data models and metrics schemas for AI Gateway."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    """Token statistics for a single request."""

    prompt_tokens: int = Field(default=0, ge=0)
    candidate_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)


class UsageMetrics(BaseModel):
    """Aggregated token and cost metrics for AI Gateway calls."""

    total_requests: int = Field(default=0, ge=0)
    successful_requests: int = Field(default=0, ge=0)
    failed_requests: int = Field(default=0, ge=0)
    fallback_occurrences: int = Field(default=0, ge=0)
    total_prompt_tokens: int = Field(default=0, ge=0)
    total_candidate_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    total_estimated_cost_usd: float = Field(default=0.0, ge=0.0)

    def record_request(
        self,
        prompt_tokens: int,
        candidate_tokens: int,
        cost_usd: float,
        used_fallback: bool = False,
    ) -> None:
        """Record usage and cost stats for a completed request."""
        self.total_requests += 1
        self.successful_requests += 1
        self.total_prompt_tokens += prompt_tokens
        self.total_candidate_tokens += candidate_tokens
        self.total_tokens += prompt_tokens + candidate_tokens
        self.total_estimated_cost_usd += cost_usd
        if used_fallback:
            self.fallback_occurrences += 1


class GatewayResponse(BaseModel):
    """Standardized response container returned by AI Gateway."""

    data: Any = Field(..., description="Generated text content or parsed Pydantic schema.")
    model: str = Field(..., description="Model identifier used for output generation.")
    usage: TokenUsage = Field(default_factory=TokenUsage, description="Token count details.")
    estimated_cost_usd: float = Field(default=0.0, description="Estimated USD cost.")
    finish_reason: Optional[str] = Field(default=None, description="Generation finish reason.")
