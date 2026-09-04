"""Runtime error capture and credential sanitization abstraction."""

import os
import re
import traceback
from typing import Any, Dict, Optional

from agents.debugging_models import ErrorReport, ErrorSeverity

# Regex patterns for matching common sensitive fields and secrets
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|password|token|auth|bearer|credential|passphrase)[\"']?\s*[:=]\s*[\"']?([^\"'\s,&]+)[\"']?"),
    re.compile(r"(?i)(AIzaSy[A-Za-z0-9_-]{33})"),  # Google API Key pattern
    re.compile(r"(?i)(bearer\s+[A-Za-z0-9\-\._~\+\/]+=*)"),
]


def sanitize_text(text: str) -> str:
    """Redact secrets, API keys, passwords, and sensitive tokens from text.

    Args:
        text: String content to sanitize.

    Returns:
        str: Redacted safe text.
    """
    if not text:
        return text

    sanitized = text

    # Check and redact pattern matches
    for pattern in SECRET_PATTERNS:
        if pattern.groups == 2:
            sanitized = pattern.sub(r"\1: [REDACTED_SECRET]", sanitized)
        else:
            sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)

    # Redact environment variable values if present in text
    for env_key in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", "SECRET_KEY"):
        val = os.getenv(env_key)
        if val and len(val) > 4:
            sanitized = sanitized.replace(val, "[REDACTED_SECRET]")

    return sanitized


def capture_exception(
    exc: Exception,
    component: str,
    request_id: str,
    service: str = "multi-agent-system",
    severity: ErrorSeverity = ErrorSeverity.HIGH,
    metadata: Optional[Dict[str, Any]] = None,
) -> ErrorReport:
    """Capture a Python runtime exception and convert it to a safe ErrorReport.

    The original exception is NOT modified or swallowed.

    Args:
        exc: Exception instance.
        component: Component or module name where error occurred.
        request_id: Traceable request correlation ID.
        service: Service name.
        severity: Error severity level.
        metadata: Optional context metadata.

    Returns:
        ErrorReport: Sanitized error report object.
    """
    raw_message = str(exc)
    raw_traceback = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    safe_message = sanitize_text(raw_message)
    safe_stack = sanitize_text(raw_traceback)

    safe_metadata = {}
    if metadata:
        for k, v in metadata.items():
            safe_metadata[k] = sanitize_text(str(v)) if isinstance(v, str) else v

    return ErrorReport(
        request_id=request_id,
        service=service,
        component=component,
        exception_type=type(exc).__name__,
        message=safe_message,
        stack_trace=safe_stack,
        severity=severity,
        metadata=safe_metadata,
    )
