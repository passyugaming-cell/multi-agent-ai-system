"""Thread-safe and async-safe tenant context manager using contextvars."""

import contextlib
from contextvars import ContextVar
from typing import Generator, Optional

DEFAULT_TENANT_ID = "default_tenant"

_CURRENT_TENANT_ID: ContextVar[str] = ContextVar("current_tenant_id", default=DEFAULT_TENANT_ID)


class TenantContext:
    """Manager for setting, getting, and scoping current active tenant ID."""

    @staticmethod
    def get_tenant_id() -> str:
        """Get the current active tenant ID."""
        return _CURRENT_TENANT_ID.get()

    @staticmethod
    def set_tenant_id(tenant_id: str) -> None:
        """Set the active tenant ID for current context.

        Args:
            tenant_id: Unique string identifier for the tenant.
        """
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id must be a non-empty string.")
        _CURRENT_TENANT_ID.set(tenant_id.strip())

    @staticmethod
    def reset_tenant_id() -> None:
        """Reset active tenant ID back to default."""
        _CURRENT_TENANT_ID.set(DEFAULT_TENANT_ID)

    @staticmethod
    @contextlib.contextmanager
    def scope(tenant_id: str) -> Generator[str, None, None]:
        """Context manager to scope execution under a specific tenant ID.

        Usage:
            with TenantContext.scope("tenant_abc"):
                # operations run under tenant_abc
        """
        token = _CURRENT_TENANT_ID.set(tenant_id.strip())
        try:
            yield tenant_id
        finally:
            _CURRENT_TENANT_ID.reset(token)
