"""End-to-End Test for Successful Flow & Debugger Failure Handling."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app_factory import build_application
from agents import AgentRegistry, AgentEngine, InMemoryMessageBus, SelfDebuggingLoop
from agents.contracts import AgentResult
from orchestrator import ApplicationOrchestrator, ExecutionStatus, OrchestrationRequest


@pytest.mark.asyncio
async def test_e2e_successful_flows():
    orchestrator = build_application(simulation_mode=True)

    # 1. Customer Service flow
    res_cs = await orchestrator.handle_request("Help customer with refund request")
    assert res_cs.success is True
    assert res_cs.status == ExecutionStatus.COMPLETED
    assert "cs-agent" in res_cs.agent_results

    # 2. Ads flow
    res_ads = await orchestrator.handle_request("Analyze Google Ads ROAS performance")
    assert res_ads.success is True
    assert res_ads.status == ExecutionStatus.COMPLETED
    assert "ads-agent" in res_ads.agent_results

    # 3. Owner only decision
    res_owner = await orchestrator.handle_request("What is our company vision?")
    assert res_owner.success is True
    assert res_owner.status == ExecutionStatus.COMPLETED


@pytest.mark.asyncio
async def test_e2e_debugger_failure_graceful_handling():
    registry = AgentRegistry()
    message_bus = InMemoryMessageBus()
    engine = AgentEngine(registry=registry, message_bus=message_bus)

    # Owner Agent
    owner_agent = MagicMock()
    owner_agent.agent_id = "owner-agent"
    owner_agent.execute = AsyncMock(
        return_value=AgentResult(
            success=True,
            agent_id="owner-agent",
            request_id="req-dbl-fail",
            output={"decision": "Route to CS", "target_agent": "cs-agent"},
        )
    )
    registry.register(owner_agent)

    # CS Agent
    cs_agent = MagicMock()
    cs_agent.agent_id = "cs-agent"
    cs_agent.execute = AsyncMock(
        return_value=AgentResult(
            success=False,
            agent_id="cs-agent",
            request_id="req-dbl-fail",
            error="CS Agent crash.",
        )
    )
    registry.register(cs_agent)

    # Failing Debugger Loop
    debugging_loop = MagicMock(spec=SelfDebuggingLoop)
    debugging_loop.analyze_exception = AsyncMock(
        return_value=AgentResult(
            success=False,
            agent_id="debugger-agent",
            request_id="req-dbl-fail",
            error="Debugger Agent LLM quota exceeded.",
        )
    )

    orchestrator = ApplicationOrchestrator(
        engine=engine,
        registry=registry,
        message_bus=message_bus,
        debugging_loop=debugging_loop,
    )

    req = OrchestrationRequest(request_id="req-dbl-fail", instruction="Check order status")
    res = await orchestrator.handle_request(req)

    assert res.success is False
    assert res.status == ExecutionStatus.FAILED
    assert "CS Agent crash." in res.final_response
    assert any("Debugger error" in err for err in res.errors)
