"""Unit tests for core/ai/genai_client.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from config import Settings
from core.ai.exceptions import GenAIAuthError, GenAIModelError
from core.ai.genai_client import AIResponse, GenAIClient


class SampleSchema(BaseModel):
    summary: str
    confidence: float


def test_genai_client_init_with_settings():
    settings = Settings(GOOGLE_API_KEY="test_key", GEMINI_MODEL="gemini-2.5-flash")
    with patch("google.genai.Client") as mock_sdk_client:
        client = GenAIClient(settings=settings)
        assert client.default_model == "gemini-2.5-flash"
        mock_sdk_client.assert_called_once_with(api_key="test_key")


def test_genai_client_init_missing_key():
    settings = Settings(GOOGLE_API_KEY=None, GEMINI_API_KEY=None)
    with pytest.raises(GenAIAuthError):
        GenAIClient(settings=settings)


def test_generate_text_success():
    settings = Settings(GOOGLE_API_KEY="test_key")
    mock_raw_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Hello world"
    mock_response.candidates = [MagicMock(finish_reason="STOP")]
    mock_response.usage_metadata = MagicMock(
        prompt_token_count=10, candidates_token_count=5, total_token_count=15
    )
    mock_raw_client.models.generate_content.return_value = mock_response

    client = GenAIClient(settings=settings, client=mock_raw_client)
    res = client.generate_text("Hi")

    assert isinstance(res, AIResponse)
    assert res.text == "Hello world"
    assert res.finish_reason == "STOP"
    assert res.usage["total_token_count"] == 15


def test_generate_text_failure_raises_model_error():
    settings = Settings(GOOGLE_API_KEY="test_key")
    mock_raw_client = MagicMock()
    mock_raw_client.models.generate_content.side_effect = Exception("API rate limit exceeded")

    client = GenAIClient(settings=settings, client=mock_raw_client)
    with pytest.raises(GenAIModelError) as exc_info:
        client.generate_text("Hi")
    assert "GenAI generation failed" in str(exc_info.value)


@pytest.mark.anyio
async def test_generate_text_async_success():
    settings = Settings(GOOGLE_API_KEY="test_key")
    mock_raw_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Async response"
    mock_raw_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    client = GenAIClient(settings=settings, client=mock_raw_client)
    res = await client.generate_text_async("Hi async")

    assert res.text == "Async response"


def test_generate_structured_success():
    settings = Settings(GOOGLE_API_KEY="test_key")
    mock_raw_client = MagicMock()
    expected_parsed = SampleSchema(summary="All good", confidence=0.95)
    mock_response = MagicMock()
    mock_response.parsed = expected_parsed
    mock_raw_client.models.generate_content.return_value = mock_response

    client = GenAIClient(settings=settings, client=mock_raw_client)
    res = client.generate_structured("Analyze", response_schema=SampleSchema)

    assert isinstance(res, SampleSchema)
    assert res.summary == "All good"
    assert res.confidence == 0.95


def test_generate_structured_json_fallback():
    settings = Settings(GOOGLE_API_KEY="test_key")
    mock_raw_client = MagicMock()
    mock_response = MagicMock()
    mock_response.parsed = None
    mock_response.text = '{"summary": "Parsed json", "confidence": 0.8}'
    mock_raw_client.models.generate_content.return_value = mock_response

    client = GenAIClient(settings=settings, client=mock_raw_client)
    res = client.generate_structured("Analyze", response_schema=SampleSchema)

    assert isinstance(res, SampleSchema)
    assert res.summary == "Parsed json"
    assert res.confidence == 0.8
