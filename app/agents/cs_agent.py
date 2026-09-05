"""Customer Service (CS) Agent implementation and contracts."""

from enum import Enum
import logging
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

try:
    from app.agents.base import BaseAgent
    from app.agents.context import AgentContext
    from app.agents.contracts import AgentResult
    from app.agents.message_bus import MessageBus
    from app.agents.prompts.cs_prompt import CS_SYSTEM_INSTRUCTION
    from app.core.ai.genai_client import GenAIClient
except ImportError:
    from agents.base import BaseAgent
    from agents.context import AgentContext
    from agents.contracts import AgentResult
    from agents.message_bus import MessageBus
    from agents.prompts.cs_prompt import CS_SYSTEM_INSTRUCTION
    from core.ai.genai_client import GenAIClient

logger = logging.getLogger(__name__)


class CSIntent(str, Enum):
    """Controlled classification intent for customer requests."""

    GENERAL_INQUIRY = "GENERAL_INQUIRY"
    ORDER_STATUS = "ORDER_STATUS"
    PRODUCT_INFO = "PRODUCT_INFO"
    BILLING_PAYMENT = "BILLING_PAYMENT"
    RETURNS_REFUNDS = "RETURNS_REFUNDS"
    COMPLAINT = "COMPLAINT"
    UNKNOWN = "UNKNOWN"


class CSRequest(BaseModel):
    """Pydantic input contract for CS Agent requests."""

    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique request ID for correlation.",
    )
    conversation_id: Optional[str] = Field(
        default=None, description="Optional conversation session ID."
    )
    customer_id: Optional[str] = Field(
        default=None, description="Optional customer ID."
    )
    tenant_id: Optional[str] = Field(
        default=None, description="Optional tenant or organization ID."
    )
    message: str = Field(
        ..., description="Customer input query or message text."
    )
    conversation_context: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Historical messages in current conversation context.",
    )
    available_facts: Dict[str, Any] = Field(
        default_factory=dict,
        description="Grounded, verified business facts provided for this query.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context metadata."
    )


class CSResponse(BaseModel):
    """Pydantic output contract for CS Agent response."""

    response: str = Field(
        ..., description="Customer-facing or internal CS response text."
    )
    intent: CSIntent = Field(
        ..., description="Classified intent of the customer message."
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0."
    )
    requires_human: bool = Field(
        default=False,
        description="True if human intervention or escalation is required.",
    )
    missing_information: List[str] = Field(
        default_factory=list,
        description="List of specific missing business facts required to fulfill request.",
    )
    recommended_next_step: str = Field(
        ..., description="Actionable recommended next step."
    )
    source_agents: List[str] = Field(
        default_factory=list,
        description="Agents involved in producing this response.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Safe execution metadata."
    )


class CSAgent(BaseAgent):
    """Customer Service Agent responsible for grounded customer interactions."""

    def __init__(
        self,
        genai_client: GenAIClient,
        message_bus: Optional[MessageBus] = None,
        agent_id: str = "cs-agent",
        name: str = "CS Agent",
        description: str = "Customer service reasoning and customer inquiry resolution agent.",
        system_instruction: str = CS_SYSTEM_INSTRUCTION,
    ) -> None:
        """Initialize CSAgent with GenAIClient dependency injection.

        Args:
            genai_client: Centralized GenAIClient instance.
            message_bus: Optional MessageBus instance.
            agent_id: Agent identifier (default 'cs-agent').
            name: Agent name.
            description: Agent description.
            system_instruction: System prompt for CS behavior.
        """
        super().__init__(
            agent_id=agent_id,
            name=name,
            description=description,
            system_instruction=system_instruction,
        )
        self.genai_client = genai_client
        self.message_bus = message_bus

    async def execute(
        self,
        request: Any,
        context: AgentContext,
    ) -> AgentResult:
        """Execute CS reasoning workflow asynchronously."""
        if isinstance(request, CSRequest):
            cs_req = request
        elif isinstance(request, dict):
            cs_req = CSRequest.model_validate(request)
        elif isinstance(request, str):
            cs_req = CSRequest(message=request, request_id=context.request_id)
        else:
            return AgentResult(
                status="FAILED",
                finding=f"Invalid request type '{type(request).__name__}' provided to CSAgent.",
                confidence=0.0,
                success=False,
                agent_id=self.agent_id,
                request_id=context.request_id,
                error=f"Invalid request type '{type(request).__name__}' provided to CSAgent.",
            )

        formatted_prompt = (
            f"CUSTOMER MESSAGE:\n{cs_req.message}\n\n"
            f"CUSTOMER ID: {cs_req.customer_id}\n"
            f"AVAILABLE GROUNDED FACTS:\n{cs_req.available_facts}\n\n"
            f"CONVERSATION HISTORY:\n{cs_req.conversation_context}\n\n"
            f"CONTEXT METADATA:\n{context.metadata}\n"
        )

        try:
            cs_response: CSResponse = await self.genai_client.generate_structured_async(
                prompt=formatted_prompt,
                response_schema=CSResponse,
                system_instruction=self.system_instruction,
            )

            if self.agent_id not in cs_response.source_agents:
                cs_response.source_agents.append(self.agent_id)
            if context.source_agent and context.source_agent not in cs_response.source_agents:
                cs_response.source_agents.append(context.source_agent)

            return AgentResult(
                status="FAILED" if cs_response.requires_human else "COMPLETED",
                finding=cs_response.response,
                evidence=cs_response.missing_information,
                confidence=cs_response.confidence,
                recommendation=cs_response.recommended_next_step,
                next_action=cs_response.recommended_next_step,
                success=True,
                agent_id=self.agent_id,
                request_id=context.request_id,
                output=cs_response.model_dump(),
                metadata={"model_used": self.genai_client.default_model},
            )
        except Exception as e:
            logger.error(
                "CSAgent execution failed for request_id %s: %s",
                context.request_id,
                str(e),
                exc_info=True,
            )
            return AgentResult(
                status="FAILED",
                finding=f"CSAgent execution failed: {e}",
                confidence=0.0,
                success=False,
                agent_id=self.agent_id,
                request_id=context.request_id,
                error=f"CSAgent execution failed: {e}",
            )
