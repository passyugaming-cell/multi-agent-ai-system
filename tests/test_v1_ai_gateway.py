"""Unit tests for AI Gateway module."""

from unittest.mock import MagicMock
import pytest
from pydantic import BaseModel, Field

from app.ai_gateway.gateway import AIGateway
from app.ai_gateway.models import TokenUsage, UsageMetrics
from app.core.config import Settings


class MockOutputSchema(BaseModel):
    """Test response schema."""

    result_summary: str = Field(..., description="Summary text.")
    confidence_score: float = Field(default=0.9, ge=0.0, le=1.0)


def test_ai_gateway_cost_calculation():
    """Test that AIGateway calculates cost correctly based on model pricing."""
    gateway = AIGateway(
        settings=Settings(GOOGLE_API_KEY="test_key", GEMINI_MODEL="gemini-3.1-flash-lite"),
        client=MagicMock(),
    )
    cost = gateway.calculate_cost("gemini-3.1-flash-lite", prompt_tokens=1000, candidate_tokens=500)
    assert cost > 0.0
    assert isinstance(cost, float)


def test_ai_gateway_metrics_recording():
    """Test that UsageMetrics records token consumption and cost accurately."""
    metrics = UsageMetrics()
    metrics.record_request(prompt_tokens=100, candidate_tokens=50, cost_usd=0.0001, used_fallback=False)
    assert metrics.total_requests == 1
    assert metrics.successful_requests == 1
    assert metrics.total_prompt_tokens == 100
    assert metrics.total_candidate_tokens == 50
    assert metrics.total_tokens == 150
    assert metrics.total_estimated_cost_usd == 0.0001
    assert metrics.fallback_occurrences == 0


def test_ai_gateway_generate_structured_success():
    """Test generate_structured using Pydantic v2 response schema."""
    mock_client = MagicMock()
    mock_raw_resp = MagicMock()
    mock_raw_resp.parsed = MockOutputSchema(result_summary="Analysis completed", confidence_score=0.95)
    mock_raw_resp.usage_metadata.prompt_token_count = 50
    mock_raw_resp.usage_metadata.candidates_token_count = 25
    mock_client.models.generate_content.return_value = mock_raw_resp

    gateway = AIGateway(
        settings=Settings(GOOGLE_API_KEY="test_key", GEMINI_MODEL="gemini-3.1-flash-lite"),
        client=mock_client,
    )

    result = gateway.generate_structured("Analyze data", response_schema=MockOutputSchema)
    assert isinstance(result, MockOutputSchema)
    assert result.result_summary == "Analysis completed"
    assert result.confidence_score == 0.95
    assert gateway.metrics.total_requests == 1


def test_ai_gateway_model_fallback():
    """Test automatic fallback from primary model to fallback model when primary model fails."""
    mock_client = MagicMock()
    mock_raw_resp = MagicMock()
    mock_raw_resp.parsed = MockOutputSchema(result_summary="Fallback succeeded", confidence_score=0.88)
    mock_raw_resp.usage_metadata.prompt_token_count = 40
    mock_raw_resp.usage_metadata.candidates_token_count = 20

    # Primary model fails, fallback model succeeds
    def mock_generate(model, contents, config):
        if "3.1" in model:
            raise Exception("Primary model rate limit / unavailable")
        return mock_raw_resp

    mock_client.models.generate_content.side_effect = mock_generate

    gateway = AIGateway(
        settings=Settings(
            GOOGLE_API_KEY="test_key",
            GEMINI_MODEL="gemini-3.1-flash-lite",
            GEMINI_FALLBACK_MODEL="gemini-1.5-flash",
        ),
        client=mock_client,
        max_retries=1,
        backoff_factor=0.001,
    )

    result = gateway.generate_structured("Analyze data", response_schema=MockOutputSchema)
    assert isinstance(result, MockOutputSchema)
    assert result.result_summary == "Fallback succeeded"
    assert gateway.metrics.fallback_occurrences == 1
