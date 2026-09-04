"""Unit tests for agents/engine.py."""

import pytest

from agents.base import BaseAgent
from agents.context import AgentContext
from agents.contracts import AgentResult
from agents.engine import AgentEngine
from agents.registry import AgentRegistry
from core.exceptions import AgentNotFoundError


class SuccessAgent(BaseAgent):
    async def execute(self, request, context):
        return AgentResult(
            success=True,
            agent_id=self.agent_id,
            request_id=context.request_id,
            output=f"Processed: {request}",
        )


class FailingAgent(BaseAgent):
    async def execute(self, request, context):
        raise RuntimeError("Something blew up inside agent execution")


@pytest.mark.anyio
async def test_engine_execute_success():
    registry = AgentRegistry()
    agent = SuccessAgent("s_agent", "Success Agent", "Desc", "Instruction")
    registry.register(agent)

    engine = AgentEngine(registry=registry)
    res = await engine.execute_agent("s_agent", "Hello")

    assert res.success is True
    assert res.agent_id == "s_agent"
    assert res.output == "Processed: Hello"
    assert "execution_duration_sec" in res.metadata


@pytest.mark.anyio
async def test_engine_execute_unknown_agent_raises():
    registry = AgentRegistry()
    engine = AgentEngine(registry=registry)

    with pytest.raises(AgentNotFoundError):
        await engine.execute_agent("non_existent", "test")


@pytest.mark.anyio
async def test_engine_handles_agent_exception_gracefully():
    registry = AgentRegistry()
    agent = FailingAgent("f_agent", "Failing Agent", "Desc", "Instruction")
    registry.register(agent)

    engine = AgentEngine(registry=registry)
    res = await engine.execute_agent("f_agent", "Crash")

    assert res.success is False
    assert res.agent_id == "f_agent"
    assert "Something blew up" in res.error


@pytest.mark.anyio
async def test_engine_recursion_depth_limit():
    registry = AgentRegistry()
    agent = SuccessAgent("s_agent", "Success Agent", "Desc", "Instruction")
    registry.register(agent)

    engine = AgentEngine(registry=registry, max_depth=3)
    deep_context = AgentContext(execution_depth=4)

    res = await engine.execute_agent("s_agent", "Test", context=deep_context)
    assert res.success is False
    assert "Maximum execution depth" in res.error
