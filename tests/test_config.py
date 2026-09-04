"""Unit tests for configuration loading and secrets management."""

import pytest

from config import Settings, get_genai_client, get_settings
from core.exceptions import ConfigurationError


def test_config_loading_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test loading settings with default values when env vars are absent."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    settings = get_settings(reload=True)
    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.google_api_key is None
    assert settings.gemini_api_key is None


def test_google_api_key_primary(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that GOOGLE_API_KEY is preferred as primary key."""
    monkeypatch.setenv("GOOGLE_API_KEY", "primary_google_key")
    monkeypatch.setenv("GEMINI_API_KEY", "fallback_gemini_key")

    settings = get_settings(reload=True)
    assert settings.api_key == "primary_google_key"


def test_gemini_api_key_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that GEMINI_API_KEY is used when GOOGLE_API_KEY is missing."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "fallback_gemini_key")

    settings = get_settings(reload=True)
    assert settings.api_key == "fallback_gemini_key"


def test_missing_api_key_raises_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that accessing api_key property raises ConfigurationError if keys are absent."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    settings = get_settings(reload=True)
    with pytest.raises(ConfigurationError) as exc_info:
        _ = settings.api_key

    assert "Missing required Google GenAI API key" in str(exc_info.value)


def test_api_keys_not_exposed_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that secrets are masked in string representations."""
    monkeypatch.setenv("GOOGLE_API_KEY", "secret_key_12345")
    monkeypatch.setenv("GEMINI_API_KEY", "secret_key_67890")

    settings = get_settings(reload=True)
    representation = repr(settings)

    assert "secret_key_12345" not in representation
    assert "secret_key_67890" not in representation
    assert "***" in representation


def test_get_genai_client_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test initializing Google GenAI client when valid API key is present."""
    monkeypatch.setenv("GOOGLE_API_KEY", "fake_test_key_abc")
    settings = get_settings(reload=True)

    client = get_genai_client(settings)
    assert client is not None
