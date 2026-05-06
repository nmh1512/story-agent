"""Ollama local HTTP API strategy."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.core.config import settings
from app.core.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)


class OllamaClient(BaseLLMClient):
    """Calls the Ollama HTTP /api/generate endpoint."""

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
        llm_options = {
            "num_ctx": 2048,
            "num_predict": 1024,
            "temperature": 0.7,
        }
        if options:
            # max_tokens is a universal alias — map to Ollama-specific num_predict
            if "max_tokens" in options and "num_predict" not in options:
                options = {**options, "num_predict": options.pop("max_tokens")}
            llm_options.update(options)

        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {k: v for k, v in llm_options.items() if k != "format"},
        }
        if "format" in llm_options:
            payload["format"] = llm_options["format"]
        if system:
            payload["system"] = system

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug("Ollama request model=%s attempt=%d", self.model, attempt)
                t0 = time.monotonic()
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(f"{self.base_url}/api/generate", json=payload)
                    resp.raise_for_status()
                elapsed = time.monotonic() - t0
                data = resp.json()
                text: str = data.get("response", "")
                logger.info("Ollama response model=%s elapsed=%.1fs tokens=%s", self.model, elapsed, data.get("eval_count", "?"))
                return text
            except Exception as exc:
                logger.warning("Ollama attempt %d failed: %s", attempt, exc)
                if attempt == self.max_retries:
                    raise
                time.sleep(2 ** attempt)

        raise RuntimeError("Ollama generate failed after all retries")
