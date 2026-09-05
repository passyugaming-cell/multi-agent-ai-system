"""Unit tests for multi-tenant context isolation."""

import pytest
from app.tenants.context import DEFAULT_TENANT_ID, TenantContext
from app.tenants.manager import Tenant, TenantManager, TenantSettings
from app.agents.context import AgentContext
from app.orchestrator import OrchestrationRequest


def test_tenant_context_get_set_scope():
    """Test setting, getting, and scoping tenant_id via TenantContext."""
    assert TenantContext.get_tenant_id() == DEFAULT_TENANT_ID

    TenantContext.set_tenant_id("tenant_a")
    assert TenantContext.get_tenant_id() == "tenant_a"

    with TenantContext.scope("tenant_b"):
        assert TenantContext.get_tenant_id() == "tenant_b"

    assert TenantContext.get_tenant_id() == "tenant_a"
    TenantContext.reset_tenant_id()
    assert TenantContext.get_tenant_id() == DEFAULT_TENANT_ID


def test_tenant_context_invalid():
    """Test that empty tenant_id raises ValueError."""
    with pytest.raises(ValueError):
        TenantContext.set_tenant_id("")


def test_tenant_manager():
    """Test tenant registration, activity check, and agent permission checks."""
    manager = TenantManager()
    assert manager.is_tenant_active(DEFAULT_TENANT_ID)

    new_tenant = Tenant(
        tenant_id="acme_corp",
        name="Acme Corporation",
        is_active=True,
        settings=TenantSettings(allowed_agents=["cs", "owner"]),
    )
    manager.register_tenant(new_tenant)

    assert manager.is_tenant_active("acme_corp")
    assert manager.is_agent_allowed("acme_corp", "cs-agent")
    assert manager.is_agent_allowed("acme_corp", "owner")
    assert not manager.is_agent_allowed("acme_corp", "ads-agent")


def test_tenant_id_propagation_in_agent_context_and_request():
    """Test that tenant_id propagates to AgentContext and OrchestrationRequest automatically."""
    with TenantContext.scope("org_123"):
        ctx = AgentContext()
        assert ctx.tenant_id == "org_123"

        req = OrchestrationRequest(instruction="Hello world")
        assert req.tenant_id == "org_123"
