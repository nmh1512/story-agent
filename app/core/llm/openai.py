"""OpenAI API strategy."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.core.config import settings
from app.core.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)


class OpenAIClient(BaseLLMClient):
    """Calls OpenAI API via the official openai SDK."""

    def __init__(
        self,
        api_key: str = settings.LLM_API_KEY_OPENAI,
        model: str = settings.LLM_MODEL,
        timeout: int = settings.LLM_TIMEOUT,
        max_retries: int = settings.LLM_MAX_RETRIES,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai is required. Run: pip install openai")

        if not api_key:
            raise ValueError("LLM_API_KEY_OPENAI is not set in .env")

        self._client = OpenAI(api_key=api_key, timeout=timeout, max_retries=max_retries)
        self.model = model
        self.max_retries = max_retries

    def generate(self, prompt: str, system: str | None = None, options: dict[str, Any] | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        use_json = self._extract_options(options, "format", None) == "json"
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self._extract_options(options, "temperature", 0.7),
            "max_tokens": self._extract_options(options, "max_tokens", 4096),
        }
        if use_json:
            kwargs["response_format"] = {"type": "json_object"}

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug("OpenAI request model=%s attempt=%d", self.model, attempt)
                t0 = time.monotonic()
                response = self._client.chat.completions.create(**kwargs)
                elapsed = time.monotonic() - t0
                text = response.choices[0].message.content or ""
                logger.info(
                    "OpenAI response model=%s elapsed=%.1fs tokens=%s",
                    self.model, elapsed,
                    response.usage.total_tokens if response.usage else "?",
                )
                return text
            except Exception as exc:
                logger.warning("OpenAI attempt %d failed: %s", attempt, exc)
                if attempt == self.max_retries:
                    raise
                time.sleep(2 ** attempt)

        raise RuntimeError("OpenAI generate failed after all retries")
