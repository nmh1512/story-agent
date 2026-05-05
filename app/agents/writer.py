"""Writer agent — writes and rewrites chapters from context."""

from __future__ import annotations

import logging

from app.core.llm_client import BaseLLMClient, get_llm_client
from app.prompts.writer import SYSTEM, build_writer_prompt
from app.schemas.writer import WriterInput, WriterOutput

logger = logging.getLogger(__name__)


class WriterAgent:
    """Writes novel chapters according to outlines and story memory."""

    def __init__(self, llm: BaseLLMClient | None = None) -> None:
        self.llm = llm or get_llm_client()

    def run(self, inp: WriterInput) -> WriterOutput:
        """Generate chapter content and return a validated WriterOutput."""
        logger.info(
            "WriterAgent running story_id=%d chapter_no=%d mode=%s",
            inp.story_id,
            inp.chapter_no,
            inp.mode,
        )
        prompt = build_writer_prompt(inp)
        raw = self.llm.generate_json(
            prompt, 
            system=SYSTEM,
            options={
                "num_ctx": 4096,
                "num_predict": 2000,
                "temperature": 0.6,
            }
        )

        if not raw:
            raise ValueError("WriterAgent received empty response from LLM")

        # Ensure required fields
        raw.setdefault("story_id", inp.story_id)
        raw.setdefault("chapter_no", inp.chapter_no)
        
        # fallback simple count if missing
        if "word_count" not in raw or not isinstance(raw["word_count"], int):
            content_str = raw.get("content", "")
            raw["word_count"] = len(content_str.split())

        output = WriterOutput.model_validate(raw)
        logger.info(
            "WriterAgent done chapter_no=%d words=%d",
            output.chapter_no,
            output.word_count,
        )
        return output
