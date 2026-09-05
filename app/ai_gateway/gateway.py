"""AI Gateway module isolating all Gemini API interactions.

Enforces rate limits, retries with exponential backoff, primary-to-fallback model switching,
token usage tracking, cost estimation, and standardized Pydantic v2 structured generation.
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional, Type, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

try:
    from app.core.config import Settings, get_settings
    from app.core.exceptions import ConfigurationError
    from app.ai_gateway.models import GatewayResponse, TokenUsage, UsageMetrics
except ImportError:
    from core.config import Settings, get_settings
    from core.exceptions import ConfigurationError
    from ai_gateway.models import GatewayResponse, TokenUsage, UsageMetrics

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Default estimated pricing per 1 million tokens (USD)
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "gemini-3.1-flash-lite": {"prompt": 0.075 / 1e6, "candidate": 0.30 / 1e6},
    "gemini-1.5-flash": {"prompt": 0.075 / 1e6, "candidate": 0.30 / 1e6},
    "gemini-2.5-flash": {"prompt": 0.075 / 1e6, "candidate": 0.30 / 1e6},
}
DEFAULT_PRICING = {"prompt": 0.10 / 1e6, "candidate": 0.40 / 1e6}


class AIGateway:
    """Centralized AI Gateway isolating all Gemini API operations."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        client: Optional[genai.Client] = None,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ) -> None:
        """Initialize AIGateway.

        Args:
            settings: Settings object.
            client: Pre-configured genai.Client instance for injection/testing.
            max_retries: Max retry attempts before failing or falling back.
            backoff_factor: Exponential backoff factor in seconds.
        """
        self._settings = settings or get_settings()
        self.primary_model = self._settings.gemini_model
        self.fallback_model = self._settings.gemini_fallback_model
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.metrics = UsageMetrics()

        if client is not None:
            self._client = client
        else:
            try:
                api_key = self._settings.api_key
                self._client = genai.Client(api_key=api_key)
            except Exception as e:
                logger.warning("AIGateway initialized without active GenAI client: %s", e)
                self._client = None

    @property
    def client(self) -> Optional[genai.Client]:
        """Get underlying GenAI client."""
        return self._client

    def calculate_cost(self, model: str, prompt_tokens: int, candidate_tokens: int) -> float:
        """Calculate estimated USD cost for token consumption."""
        pricing = MODEL_PRICING.get(model, DEFAULT_PRICING)
        cost = (prompt_tokens * pricing["prompt"]) + (candidate_tokens * pricing["candidate"])
        return round(cost, 8)

    def _extract_usage(self, raw_response: Any) -> TokenUsage:
        """Extract TokenUsage from raw SDK response."""
        prompt_tokens = 0
        candidate_tokens = 0
        if hasattr(raw_response, "usage_metadata") and raw_response.usage_metadata:
            um = raw_response.usage_metadata
            prompt_tokens = getattr(um, "prompt_token_count", 0) or 0
            candidate_tokens = getattr(um, "candidates_token_count", 0) or 0
        total_tokens = prompt_tokens + candidate_tokens
        return TokenUsage(
            prompt_tokens=prompt_tokens,
            candidate_tokens=candidate_tokens,
            total_tokens=total_tokens,
        )

    def _extract_finish_reason(self, raw_response: Any) -> Optional[str]:
        """Extract finish reason from raw SDK response."""
        if hasattr(raw_response, "candidates") and raw_response.candidates:
            first = raw_response.candidates[0]
            if hasattr(first, "finish_reason"):
                return str(first.finish_reason)
        return None

    def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> T:
        """Synchronously generate structured response validated by a Pydantic v2 model."""
        target_models = [model] if model else [self.primary_model, self.fallback_model]
        last_exception: Optional[Exception] = None

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_schema,
        )
        if system_instruction:
            config.system_instruction = system_instruction
        if temperature is not None:
            config.temperature = temperature

        for model_idx, target_model in enumerate(target_models):
            is_fallback = model_idx > 0
            for attempt in range(self.max_retries):
                try:
                    if not self._client:
                        raise ConfigurationError("AIGateway requires a configured genai.Client.")

                    raw_response = self._client.models.generate_content(
                        model=target_model,
                        contents=prompt,
                        config=config,
                    )

                    usage = self._extract_usage(raw_response)
                    cost = self.calculate_cost(target_model, usage.prompt_tokens, usage.candidate_tokens)
                    self.metrics.record_request(
                        prompt_tokens=usage.prompt_tokens,
                        candidate_tokens=usage.candidate_tokens,
                        cost_usd=cost,
                        used_fallback=is_fallback,
                    )

                    if hasattr(raw_response, "parsed") and raw_response.parsed is not None:
                        if isinstance(raw_response.parsed, response_schema):
                            return raw_response.parsed
                        return response_schema.model_validate(raw_response.parsed)
                    if raw_response.text:
                        return response_schema.model_validate_json(raw_response.text)

                    raise ValueError("Model returned empty text and unparseable structured output.")

                except Exception as e:
                    last_exception = e
                    logger.warning(
                        "Attempt %d/%d failed for model %s: %s",
                        attempt + 1,
                        self.max_retries,
                        target_model,
                        e,
                    )
                    if attempt < self.max_retries - 1:
                        time.sleep(self.backoff_factor * (2 ** attempt))

        self.metrics.total_requests += 1
        self.metrics.failed_requests += 1
        raise RuntimeError(f"AIGateway structured generation failed across all models: {last_exception}") from last_exception

    async def generate_structured_async(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> T:
        """Asynchronously generate structured response validated by a Pydantic v2 model."""
        target_models = [model] if model else [self.primary_model, self.fallback_model]
        last_exception: Optional[Exception] = None

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_schema,
        )
        if system_instruction:
            config.system_instruction = system_instruction
        if temperature is not None:
            config.temperature = temperature

        for model_idx, target_model in enumerate(target_models):
            is_fallback = model_idx > 0
            for attempt in range(self.max_retries):
                try:
                    if not self._client:
                        raise ConfigurationError("AIGateway requires a configured genai.Client.")

                    raw_response = await self._client.aio.models.generate_content(
                        model=target_model,
                        contents=prompt,
                        config=config,
                    )

                    usage = self._extract_usage(raw_response)
                    cost = self.calculate_cost(target_model, usage.prompt_tokens, usage.candidate_tokens)
                    self.metrics.record_request(
                        prompt_tokens=usage.prompt_tokens,
                        candidate_tokens=usage.candidate_tokens,
                        cost_usd=cost,
                        used_fallback=is_fallback,
                    )

                    if hasattr(raw_response, "parsed") and raw_response.parsed is not None:
                        if isinstance(raw_response.parsed, response_schema):
                            return raw_response.parsed
                        return response_schema.model_validate(raw_response.parsed)
                    if raw_response.text:
                        return response_schema.model_validate_json(raw_response.text)

                    raise ValueError("Model returned empty text and unparseable structured output.")

                except Exception as e:
                    last_exception = e
                    logger.warning(
                        "Async attempt %d/%d failed for model %s: %s",
                        attempt + 1,
                        self.max_retries,
                        target_model,
                        e,
                    )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.backoff_factor * (2 ** attempt))

        self.metrics.total_requests += 1
        self.metrics.failed_requests += 1
        raise RuntimeError(f"Async AIGateway structured generation failed across all models: {last_exception}") from last_exception

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> GatewayResponse:
        """Synchronously generate text response."""
        target_models = [model] if model else [self.primary_model, self.fallback_model]
        last_exception: Optional[Exception] = None

        config = types.GenerateContentConfig()
        if system_instruction:
            config.system_instruction = system_instruction
        if temperature is not None:
            config.temperature = temperature

        for model_idx, target_model in enumerate(target_models):
            is_fallback = model_idx > 0
            for attempt in range(self.max_retries):
                try:
                    if not self._client:
                        raise ConfigurationError("AIGateway requires a configured genai.Client.")

                    raw_response = self._client.models.generate_content(
                        model=target_model,
                        contents=prompt,
                        config=config,
                    )

                    usage = self._extract_usage(raw_response)
                    cost = self.calculate_cost(target_model, usage.prompt_tokens, usage.candidate_tokens)
                    self.metrics.record_request(
                        prompt_tokens=usage.prompt_tokens,
                        candidate_tokens=usage.candidate_tokens,
                        cost_usd=cost,
                        used_fallback=is_fallback,
                    )

                    return GatewayResponse(
                        data=raw_response.text or "",
                        model=target_model,
                        usage=usage,
                        estimated_cost_usd=cost,
                        finish_reason=self._extract_finish_reason(raw_response),
                    )

                except Exception as e:
                    last_exception = e
                    if attempt < self.max_retries - 1:
                        time.sleep(self.backoff_factor * (2 ** attempt))

        self.metrics.total_requests += 1
        self.metrics.failed_requests += 1
        raise RuntimeError(f"AIGateway text generation failed across all models: {last_exception}") from last_exception

    async def generate_text_async(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> GatewayResponse:
        """Asynchronously generate text response."""
        target_models = [model] if model else [self.primary_model, self.fallback_model]
        last_exception: Optional[Exception] = None

        config = types.GenerateContentConfig()
        if system_instruction:
            config.system_instruction = system_instruction
        if temperature is not None:
            config.temperature = temperature

        for model_idx, target_model in enumerate(target_models):
            is_fallback = model_idx > 0
            for attempt in range(self.max_retries):
                try:
                    if not self._client:
                        raise ConfigurationError("AIGateway requires a configured genai.Client.")

                    raw_response = await self._client.aio.models.generate_content(
                        model=target_model,
                        contents=prompt,
                        config=config,
                    )

                    usage = self._extract_usage(raw_response)
                    cost = self.calculate_cost(target_model, usage.prompt_tokens, usage.candidate_tokens)
                    self.metrics.record_request(
                        prompt_tokens=usage.prompt_tokens,
                        candidate_tokens=usage.candidate_tokens,
                        cost_usd=cost,
                        used_fallback=is_fallback,
                    )

                    return GatewayResponse(
                        data=raw_response.text or "",
                        model=target_model,
                        usage=usage,
                        estimated_cost_usd=cost,
                        finish_reason=self._extract_finish_reason(raw_response),
                    )

                except Exception as e:
                    last_exception = e
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.backoff_factor * (2 ** attempt))

        self.metrics.total_requests += 1
        self.metrics.failed_requests += 1
        raise RuntimeError(f"Async AIGateway text generation failed across all models: {last_exception}") from last_exception
