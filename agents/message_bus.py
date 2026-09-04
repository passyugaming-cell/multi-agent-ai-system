"""Mock in-memory message bus for agent-to-agent communication."""

from abc import ABC, abstractmethod
import asyncio
import logging
from typing import Awaitable, Callable, Dict, List, Optional

from agents.messages import AgentMessage, MessageType
from core.exceptions import MessageDeliveryError, MessageValidationError

logger = logging.getLogger(__name__)

MessageHandler = Callable[[AgentMessage], Awaitable[Optional[AgentMessage]]]


class MessageBus(ABC):
    """Abstract Message Bus interface for inter-agent messaging."""

    @abstractmethod
    async def publish(self, message: AgentMessage) -> None:
        """Publish a message to subscriber agents."""
        pass

    @abstractmethod
    def subscribe(self, agent_id: str, handler: MessageHandler) -> None:
        """Subscribe an agent to incoming messages."""
        pass

    @abstractmethod
    async def request_reply(self, message: AgentMessage, timeout: float = 10.0) -> AgentMessage:
        """Send a request message and wait for direct response."""
        pass


class InMemoryMessageBus(MessageBus):
    """Development/testing in-memory message bus implementation."""

    def __init__(self) -> None:
        self._subscriptions: Dict[str, List[MessageHandler]] = {}
        self._pending_replies: Dict[str, asyncio.Future[AgentMessage]] = {}

    def subscribe(self, agent_id: str, handler: MessageHandler) -> None:
        """Subscribe handler for target agent ID."""
        if agent_id not in self._subscriptions:
            self._subscriptions[agent_id] = []
        self._subscriptions[agent_id].append(handler)
        logger.debug("Subscribed handler for agent_id: %s", agent_id)

    async def publish(self, message: AgentMessage) -> None:
        """Publish message to recipient subscribers or process pending request reply."""
        if not isinstance(message, AgentMessage):
            raise MessageValidationError("Published item must be an instance of AgentMessage.")

        logger.info(
            "Publishing message %s from '%s' to '%s' (Type: %s)",
            message.message_id,
            message.sender_agent,
            message.recipient_agent,
            message.message_type,
        )

        # Check if message is a response/error fulfilling a pending request_reply call
        if (
            message.request_id in self._pending_replies
            and message.message_type in (MessageType.RESPONSE, MessageType.ERROR)
            and not self._pending_replies[message.request_id].done()
        ):
            fut = self._pending_replies[message.request_id]
            fut.set_result(message)
            return

        recipients: List[str] = []
        if message.recipient_agent == "*":
            recipients = list(self._subscriptions.keys())
        elif message.recipient_agent in self._subscriptions:
            recipients = [message.recipient_agent]

        if not recipients:
            logger.warning("No subscribers found for recipient_agent: %s", message.recipient_agent)
            return

        for recipient in recipients:
            for handler in self._subscriptions.get(recipient, []):
                try:
                    reply = await handler(message)
                    if reply and isinstance(reply, AgentMessage):
                        await self.publish(reply)
                except Exception as e:
                    logger.error("Error executing message handler for agent %s: %s", recipient, str(e))
                    raise MessageDeliveryError(f"Handler error on message delivery: {e}") from e

    async def request_reply(self, message: AgentMessage, timeout: float = 10.0) -> AgentMessage:
        """Send request and await response with timeout."""
        if not isinstance(message, AgentMessage):
            raise MessageValidationError("Request message must be an instance of AgentMessage.")

        fut: asyncio.Future[AgentMessage] = asyncio.get_running_loop().create_future()
        self._pending_replies[message.request_id] = fut

        try:
            await self.publish(message)
            response = await asyncio.wait_for(fut, timeout=timeout)
            return response
        except asyncio.TimeoutError as e:
            raise MessageDeliveryError(
                f"Timeout waiting for reply to message_id {message.message_id} (request_id {message.request_id})"
            ) from e
        finally:
            self._pending_replies.pop(message.request_id, None)
