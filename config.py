"""Application configuration management module."""

import logging
import os
from typing import Any, Optional

from dotenv import load_dotenv
from google import genai
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings

from core.exceptions import ConfigurationError

# Load environment variables from .env file if present
load_dotenv()

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings and credential configuration.

    Reads environment variables with priority:
    1. GOOGLE_API_KEY (primary)
    2. GEMINI_API_KEY (fallback)
    """

    google_api_key: Optional[SecretStr] = Field(
        default=None, alias="GOOGLE_API_KEY"
    )
    gemini_api_key: Optional[SecretStr] = Field(
        default=None, alias="GEMINI_API_KEY"
    )
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,
    }

    @property
    def api_key(self) -> str:
        """Get the active Google GenAI API key.

        Prefers GOOGLE_API_KEY over GEMINI_API_KEY.
        Raises ConfigurationError if neither key is provided.
        """
        key_secret = self.google_api_key or self.gemini_api_key
        if not key_secret or not key_secret.get_secret_value():
            raise ConfigurationError(
                "Missing required Google GenAI API key. "
                "Set GOOGLE_API_KEY or GEMINI_API_KEY in environment variables or .env file."
            )
        return key_secret.get_secret_value()

    def __repr__(self) -> str:
        """Represent settings without exposing secret API keys."""
        return (
            f"Settings(environment={self.environment!r}, "
            f"log_level={self.log_level!r}, "
            f"google_api_key={'***' if self.google_api_key else None!r}, "
            f"gemini_api_key={'***' if self.gemini_api_key else None!r})"
        )

    def __str__(self) -> str:
        return self.__repr__()


_settings_instance: Optional[Settings] = None


def get_settings(reload: bool = False) -> Settings:
    """Get or initialize application settings singleton.

    Args:
        reload: Force re-reading environment variables if True.

    Returns:
        Settings: Validated application settings instance.
    """
    global _settings_instance
    if _settings_instance is None or reload:
        load_dotenv(override=True)
        _settings_instance = Settings()
    return _settings_instance


def get_genai_client(settings: Optional[Settings] = None) -> genai.Client:
    """Instantiate and return a centrally configured official Google GenAI Client.

    Args:
        settings: Optional Settings object. Uses get_settings() if None.

    Returns:
        genai.Client: Initialized Google GenAI client.

    Raises:
        ConfigurationError: If API key is missing or client initialization fails.
    """
    if settings is None:
        settings = get_settings()

    api_key = settings.api_key
    try:
        client = genai.Client(api_key=api_key)
        return client
    except Exception as e:
        logger.error("Failed to initialize Google GenAI Client: %s", str(e))
        raise ConfigurationError(f"Failed to initialize Google GenAI Client: {e}") from e
