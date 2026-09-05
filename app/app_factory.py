"""Application factory for dependency wiring and initialization."""

import logging
import re
from typing import Any, Dict, Optional

from config import Settings, get_settings
from core.ai.genai_client import GenAIClient
from agents import (
    AdsAgent,
    AgentEngine,
    AgentRegistry,
    CSAgent,
    DebuggerAgent,
    InMemoryMessageBus,
    OwnerAgent,
    SelfDebuggingLoop,
)
from orchestrator import ApplicationOrchestrator

logger = logging.getLogger(__name__)


class MockGenAIClient(GenAIClient):
    """Deterministic simulation GenAIClient for offline testing and demonstration."""

    def __init__(self, responses: Optional[Dict[str, Any]] = None) -> None:
        """Initialize MockGenAIClient.

        Args:
            responses: Predefined responses dictionary keyed by keyword or schema.
        """
        # Bypass API key requirements for simulation mode
        self._default_model = "mock-gemini-2.5-flash"
        self._client = None
        self.responses = responses or {}

    async def generate_structured_async(
        self,
        prompt: str,
        response_schema: Any,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Any:
        """Return deterministic mocked schema instance based on target schema type."""
        schema_name = getattr(response_schema, "__name__", str(response_schema))

        if "OwnerDecision" in schema_name:
            prompt_lower = prompt.lower()
            if "customer" in prompt_lower or "order" in prompt_lower or re.search(r"\bcs\b", prompt_lower):
                target = "cs-agent"
            elif "ad" in prompt_lower or "campaign" in prompt_lower or "roas" in prompt_lower or re.search(r"\bads\b", prompt_lower):
                target = "ads-agent"
            else:
                target = None

            return response_schema(
                decision=f"Executive decision for request: {prompt[:40]}...",
                priority="MEDIUM",
                reasoning="Simulated analysis of user instruction.",
                target_agent=target,
                facts=["Fact 1: User prompt submitted."],
                assumptions=["Assumption 1: Simulation mode active."],
                recommendations=["Proceed with specialist analysis."],
                requested_actions=["Delegate to target agent if present."],
            )

        elif "CSResponse" in schema_name:
            return response_schema(
                response="Thank you for contacting Customer Support. We have processed your inquiry.",
                intent="GENERAL_INQUIRY",
                confidence=0.95,
                requires_human=False,
                missing_information=[],
                recommended_next_step="Send resolution summary to customer.",
            )

        elif "AdsAnalysis" in schema_name:
            return response_schema(
                summary="Campaign performance analysis complete. CTR is healthy and ROAS is optimal.",
                performance_status="GOOD",
                key_findings=["Click-through rate increased by 12%.", "ROAS target met."],
                anomalies=[],
                recommendations=["Reallocate 10% budget to top performing ad set."],
                missing_data=[],
                requires_human_approval=True,
                confidence=0.92,
            )

        elif "DebugAnalysis" in schema_name:
            return response_schema(
                root_cause_analysis="Simulated agent failure due to unexpected input schema or transient error.",
                error_classification="AGENT_LOGIC_ERROR",
                patch_recommendation="Validate request payload before execution.",
                affected_components=["failing_agent"],
                risk_assessment="LOW",
                confidence=0.88,
            )

        # Default fallback if schema is generic or unknown
        return response_schema()


def build_application(
    settings: Optional[Settings] = None,
    simulation_mode: bool = False,
    mock_genai_client: Optional[GenAIClient] = None,
) -> ApplicationOrchestrator:
    """Build and wire application components and return ApplicationOrchestrator.

    Args:
        settings: Application Settings (loaded via get_settings() if None).
        simulation_mode: Force offline deterministic simulation mode.
        mock_genai_client: Custom mock GenAI client instance if supplied.

    Returns:
        ApplicationOrchestrator: Fully wired orchestrator ready for requests.
    """
    if settings is None:
        try:
            settings = get_settings()
        except Exception:
            settings = None

    # Determine GenAIClient implementation
    genai_client: GenAIClient
    if mock_genai_client is not None:
        genai_client = mock_genai_client
    elif simulation_mode or not settings or not (settings.google_api_key or settings.gemini_api_key):
        logger.info("Initializing application in deterministic SIMULATION mode.")
        genai_client = MockGenAIClient()
    else:
        logger.info("Initializing application in PRODUCTION mode with GenAIClient.")
        genai_client = GenAIClient(settings=settings)

    # Core Infrastructure
    message_bus = InMemoryMessageBus()
    registry = AgentRegistry()
    engine = AgentEngine(registry=registry, message_bus=message_bus)

    # Instantiate Agents
    owner_agent = OwnerAgent(genai_client=genai_client, message_bus=message_bus)
    cs_agent = CSAgent(genai_client=genai_client, message_bus=message_bus)
    ads_agent = AdsAgent(genai_client=genai_client, message_bus=message_bus)
    debugger_agent = DebuggerAgent(genai_client=genai_client, message_bus=message_bus)

    # Register Agents
    registry.register(owner_agent)
    registry.register(cs_agent)
    registry.register(ads_agent)
    registry.register(debugger_agent)

    # Instantiate Self-Debugging Loop
    debugging_loop = SelfDebuggingLoop(debugger_agent=debugger_agent)

    # Instantiate Application Orchestrator
    orchestrator = ApplicationOrchestrator(
        engine=engine,
        registry=registry,
        message_bus=message_bus,
        debugging_loop=debugging_loop,
    )

    return orchestrator
