"""Abstract base strategy for all LLM clients."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseLLMClient(ABC):
    """Abstract base — all concrete LLM strategies implement this."""

    @abstractmethod
    def generate(self, prompt: str, system: str | None = None, options: dict[str, Any] | None = None) -> str:
        """Return raw text response from the model."""

    def generate_json(self, prompt: str, system: str | None = None, options: dict[str, Any] | None = None) -> Any:
        """Generate and JSON-parse the response."""
        from app.utils.json_repair import parse_json_safe
        raw = self.generate(prompt, system, options=options)
        return parse_json_safe(raw)

    def _extract_options(self, options: dict[str, Any] | None, key: str, default: Any) -> Any:
        """Helper to safely extract a value from options dict."""
        return (options or {}).get(key, default)
