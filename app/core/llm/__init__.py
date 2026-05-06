"""app.core.llm — LLM Strategy Pattern package.

Public API:
    from app.core.llm import BaseLLMClient, get_llm_client
"""

from app.core.llm.base import BaseLLMClient
from app.core.llm.factory import get_llm_client

__all__ = ["BaseLLMClient", "get_llm_client"]
