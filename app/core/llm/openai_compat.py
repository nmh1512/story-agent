"""OpenAI-compatible local endpoint strategy (LM Studio, vLLM, etc.)."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.core.config import settings
from app.core.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)


class OpenAICompatibleLocalClient(BaseLLMClient):
    """Calls any OpenAI-compatible /v1/chat/completions local endpoint."""

    def __init__(
        self,
        base_url: str = settings.LLM_BASE_URL,
        model: str = settings.LLM_MODEL,
        timeout: int = settings.LLM_TIMEOUT,
        max_retries: int = settings.LLM_MAX_RETRIES,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries

    def generate(self, prompt: str, system: str | None = None, options: dict[str, Any] | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        use_json = self._extract_options(options, "format", None) == "json"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self._extract_options(options, "temperature", 0.7),
            "max_tokens": self._extract_options(options, "max_tokens", 2048),
            "response_format": {"type": "json_object"} if use_json else {"type": "text"},
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                t0 = time.monotonic()
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(f"{self.base_url}/v1/chat/completions", json=payload)
                    resp.raise_for_status()
                elapsed = time.monotonic() - t0
                data = resp.json()
                text: str = data["choices"][0]["message"]["content"]
                logger.info("OpenAI-compat response model=%s elapsed=%.1fs", self.model, elapsed)
                return text
            except Exception as exc:
                logger.warning("OpenAI-compat attempt %d failed: %s", attempt, exc)
                if attempt == self.max_retries:
                    raise
                time.sleep(2 ** attempt)

        raise RuntimeError("OpenAI-compat generate failed after all retries")
