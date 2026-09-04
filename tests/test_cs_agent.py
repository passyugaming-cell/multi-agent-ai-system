"""Unit tests for agents/cs_agent.py."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from agents.context import AgentContext
from agents.contracts import AgentResult
from agents.cs_agent import CSAgent, CSIntent, CSRequest, CSResponse
from core.ai.exceptions import GenAIModelError


@pytest.fixture
def mock_genai_client():
    client = MagicMock()
    client.default_model = "gemini-2.5-flash"
    return client


def test_cs_agent_initialization(mock_genai_client):
    agent = CSAgent(genai_client=mock_genai_client)
    assert agent.agent_id == "cs-agent"
    assert agent.name == "CS Agent"
    assert "Customer Service" in agent.system_instruction


def test_cs_request_contract_valid():
    req = CSRequest(
        message="Where is my package?",
        customer_id="cust-123",
        available_facts={"order_id": "ord-456"},
    )
    assert req.message == "Where is my package?"
    assert req.customer_id == "cust-123"
    assert req.available_facts["order_id"] == "ord-456"


@pytest.mark.anyio
async def test_cs_agent_execute_success(mock_genai_client):
    expected_response = CSResponse(
        response="Order status is currently unavailable in system facts.",
        intent=CSIntent.ORDER_STATUS,
        confidence=0.95,
        requires_human=True,
        missing_information=["tracking_number", "order_status"],
        recommended_next_step="Request order ID or tracking number from customer.",
        source_agents=["cs-agent"],
    )
    mock_genai_client.generate_structured_async = AsyncMock(return_value=expected_response)

    cs_agent = CSAgent(genai_client=mock_genai_client)
    context = AgentContext(source_agent="owner")

    request = CSRequest(
        message="What is the status of my order?",
        customer_id="cust-789",
    )

    result = await cs_agent.execute(request, context)

    assert isinstance(result, AgentResult)
    assert result.success is True
    assert result.agent_id == "cs-agent"
    assert result.output["intent"] == "ORDER_STATUS"
    assert result.output["requires_human"] is True
    assert "tracking_number" in result.output["missing_information"]
    assert "owner" in result.output["source_agents"]


@pytest.mark.anyio
async def test_cs_agent_execute_string_request(mock_genai_client):
    expected_response = CSResponse(
        response="Hello! How can I assist you today?",
        intent=CSIntent.GENERAL_INQUIRY,
        confidence=0.98,
        requires_human=False,
        missing_information=[],
        recommended_next_step="Await customer response.",
        source_agents=["cs-agent"],
    )
    mock_genai_client.generate_structured_async = AsyncMock(return_value=expected_response)

    cs_agent = CSAgent(genai_client=mock_genai_client)
    context = AgentContext()

    result = await cs_agent.execute("Hello CS team", context)

    assert result.success is True
    assert result.output["intent"] == "GENERAL_INQUIRY"


@pytest.mark.anyio
async def test_cs_agent_validation_failure(mock_genai_client):
    mock_genai_client.generate_structured_async = AsyncMock(
        side_effect=GenAIModelError("Model output invalid JSON structure")
    )

    cs_agent = CSAgent(genai_client=mock_genai_client)
    context = AgentContext()

    result = await cs_agent.execute("Where is my order?", context)

    assert result.success is False
    assert "CSAgent execution failed" in result.error
