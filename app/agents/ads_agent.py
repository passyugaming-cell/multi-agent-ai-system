"""Ads Agent implementation and campaign contracts."""

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
    from app.agents.prompts.ads_prompt import ADS_SYSTEM_INSTRUCTION
    from app.core.ai.genai_client import GenAIClient
except ImportError:
    from agents.base import BaseAgent
    from agents.context import AgentContext
    from agents.contracts import AgentResult
    from agents.message_bus import MessageBus
    from agents.prompts.ads_prompt import ADS_SYSTEM_INSTRUCTION
    from core.ai.genai_client import GenAIClient

logger = logging.getLogger(__name__)


class PerformanceStatus(str, Enum):
    """Status indicator for campaign performance."""

    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    AVERAGE = "AVERAGE"
    UNDERPERFORMING = "UNDERPERFORMING"
    CRITICAL = "CRITICAL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class CampaignMetrics(BaseModel):
    """Explicitly typed quantitative metrics for an ad campaign."""

    impressions: Optional[int] = Field(default=None, ge=0, description="Total ad impressions.")
    clicks: Optional[int] = Field(default=None, ge=0, description="Total ad clicks.")
    conversions: Optional[int] = Field(default=None, ge=0, description="Total ad conversions.")
    spend: Optional[float] = Field(default=None, ge=0.0, description="Total spend in USD.")
    revenue: Optional[float] = Field(default=None, ge=0.0, description="Total revenue generated in USD.")
    ctr: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="Click-through rate %.")
    cpc: Optional[float] = Field(default=None, ge=0.0, description="Cost per click in USD.")
    cpa: Optional[float] = Field(default=None, ge=0.0, description="Cost per acquisition/conversion in USD.")
    roas: Optional[float] = Field(default=None, ge=0.0, description="Return on ad spend factor.")


class AdsRequest(BaseModel):
    """Pydantic input contract for Ads Agent analytics requests."""

    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique request ID for correlation.",
    )
    tenant_id: Optional[str] = Field(
        default=None, description="Optional tenant/organization ID."
    )
    campaign_id: Optional[str] = Field(
        default=None, description="Optional target campaign identifier."
    )
    campaigns: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of raw or structured campaign data dictionaries.",
    )
    metrics: Optional[CampaignMetrics] = Field(
        default=None, description="Quantitative campaign performance metrics."
    )
    time_range: Optional[str] = Field(
        default=None, description="Time window for analysis (e.g. 'last_7_days')."
    )
    objective: str = Field(
        default="Maximize ROAS", description="Primary campaign optimization goal."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context metadata."
    )


class AdsAnalysis(BaseModel):
    """Pydantic output contract for Ads Agent analytics output."""

    summary: str = Field(
        ..., description="Executive summary of campaign performance analysis."
    )
    performance_status: PerformanceStatus = Field(
        ..., description="Overall campaign performance status assessment."
    )
    key_findings: List[str] = Field(
        default_factory=list, description="Key insights and findings from metrics."
    )
    anomalies: List[str] = Field(
        default_factory=list, description="Detected performance anomalies or spikes."
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Optimization strategy recommendations."
    )
    missing_data: List[str] = Field(
        default_factory=list, description="Missing metrics or information needed."
    )
    requires_human_approval: bool = Field(
        default=True,
        description="Indicates whether external campaign modifications require approval.",
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Safe execution metadata."
    )


class AdsAgent(BaseAgent):
    """Ads Agent responsible for campaign analytics and optimization decision support."""

    def __init__(
        self,
        genai_client: GenAIClient,
        message_bus: Optional[MessageBus] = None,
        agent_id: str = "ads-agent",
        name: str = "Ads Agent",
        description: str = "Advertising analytics and campaign optimization strategy agent.",
        system_instruction: str = ADS_SYSTEM_INSTRUCTION,
    ) -> None:
        """Initialize AdsAgent with GenAIClient dependency injection.

        Args:
            genai_client: Centralized GenAIClient instance.
            message_bus: Optional MessageBus instance.
            agent_id: Agent identifier (default 'ads-agent').
            name: Agent name.
            description: Agent description.
            system_instruction: System prompt for Ads behavior.
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
        """Execute campaign metrics analysis asynchronously."""
        if isinstance(request, AdsRequest):
            ads_req = request
        elif isinstance(request, dict):
            ads_req = AdsRequest.model_validate(request)
        elif isinstance(request, str):
            ads_req = AdsRequest(objective=request, request_id=context.request_id)
        else:
            return AgentResult(
                status="FAILED",
                finding=f"Invalid request type '{type(request).__name__}' provided to AdsAgent.",
                confidence=0.0,
                success=False,
                agent_id=self.agent_id,
                request_id=context.request_id,
                error=f"Invalid request type '{type(request).__name__}' provided to AdsAgent.",
            )

        formatted_prompt = (
            f"CAMPAIGN ID: {ads_req.campaign_id}\n"
            f"TIME RANGE: {ads_req.time_range}\n"
            f"OBJECTIVE: {ads_req.objective}\n"
            f"METRICS:\n{ads_req.metrics.model_dump() if ads_req.metrics else 'None'}\n\n"
            f"CAMPAIGNS DATA:\n{ads_req.campaigns}\n\n"
            f"CONTEXT METADATA:\n{context.metadata}\n"
        )

        try:
            analysis: AdsAnalysis = await self.genai_client.generate_structured_async(
                prompt=formatted_prompt,
                response_schema=AdsAnalysis,
                system_instruction=self.system_instruction,
            )

            rec = analysis.recommendations[0] if analysis.recommendations else None

            return AgentResult(
                status="WAITING_APPROVAL" if analysis.requires_human_approval else "COMPLETED",
                finding=analysis.summary,
                evidence=analysis.key_findings,
                confidence=analysis.confidence,
                recommendation=rec,
                next_action=rec,
                success=True,
                agent_id=self.agent_id,
                request_id=context.request_id,
                output=analysis.model_dump(),
                metadata={"model_used": self.genai_client.default_model},
            )
        except Exception as e:
            logger.error(
                "AdsAgent execution failed for request_id %s: %s",
                context.request_id,
                str(e),
                exc_info=True,
            )
            return AgentResult(
                status="FAILED",
                finding=f"AdsAgent execution failed: {e}",
                confidence=0.0,
                success=False,
                agent_id=self.agent_id,
                request_id=context.request_id,
                error=f"AdsAgent execution failed: {e}",
            )
