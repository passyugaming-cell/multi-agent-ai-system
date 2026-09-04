"""Inter-agent message contracts and types."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import uuid

from pydantic import BaseModel, Field, field_validator


class MessageType(str, Enum):
    """Controlled message types for inter-agent communication."""

    REQUEST = "REQUEST"
    RESPONSE = "RESPONSE"
    HANDOFF = "HANDOFF"
    EVENT = "EVENT"
    ERROR = "ERROR"


class AgentMessage(BaseModel):
    """Typed inter-agent message contract."""

    message_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique message ID.",
    )
    conversation_id: Optional[str] = Field(
        default=None, description="Conversation session ID."
    )
    request_id: str = Field(
        ..., description="Traceable request ID linking messages across calls."
    )
    sender_agent: str = Field(..., description="ID of sender agent.")
    recipient_agent: str = Field(..., description="ID of recipient agent or '*' for broadcast.")
    message_type: MessageType = Field(..., description="Type of message.")
    payload: Dict[str, Any] = Field(
        default_factory=dict, description="Structured JSON-compatible data payload."
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC creation timestamp.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Safe transport metadata."
    )

    @field_validator("payload")
    @classmethod
    def validate_payload_safety(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure payload is JSON-serializable safe data."""
        # Check basic safety / non-callable types
        for k, val in v.items():
            if callable(val):
                raise ValueError(f"Message payload cannot contain executable code/callables for key '{k}'")
        return v
