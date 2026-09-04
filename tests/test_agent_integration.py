"""Integration tests for multi-agent inter-communication flows."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from agents.ads_agent import AdsAgent, AdsAnalysis, AdsRequest, CampaignMetrics, PerformanceStatus
from agents.context import AgentContext
from agents.contracts import AgentResult
from agents.cs_agent import CSAgent, CSIntent, CSRequest, CSResponse
from agents.debugger_agent import DebuggerAgent
from agents.debugging_loop import SelfDebuggingLoop
from agents.debugging_models import DebugAnalysis, ErrorSeverity, PatchRecommendation
from agents.engine import AgentEngine
from agents.message_bus import InMemoryMessageBus
from agents.messages import AgentMessage, MessageType
from agents.owner_agent import OwnerAgent, OwnerDecision, OwnerDecisionPriority
from agents.registry import AgentRegistry
from agents.router import AgentRouter


@pytest.fixture
def mock_genai_client():
    client = MagicMock()
    client.default_model = "gemini-2.5-flash"
    return client


@pytest.mark.anyio
async def test_owner_to_cs_communication_flow(mock_genai_client):
    bus = InMemoryMessageBus()
    registry = AgentRegistry()
    engine = AgentEngine(registry=registry, message_bus=bus)

    # Setup CS Agent handler on MessageBus
    cs_agent = CSAgent(genai_client=mock_genai_client, message_bus=bus)
    registry.register(cs_agent)

    expected_cs_response = CSResponse(
        response="No active orders found for customer.",
        intent=CSIntent.ORDER_STATUS,
        confidence=0.9,
        requires_human=False,
        missing_information=[],
        recommended_next_step="Prompt customer for order ID.",
        source_agents=["cs-agent"],
    )
    mock_genai_client.generate_structured_async = AsyncMock(return_value=expected_cs_response)

    async def cs_bus_handler(message: AgentMessage) -> AgentMessage:
        cs_req = CSRequest.model_validate(message.payload)
        context = AgentContext(
            request_id=message.request_id,
            conversation_id=message.conversation_id,
            source_agent=message.sender_agent,
        )
        res = await cs_agent.execute(cs_req, context)
        return AgentMessage(
            request_id=message.request_id,
            conversation_id=message.conversation_id,
            sender_agent=cs_agent.agent_id,
            recipient_agent=message.sender_agent,
            message_type=MessageType.RESPONSE,
            payload=res.output,
        )

    bus.subscribe("cs-agent", cs_bus_handler)

    # Setup Owner Agent and test delegation
    owner = OwnerAgent(genai_client=mock_genai_client, message_bus=bus)
    registry.register(owner)

    context = AgentContext(request_id="req-owner-cs-1", conversation_id="conv-100")
    cs_payload = CSRequest(message="Check order status", customer_id="c-55").model_dump()

    reply_msg = await owner.delegate_to_agent("cs-agent", cs_payload, context)

    assert reply_msg.request_id == "req-owner-cs-1"
    assert reply_msg.conversation_id == "conv-100"
    assert reply_msg.sender_agent == "cs-agent"
    assert reply_msg.recipient_agent == "owner"
    assert reply_msg.payload["intent"] == "ORDER_STATUS"


@pytest.mark.anyio
async def test_owner_to_ads_communication_flow(mock_genai_client):
    bus = InMemoryMessageBus()
    registry = AgentRegistry()

    ads_agent = AdsAgent(genai_client=mock_genai_client, message_bus=bus)
    registry.register(ads_agent)

    expected_ads_analysis = AdsAnalysis(
        summary="Campaign performance looks optimal.",
        performance_status=PerformanceStatus.GOOD,
        key_findings=["Stable CPA"],
        anomalies=[],
        recommendations=["Maintain current spend"],
        missing_data=[],
        requires_human_approval=True,
        confidence=0.91,
    )
    mock_genai_client.generate_structured_async = AsyncMock(return_value=expected_ads_analysis)

    async def ads_bus_handler(message: AgentMessage) -> AgentMessage:
        ads_req = AdsRequest.model_validate(message.payload)
        context = AgentContext(
            request_id=message.request_id,
            conversation_id=message.conversation_id,
            source_agent=message.sender_agent,
        )
        res = await ads_agent.execute(ads_req, context)
        return AgentMessage(
            request_id=message.request_id,
            conversation_id=message.conversation_id,
            sender_agent=ads_agent.agent_id,
            recipient_agent=message.sender_agent,
            message_type=MessageType.RESPONSE,
            payload=res.output,
        )

    bus.subscribe("ads-agent", ads_bus_handler)

    owner = OwnerAgent(genai_client=mock_genai_client, message_bus=bus)
    registry.register(owner)

    context = AgentContext(request_id="req-owner-ads-1", conversation_id="conv-200")
    ads_payload = AdsRequest(campaign_id="cmp-88", objective="Optimize CPC").model_dump()

    reply_msg = await owner.delegate_to_agent("ads-agent", ads_payload, context)

    assert reply_msg.request_id == "req-owner-ads-1"
    assert reply_msg.sender_agent == "ads-agent"
    assert reply_msg.payload["performance_status"] == "GOOD"


@pytest.mark.anyio
async def test_agent_failure_to_debugger_flow(mock_genai_client):
    bus = InMemoryMessageBus()
    debugger = DebuggerAgent(genai_client=mock_genai_client, message_bus=bus)
    debugging_loop = SelfDebuggingLoop(debugger_agent=debugger, max_attempts=3)

    expected_debug_analysis = DebugAnalysis(
        classification="PAYLOAD_KEY_ERROR",
        severity=ErrorSeverity.HIGH,
        root_cause="KeyError when looking up customer_id in payload dictionary.",
        affected_components=["cs_agent"],
        evidence=["KeyError: 'customer_id'"],
        recommended_fix="Use payload.get('customer_id') instead of direct key lookup.",
        patch=PatchRecommendation(
            file_path="agents/cs_agent.py",
            description="Use safe get dict lookup",
            change_type="BUG_FIX",
            old_behavior="Direct key lookup",
            new_behavior="Safe dictionary get",
            rationale="Avoid KeyError on optional fields",
        ),
        tests_to_add=["test_cs_agent_missing_key"],
        confidence=0.97,
        requires_human_review=True,
    )
    mock_genai_client.generate_structured_async = AsyncMock(return_value=expected_debug_analysis)

    context = AgentContext(request_id="req-debug-flow-1")

    # Simulate CS agent execution raising KeyError
    try:
        data = {}
        _ = data["customer_id"]
    except KeyError as exc:
        result = await debugging_loop.analyze_exception(
            exc=exc,
            component="cs_agent",
            context=context,
        )

    assert result.success is True
    assert result.agent_id == "debugger-agent"
    assert result.output["classification"] == "PAYLOAD_KEY_ERROR"
    assert result.output["requires_human_review"] is True
