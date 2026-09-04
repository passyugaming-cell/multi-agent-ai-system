"""End-to-End Test for Error -> Debugger Flow."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from agents import AgentRegistry, AgentEngine, InMemoryMessageBus, SelfDebuggingLoop
from agents.contracts import AgentResult
from orchestrator import ApplicationOrchestrator, ExecutionStatus, OrchestrationRequest


@pytest.mark.asyncio
async def test_e2e_error_to_debugger_flow():
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
            request_id="req-fail",
            output={"decision": "Route to CS", "target_agent": "cs-agent"},
        )
    )
    registry.register(owner_agent)

    # Failing CS Agent
    cs_agent = MagicMock()
    cs_agent.agent_id = "cs-agent"
    cs_agent.execute = AsyncMock(
        return_value=AgentResult(
            success=False,
            agent_id="cs-agent",
            request_id="req-fail",
            error="Database connection timeout in CS Agent.",
        )
    )
    registry.register(cs_agent)

    # Self-Debugging Loop
    debugging_loop = MagicMock(spec=SelfDebuggingLoop)
    debugging_loop.analyze_exception = AsyncMock(
        return_value=AgentResult(
            success=True,
            agent_id="debugger-agent",
            request_id="req-fail",
            output={
                "root_cause_analysis": "Database connection string invalid or timed out.",
                "error_classification": "INFRASTRUCTURE_ERROR",
                "patch_recommendation": "Update database pool timeout setting.",
                "affected_components": ["cs-agent"],
            },
        )
    )

    orchestrator = ApplicationOrchestrator(
        engine=engine,
        registry=registry,
        message_bus=message_bus,
        debugging_loop=debugging_loop,
    )

    req = OrchestrationRequest(request_id="req-fail", instruction="Check order status")
    res = await orchestrator.handle_request(req)

    assert res.success is False
    assert res.status == ExecutionStatus.REQUIRES_HUMAN_REVIEW
    assert "Database connection timeout" in res.final_response
    assert res.debug_result is not None
    assert "Database connection string invalid" in res.debug_result["root_cause_analysis"]
    assert "Update database pool timeout setting." in res.debug_result["patch_recommendation"]
