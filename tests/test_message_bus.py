"""Unit tests for agents/messages.py and agents/message_bus.py."""

import asyncio
import pytest

from agents.messages import AgentMessage, MessageType
from agents.message_bus import InMemoryMessageBus
from core.exceptions import MessageDeliveryError, MessageValidationError


def test_agent_message_validation():
    msg = AgentMessage(
        request_id="req_123",
        sender_agent="agent_a",
        recipient_agent="agent_b",
        message_type=MessageType.REQUEST,
        payload={"query": "hello"},
    )
    assert msg.request_id == "req_123"
    assert msg.message_type == MessageType.REQUEST
    assert msg.payload["query"] == "hello"


def test_agent_message_rejects_callable_payload():
    with pytest.raises(ValueError) as exc_info:
        AgentMessage(
            request_id="req_123",
            sender_agent="agent_a",
            recipient_agent="agent_b",
            message_type=MessageType.REQUEST,
            payload={"func": lambda x: x},
        )
    assert "cannot contain executable code" in str(exc_info.value)


@pytest.mark.anyio
async def test_message_bus_publish_and_subscribe():
    bus = InMemoryMessageBus()
    received_messages = []

    async def sample_handler(msg: AgentMessage):
        received_messages.append(msg)
        return None

    bus.subscribe("agent_b", sample_handler)

    msg = AgentMessage(
        request_id="req_100",
        sender_agent="agent_a",
        recipient_agent="agent_b",
        message_type=MessageType.EVENT,
        payload={"event": "status_changed"},
    )

    await bus.publish(msg)
    assert len(received_messages) == 1
    assert received_messages[0].request_id == "req_100"


@pytest.mark.anyio
async def test_message_bus_request_reply():
    bus = InMemoryMessageBus()

    async def replying_handler(msg: AgentMessage):
        return AgentMessage(
            request_id=msg.request_id,
            sender_agent="agent_b",
            recipient_agent=msg.sender_agent,
            message_type=MessageType.RESPONSE,
            payload={"status": "ok"},
        )

    bus.subscribe("agent_b", replying_handler)

    request_msg = AgentMessage(
        request_id="req_200",
        sender_agent="agent_a",
        recipient_agent="agent_b",
        message_type=MessageType.REQUEST,
        payload={"ping": True},
    )

    reply = await bus.request_reply(request_msg, timeout=2.0)
    assert reply.message_type == MessageType.RESPONSE
    assert reply.payload["status"] == "ok"


@pytest.mark.anyio
async def test_message_bus_request_reply_timeout():
    bus = InMemoryMessageBus()

    # Subscriber does not reply
    async def no_reply_handler(msg: AgentMessage):
        return None

    bus.subscribe("agent_b", no_reply_handler)

    request_msg = AgentMessage(
        request_id="req_300",
        sender_agent="agent_a",
        recipient_agent="agent_b",
        message_type=MessageType.REQUEST,
        payload={"ping": True},
    )

    with pytest.raises(MessageDeliveryError) as exc_info:
        await bus.request_reply(request_msg, timeout=0.1)
    assert "Timeout waiting for reply" in str(exc_info.value)
