"""Unit tests for agents/registry.py."""

import pytest

from agents.base import BaseAgent
from agents.context import AgentContext
from agents.contracts import AgentResult
from agents.registry import AgentRegistry
from core.exceptions import AgentNotFoundError, DuplicateAgentError


class DummyAgent(BaseAgent):
    async def execute(self, request, context):
        return AgentResult(success=True, agent_id=self.agent_id, request_id=context.request_id)


def test_agent_registry_register_and_get():
    registry = AgentRegistry()
    agent = DummyAgent("dummy_1", "Dummy Agent", "Description", "Instruction")

    registry.register(agent)
    assert registry.exists("dummy_1")
    assert registry.get("dummy_1") is agent
    assert len(registry.list_agents()) == 1


def test_agent_registry_duplicate_registration_fails():
    registry = AgentRegistry()
    agent1 = DummyAgent("dummy_1", "Dummy Agent 1", "Desc 1", "Instruction 1")
    agent2 = DummyAgent("dummy_1", "Dummy Agent 2", "Desc 2", "Instruction 2")

    registry.register(agent1)
    with pytest.raises(DuplicateAgentError):
        registry.register(agent2)


def test_agent_registry_get_missing_fails():
    registry = AgentRegistry()
    with pytest.raises(AgentNotFoundError):
        registry.get("non_existent")


def test_agent_registry_clear():
    registry = AgentRegistry()
    registry.register(DummyAgent("a1", "Agent 1", "Desc", "Instr"))
    assert len(registry.list_agents()) == 1
    registry.clear()
    assert len(registry.list_agents()) == 0
