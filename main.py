"""Main application entry point for Multi-Agent AI System scaffold."""

import logging
import sys
from typing import Optional

from config import get_settings
from core.ai.genai_client import GenAIClient
from core.exceptions import ApplicationError, ConfigurationError
from agents import AgentEngine, AgentRegistry, InMemoryMessageBus, OwnerAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("main")


def main() -> None:
    """Initialize and bootstrap Phase 2 multi-agent system application."""
    logger.info("Initializing Multi-Agent AI System Phase 2 architecture...")

    try:
        settings = get_settings()
        logger.info(
            "Configuration loaded successfully (Environment: %s, Model: %s)",
            settings.environment,
            settings.gemini_model,
        )
    except Exception as e:
        logger.error("Configuration loading failed: %s", str(e))
        sys.exit(1)

    # Initialize central GenAI Client if API key is provided
    genai_client: Optional[GenAIClient] = None
    try:
        if settings.google_api_key or settings.gemini_api_key:
            genai_client = GenAIClient(settings=settings)
            logger.info("Central GenAIClient initialized successfully.")
        else:
            logger.info(
                "No API key detected in environment. GenAIClient initialization skipped for bootstrap check."
            )
    except ConfigurationError as e:
        logger.warning("GenAI client setup notice: %s", str(e))

    # Initialize Message Bus, Agent Registry, and Agent Engine
    message_bus = InMemoryMessageBus()
    registry = AgentRegistry()
    engine = AgentEngine(registry=registry, message_bus=message_bus)

    # Register Owner Agent if GenAI client is available (or register dummy/mock in production setup)
    if genai_client is not None:
        owner_agent = OwnerAgent(genai_client=genai_client, message_bus=message_bus)
        registry.register(owner_agent)
        logger.info("OwnerAgent registered successfully in AgentRegistry.")

    registered_agents = [agent.agent_id for agent in registry.list_agents()]
    logger.info("Active registered agents in system: %s", registered_agents)
    logger.info("Multi-Agent AI System Phase 2 foundation initialized successfully.")


if __name__ == "__main__":
    main()
