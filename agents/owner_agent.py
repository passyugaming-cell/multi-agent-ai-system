"""Owner Agent module implementation.

Primary decision-support, supervisory, and inter-agent coordinator agent.
"""

from enum import Enum
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from agents.base import BaseAgent
from agents.context import AgentContext
from agents.contracts import AgentResult
from agents.message_bus import MessageBus
from agents.prompts.owner_prompt import OWNER_SYSTEM_INSTRUCTION
from core.ai.genai_client import GenAIClient

logger = logging.getLogger(__name__)


class OwnerDecisionPriority(str, Enum):
    """Priority levels for Owner Agent decision outputs."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class OwnerDecision(BaseModel):
    """Structured decision output schema for Owner Agent."""

    decision: str = Field(
        ..., description="High-level decision statement or executive summary."
    )
    priority: OwnerDecisionPriority = Field(
        ..., description="Priority level of the decision/request."
    )
    reasoning: str = Field(
        ..., description="Step-by-step reasoning supporting the decision."
    )
    facts: List[str] = Field(
        default_factory=list,
        description="Grounded facts confirmed from verified prompt/context data.",
    )
    assumptions: List[str] = Field(
        default_factory=list,
        description="Explicit assumptions made due to missing or incomplete information.",
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Actionable recommendations for the human owner.",
    )
    requested_actions: List[str] = Field(
        default_factory=list,
        description="Tasks or sub-requests flagged for specialized agents or tools.",
    )
    source_agents: List[str] = Field(
        default_factory=list,
        description="List of agent IDs whose input informed this decision.",
    )
    requires_human_approval: bool = Field(
        default=True,
        description="Whether proposed actions require human authorization before execution.",
    )


class OwnerAgent(BaseAgent):
    """Owner Agent for executive decision-making and agent coordination."""

    def __init__(
        self,
        genai_client: GenAIClient,
        message_bus: Optional[MessageBus] = None,
        agent_id: str = "owner",
        name: str = "Owner Agent",
        description: str = "Executive supervisory decision support agent.",
        system_instruction: str = OWNER_SYSTEM_INSTRUCTION,
    ) -> None:
        """Initialize OwnerAgent.

        Args:
            genai_client: Centralized GenAIClient infrastructure dependency.
            message_bus: Optional MessageBus instance for inter-agent communication.
            agent_id: Agent identifier (default 'owner').
            name: Human-readable agent name.
            description: Agent description.
            system_instruction: System prompt instruction.
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
        """Execute decision support analysis for a user or system request.

        Args:
            request: String prompt, dictionary payload, or request object.
            context: AgentContext for tracking request state.

        Returns:
            AgentResult: Execution result containing OwnerDecision output.
        """
        prompt_text = str(request) if not isinstance(request, str) else request

        # Grounding text preparation
        formatted_prompt = (
            f"REQUEST / SYSTEM INPUT:\n{prompt_text}\n\n"
            f"CONTEXT METADATA:\n{context.metadata}\n"
        )

        try:
            # Invoke structured generation via central GenAIClient
            decision: OwnerDecision = await self.genai_client.generate_structured_async(
                prompt=formatted_prompt,
                response_schema=OwnerDecision,
                system_instruction=self.system_instruction,
            )

            # Preserve source agent in output if context originated from another agent
            if context.source_agent and context.source_agent not in decision.source_agents:
                decision.source_agents.append(context.source_agent)

            return AgentResult(
                success=True,
                agent_id=self.agent_id,
                request_id=context.request_id,
                output=decision.model_dump(),
                metadata={"model_used": self.genai_client.default_model},
            )
        except Exception as e:
            logger.error(
                "OwnerAgent execution failed for request_id %s: %s",
                context.request_id,
                str(e),
                exc_info=True,
            )
            return AgentResult(
                success=False,
                agent_id=self.agent_id,
                request_id=context.request_id,
                error=f"OwnerAgent failed to generate decision: {e}",
            )
