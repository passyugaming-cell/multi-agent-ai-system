"""End-to-End Test for Owner -> Ads Flow."""

import pytest

from app_factory import build_application
from orchestrator import OrchestrationRequest


@pytest.mark.asyncio
async def test_e2e_owner_to_ads_flow():
    orchestrator = build_application(simulation_mode=True)

    req = OrchestrationRequest(
        instruction="Analyze our ad campaign performance and ROAS metrics.",
        conversation_id="conv-ads-01",
        tenant_id="tenant-123",
    )

    result = await orchestrator.handle_request(req)

    assert result.success is True
    assert result.request_id == req.request_id
    assert "owner" in result.agent_results or "owner-agent" in result.agent_results
    assert "ads-agent" in result.agent_results
    assert result.owner_decision["target_agent"] == "ads-agent"
    assert "Campaign performance analysis complete" in result.final_response
    assert len(result.execution_trace) > 0
