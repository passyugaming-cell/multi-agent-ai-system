"""Unit tests for secret sanitization and runtime error capture."""

import os
from unittest.mock import patch
import pytest

from agents.debugging_models import ErrorReport, ErrorSeverity
from core.debugging.error_capture import capture_exception, sanitize_text


def test_sanitize_text_redacts_api_keys():
    raw = "Failed connection with api_key='AIzaSy1234567890abcdef1234567890abc'"
    cleaned = sanitize_text(raw)
    assert "AIzaSy1234567890abcdef1234567890abc" not in cleaned
    assert "[REDACTED_SECRET]" in cleaned


def test_sanitize_text_redacts_passwords_and_tokens():
    raw = "Authorization failed for user=admin password='SecretPassword123' token=bearer_abc123"
    cleaned = sanitize_text(raw)
    assert "SecretPassword123" not in cleaned
    assert "[REDACTED_SECRET]" in cleaned


def test_sanitize_text_redacts_env_var_values():
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "my-secret-google-api-key-999"}):
        raw = "Error calling Google API with key my-secret-google-api-key-999"
        cleaned = sanitize_text(raw)
        assert "my-secret-google-api-key-999" not in cleaned
        assert "[REDACTED_SECRET]" in cleaned


def test_capture_exception_creates_sanitized_report():
    try:
        raise ValueError("Invalid credentials api_key=super-secret-key-111")
    except Exception as exc:
        report = capture_exception(
            exc=exc,
            component="test_module",
            request_id="req-test-123",
            severity=ErrorSeverity.CRITICAL,
        )

    assert isinstance(report, ErrorReport)
    assert report.request_id == "req-test-123"
    assert report.component == "test_module"
    assert report.exception_type == "ValueError"
    assert "super-secret-key-111" not in report.message
    assert "super-secret-key-111" not in report.stack_trace
    assert "[REDACTED_SECRET]" in report.message
