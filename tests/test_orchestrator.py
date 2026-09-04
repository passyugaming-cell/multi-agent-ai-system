"""Unit tests for ApplicationOrchestrator."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from agents import AgentEngine, AgentRegistry, InMemoryMessageBus, SelfDebuggingLoop
from orchestrator import (
    ApplicationOrchestrator,
    ExecutionStatus,
    OrchestrationRequest,
)


@pytest.fixture
def mock_deps():
    registry = AgentRegistry()
    message_bus = InMemoryMessageBus()
    engine = AgentEngine(registry=registry, message_bus=message_bus)
    debugging_loop = MagicMock(spec=SelfDebuggingLoop)
    return registry, message_bus, engine, debugging_loop


@pytest.mark.asyncio
async def test_orchestrator_valid_request_owner_only(mock_deps):
    registry, message_bus, engine, debugging_loop = mock_deps

    owner_agent = MagicMock()
    owner_agent.agent_id = "owner-agent"
    owner_agent.execute = AsyncMock()

    from agents.contracts import AgentResult
    owner_agent.execute.return_value = AgentResult(
        success=True,
        agent_id="owner-agent",
        request_id="req-1",
        output={
            "decision": "Decision made.",
            "target_agent": None,
            "priority": "LOW",
            "reasoning": "No routing needed.",
        },
    )
    registry.register(owner_agent)

    orchestrator = ApplicationOrchestrator(
        engine=engine,
        registry=registry,
        message_bus=message_bus,
        debugging_loop=debugging_loop,
    )

    req = OrchestrationRequest(request_id="req-1", instruction="General query")
    res = await orchestrator.handle_request(req)

    assert res.success is True
    assert res.request_id == "req-1"
    assert res.status == ExecutionStatus.COMPLETED
    assert res.final_response == "Decision made."
    assert len(res.execution_trace) >= 3


@pytest.mark.asyncio
async def test_orchestrator_cs_routing(mock_deps):
    registry, message_bus, engine, debugging_loop = mock_deps

    owner_agent = MagicMock()
    owner_agent.agent_id = "owner-agent"
    owner_agent.execute = AsyncMock()

    cs_agent = MagicMock()
    cs_agent.agent_id = "cs-agent"
    cs_agent.execute = AsyncMock()

    from agents.contracts import AgentResult
    owner_agent.execute.return_value = AgentResult(
        success=True,
        agent_id="owner-agent",
        request_id="req-cs",
        output={"decision": "Route to CS", "target_agent": "cs-agent", "priority": "MEDIUM", "reasoning": "CS query"},
    )
    cs_agent.execute.return_value = AgentResult(
        success=True,
        agent_id="cs-agent",
        request_id="req-cs",
        output={"response": "CS response text", "recommended_next_step": "Follow up"},
    )

    registry.register(owner_agent)
    registry.register(cs_agent)

    orchestrator = ApplicationOrchestrator(
        engine=engine,
        registry=registry,
        message_bus=message_bus,
        debugging_loop=debugging_loop,
    )

    res = await orchestrator.handle_request("Support request")

    assert res.success is True
    assert "CS response text" in res.final_response
    assert "cs-agent" in res.agent_results


@pytest.mark.asyncio
async def test_orchestrator_unknown_target_rejection(mock_deps):
    registry, message_bus, engine, debugging_loop = mock_deps

    owner_agent = MagicMock()
    owner_agent.agent_id = "owner-agent"
    owner_agent.execute = AsyncMock()

    from agents.contracts import AgentResult
    owner_agent.execute.return_value = AgentResult(
        success=True,
        agent_id="owner-agent",
        request_id="req-unallowed",
        output={"decision": "Route to malicious agent", "target_agent": "unauthorized-malicious-agent", "priority": "HIGH", "reasoning": "Evil"},
    )
    registry.register(owner_agent)

    orchestrator = ApplicationOrchestrator(
        engine=engine,
        registry=registry,
        message_bus=message_bus,
        debugging_loop=debugging_loop,
    )

    res = await orchestrator.handle_request("Do evil")

    assert res.success is False
    assert res.status == ExecutionStatus.FAILED
    assert "security allowlist" in res.final_response
