"""Tenant management, registration, and context isolation enforcement."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

try:
    from app.tenants.context import DEFAULT_TENANT_ID, TenantContext
except ImportError:
    from tenants.context import DEFAULT_TENANT_ID, TenantContext


class TenantSettings(BaseModel):
    """Configuration settings specific to a tenant."""

    custom_instructions: Optional[str] = Field(default=None, description="Custom system prompt instructions.")
    rate_limit_rpm: int = Field(default=60, description="Requests per minute allowed.")
    allowed_agents: List[str] = Field(
        default_factory=lambda: ["owner", "cs", "ads", "debugger"],
        description="List of allowed agent IDs for this tenant.",
    )


class Tenant(BaseModel):
    """Tenant organization model."""

    tenant_id: str = Field(..., description="Unique tenant identifier.")
    name: str = Field(..., description="Human-readable organization name.")
    is_active: bool = Field(default=True, description="Whether tenant account is active.")
    settings: TenantSettings = Field(default_factory=TenantSettings, description="Tenant config settings.")


class TenantManager:
    """Registry and isolation policy manager for multi-tenant deployment."""

    def __init__(self) -> None:
        """Initialize TenantManager with default system tenant."""
        self._tenants: Dict[str, Tenant] = {}
        # Register default tenant
        self.register_tenant(
            Tenant(
                tenant_id=DEFAULT_TENANT_ID,
                name="Default System Tenant",
                is_active=True,
            )
        )

    def register_tenant(self, tenant: Tenant) -> None:
        """Register or update a tenant organization.

        Args:
            tenant: Tenant model instance.
        """
        self._tenants[tenant.tenant_id] = tenant

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID."""
        return self._tenants.get(tenant_id)

    def is_tenant_active(self, tenant_id: str) -> bool:
        """Check if tenant exists and is active."""
        tenant = self._tenants.get(tenant_id)
        return tenant is not None and tenant.is_active

    def is_agent_allowed(self, tenant_id: str, agent_id: str) -> bool:
        """Check if tenant is authorized to invoke a specific agent."""
        tenant = self._tenants.get(tenant_id)
        if not tenant or not tenant.is_active:
            return False
        clean_agent_id = agent_id.replace("-agent", "").lower()
        return any(clean_agent_id in allowed.lower() for allowed in tenant.settings.allowed_agents)
