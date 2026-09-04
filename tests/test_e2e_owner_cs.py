"""End-to-End Test for Owner -> CS Flow."""

import pytest

from app_factory import build_application
from orchestrator import OrchestrationRequest


@pytest.mark.asyncio
async def test_e2e_owner_to_cs_flow():
    orchestrator = build_application(simulation_mode=True)

    req = OrchestrationRequest(
        instruction="Analyze our customer service response times and refunds policy.",
        conversation_id="conv-cs-01",
        tenant_id="tenant-123",
    )

    result = await orchestrator.handle_request(req)

    assert result.success is True
    assert result.request_id == req.request_id
    assert "owner" in result.agent_results or "owner-agent" in result.agent_results
    assert "cs-agent" in result.agent_results
    assert result.owner_decision["target_agent"] == "cs-agent"
    assert "Customer Support" in result.final_response
    assert len(result.execution_trace) > 0
