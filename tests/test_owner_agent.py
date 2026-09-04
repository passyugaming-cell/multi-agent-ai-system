"""Unit tests for agents/owner_agent.py."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from agents.context import AgentContext
from agents.contracts import AgentResult
from agents.owner_agent import OwnerAgent, OwnerDecision, OwnerDecisionPriority
from core.ai.exceptions import GenAIModelError


@pytest.fixture
def mock_genai_client():
    client = MagicMock()
    client.default_model = "gemini-2.5-flash"
    return client


def test_owner_agent_initialization(mock_genai_client):
    owner = OwnerAgent(genai_client=mock_genai_client)
    assert owner.agent_id == "owner"
    assert owner.name == "Owner Agent"
    assert "You are the Owner Agent" in owner.system_instruction


@pytest.mark.anyio
async def test_owner_agent_execute_success(mock_genai_client):
    expected_decision = OwnerDecision(
        decision="Review high-priority customer complaints.",
        priority=OwnerDecisionPriority.HIGH,
        reasoning="Multiple support tickets escalated in the last 2 hours.",
        facts=["3 tickets escalated in 2 hours"],
        assumptions=["Staffing is normal"],
        recommendations=["Notify CS supervisor"],
        requested_actions=["cs_agent:fetch_ticket_details"],
        source_agents=["cs"],
        requires_human_approval=True,
    )
    mock_genai_client.generate_structured_async = AsyncMock(return_value=expected_decision)

    owner = OwnerAgent(genai_client=mock_genai_client)
    context = AgentContext(source_agent="cs", metadata={"env": "prod"})

    result = await owner.execute("What should we do about escalated tickets?", context)

    assert isinstance(result, AgentResult)
    assert result.success is True
    assert result.agent_id == "owner"
    assert result.output["decision"] == "Review high-priority customer complaints."
    assert result.output["priority"] == "HIGH"
    assert "cs" in result.output["source_agents"]


@pytest.mark.anyio
async def test_owner_agent_execute_failure_handled(mock_genai_client):
    mock_genai_client.generate_structured_async = AsyncMock(
        side_effect=GenAIModelError("Model failed to adhere to JSON schema")
    )

    owner = OwnerAgent(genai_client=mock_genai_client)
    context = AgentContext()

    result = await owner.execute("Analyze server load", context)

    assert isinstance(result, AgentResult)
    assert result.success is False
    assert result.agent_id == "owner"
    assert "OwnerAgent failed to generate decision" in result.error
