"""LLM client abstraction — supports Ollama and any OpenAI-compatible local endpoint."""

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, system: str | None = None, options: dict[str, Any] | None = None) -> str:
        """Return raw text response from the model."""

    def generate_json(self, prompt: str, system: str | None = None, options: dict[str, Any] | None = None) -> Any:
        """Generate and JSON-parse the response with simple retry."""
        from app.utils.json_repair import parse_json_safe

        raw = self.generate(prompt, system, options=options)
        return parse_json_safe(raw)


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
            llm_options.update(options)

        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": llm_options
        }
        if options and "format" in options:
            payload["format"] = options["format"]
            
        if system:
            payload["system"] = system

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(
                    "Ollama request model=%s attempt=%d prompt_len=%d",
                    self.model,
                    attempt,
                    len(prompt),
                )
                t0 = time.monotonic()
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(f"{self.base_url}/api/generate", json=payload)
                    resp.raise_for_status()
                elapsed = time.monotonic() - t0
                data = resp.json()
                response_text: str = data.get("response", "")
                logger.info(
                    "Ollama response model=%s elapsed=%.1fs tokens=%s",
                    self.model,
                    elapsed,
                    data.get("eval_count", "?"),
                )
                return response_text
            except Exception as exc:
                logger.warning("Ollama attempt %d failed: %s", attempt, exc)
                if attempt == self.max_retries:
                    raise
                time.sleep(2 ** attempt)

        raise RuntimeError("Ollama generate failed after all retries")


class OpenAICompatibleLocalClient(BaseLLMClient):
    """Calls any OpenAI-compatible /v1/chat/completions endpoint (LM Studio, vLLM, etc.)."""

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

    def generate(self, prompt: str, system: str | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {"model": self.model, "messages": messages}

        for attempt in range(1, self.max_retries + 1):
            try:
                t0 = time.monotonic()
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(
                        f"{self.base_url}/v1/chat/completions", json=payload
                    )
                    resp.raise_for_status()
                elapsed = time.monotonic() - t0
                data = resp.json()
                text: str = data["choices"][0]["message"]["content"]
                logger.info(
                    "OpenAI-compat response model=%s elapsed=%.1fs", self.model, elapsed
                )
                return text
            except Exception as exc:
                logger.warning("OpenAI-compat attempt %d failed: %s", attempt, exc)
                if attempt == self.max_retries:
                    raise
                time.sleep(2 ** attempt)

        raise RuntimeError("OpenAI-compat generate failed after all retries")


def get_llm_client() -> BaseLLMClient:
    """Factory: returns the configured LLM client."""
    provider = settings.LLM_PROVIDER.lower()
    if provider == "openai_compatible":
        return OpenAICompatibleLocalClient()
    return OllamaClient()
