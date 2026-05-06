"""Google Gemini API strategy."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.core.config import settings
from app.core.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)


class GeminiClient(BaseLLMClient):
    """Calls Google Gemini API via google-generativeai SDK."""

    def __init__(
        self,
        api_key: str = settings.LLM_API_KEY_GEMINI,
        model: str = settings.LLM_MODEL,
        timeout: int = settings.LLM_TIMEOUT,
        max_retries: int = settings.LLM_MAX_RETRIES,
    ) -> None:
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("google-generativeai is required. Run: pip install google-generativeai")

        if not api_key:
            raise ValueError("LLM_API_KEY_GEMINI is not set in .env")

        genai.configure(api_key=api_key)
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries

    def generate(self, prompt: str, system: str | None = None, options: dict[str, Any] | None = None) -> str:
        import google.generativeai as genai
        from google.generativeai.types import GenerationConfig

        temperature = self._extract_options(options, "temperature", 0.7)
        max_tokens = self._extract_options(options, "max_tokens", 4096)
        use_json = self._extract_options(options, "format", None) == "json"

        generation_config = GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            response_mime_type="application/json" if use_json else "text/plain",
        )
        client = genai.GenerativeModel(
            model_name=self.model,
            system_instruction=system,
            generation_config=generation_config,
        )

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug("Gemini request model=%s attempt=%d", self.model, attempt)
                t0 = time.monotonic()
                response = client.generate_content(prompt)
                elapsed = time.monotonic() - t0
                text = response.text
                logger.info("Gemini response model=%s elapsed=%.1fs chars=%d", self.model, elapsed, len(text))
                return text
            except Exception as exc:
                logger.warning("Gemini attempt %d failed: %s", attempt, exc)
                if attempt == self.max_retries:
                    raise
                time.sleep(2 ** attempt)

        raise RuntimeError("Gemini generate failed after all retries")
