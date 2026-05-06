"""Backward-compatible shim — re-exports from app.core.llm package.

All agents import from here. The actual implementations live in app/core/llm/.
"""

from app.core.llm.base import BaseLLMClient
from app.core.llm.factory import get_llm_client
from app.core.llm.ollama import OllamaClient
from app.core.llm.openai_compat import OpenAICompatibleLocalClient
from app.core.llm.gemini import GeminiClient
from app.core.llm.openai import OpenAIClient

__all__ = [
    "BaseLLMClient",
    "get_llm_client",
    "OllamaClient",
    "OpenAICompatibleLocalClient",
    "GeminiClient",
    "OpenAIClient",
]
