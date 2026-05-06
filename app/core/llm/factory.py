"""Factory — resolves the correct LLM strategy based on config."""

from __future__ import annotations

import logging

from app.core.config import settings
from app.core.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)

_PROVIDER_MAP: dict[str, str] = {
    "ollama": "app.core.llm.ollama.OllamaClient",
    "openai_compatible": "app.core.llm.openai_compat.OpenAICompatibleLocalClient",
    "gemini": "app.core.llm.gemini.GeminiClient",
    "openai": "app.core.llm.openai.OpenAIClient",
}


def get_llm_client(provider: str | None = None) -> BaseLLMClient:
    """Resolve and return the configured LLM strategy.

    Args:
        provider: Override the provider from settings (e.g. for per-agent override).
    """
    key = (provider or settings.LLM_PROVIDER).lower()
    dotted = _PROVIDER_MAP.get(key)

    if dotted is None:
        supported = ", ".join(_PROVIDER_MAP.keys())
        raise ValueError(f"Unknown LLM provider '{key}'. Supported: {supported}")

    module_path, class_name = dotted.rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    cls: type[BaseLLMClient] = getattr(module, class_name)

    logger.debug("LLM strategy resolved: %s -> %s", key, cls.__name__)
    return cls()
