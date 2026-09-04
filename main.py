"""Main application entry point for Multi-Agent AI System scaffold."""

import logging
import sys

from config import get_genai_client, get_settings
from core.exceptions import ApplicationError, ConfigurationError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("main")


def main() -> None:
    """Initialize and bootstrap application foundation."""
    logger.info("Initializing Multi-Agent AI System foundation...")

    try:
        settings = get_settings()
        logger.info("Configuration loaded successfully (Environment: %s)", settings.environment)
    except Exception as e:
        logger.error("Configuration loading failed: %s", str(e))
        sys.exit(1)

    # Check for Google GenAI client readiness if credentials are provided
    try:
        if settings.google_api_key or settings.gemini_api_key:
            _ = get_genai_client(settings)
            logger.info("Google GenAI client initialized successfully.")
        else:
            logger.info(
                "No API key detected in environment. GenAI client initialization skipped for Phase 1 setup."
            )
    except ConfigurationError as e:
        logger.warning("GenAI client setup notice: %s", str(e))

    logger.info("Multi-Agent AI System Phase 1 foundation initialized successfully.")


if __name__ == "__main__":
    main()
