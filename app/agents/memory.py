"""Memory Update agent — extracts long term deterministic state from chapters."""

from __future__ import annotations

import logging

from app.core.llm_client import BaseLLMClient, get_llm_client
from app.prompts.memory import SYSTEM, build_memory_prompt
from app.schemas.memory import MemoryUpdateInput, MemoryUpdateOutput

logger = logging.getLogger(__name__)


class MemoryUpdateAgent:
    """Extracts state, events, and relations from chapters."""

    def __init__(self, llm: BaseLLMClient | None = None) -> None:
        self.llm = llm or get_llm_client()

    def run(self, inp: MemoryUpdateInput) -> MemoryUpdateOutput:
        """Parse chapter and build updated memory structures."""
        logger.info(
            "MemoryUpdateAgent running story_id=%d chapter_no=%d",
            inp.story_id,
            inp.chapter_no,
        )
        prompt = build_memory_prompt(inp)
        raw = self.llm.generate_json(
            prompt,
            system=SYSTEM,
            options={
                "max_tokens": 2048,
                "temperature": 0.4,
                "format": "json",
            }
        )


        if not raw:
            raise ValueError("MemoryUpdateAgent received empty response from LLM")

        raw.setdefault("story_id", inp.story_id)
        raw.setdefault("chapter_id", inp.chapter_id)
        raw.setdefault("chapter_no", inp.chapter_no)

        output = MemoryUpdateOutput.model_validate(raw)
        logger.info(
            "MemoryUpdateAgent done chapter_no=%d events=%d chars=%d rels=%d",
            output.chapter_no,
            len(output.key_events),
            len(output.character_state_updates),
            len(output.relation_updates),
        )
        return output
