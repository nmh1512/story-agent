"""Reviewer agent — scores chapters and generates rewrite instructions."""

from __future__ import annotations

import logging

from app.core.llm_client import BaseLLMClient, get_llm_client
from app.prompts.reviewer import SYSTEM, build_reviewer_prompt
from app.schemas.reviewer import ReviewerInput, ReviewerOutput

logger = logging.getLogger(__name__)


class ReviewerAgent:
    """Evaluates written chapters."""

    def __init__(self, llm: BaseLLMClient | None = None) -> None:
        self.llm = llm or get_llm_client()

    def run(self, inp: ReviewerInput) -> ReviewerOutput:
        """Score chapter and return validated ReviewerOutput."""
        logger.info(
            "ReviewerAgent running story_id=%d chapter_no=%d",
            inp.story_id,
            inp.chapter_no,
        )
        prompt = build_reviewer_prompt(inp)
        raw = self.llm.generate_json(
            prompt, 
            system=SYSTEM,
            options={
                "max_tokens": 1024,
                "temperature": 0.5,
                "format": "json",
            }
        )

        if not raw:
            raise ValueError("ReviewerAgent received empty response from LLM")

        raw.setdefault("story_id", inp.story_id)
        raw.setdefault("chapter_id", inp.chapter_id)
        
        # Enforce threshold logic
        score = raw.get("score", 10)
        target = inp.target_quality_threshold
        if score < target:
            raw["should_rewrite"] = True

        output = ReviewerOutput.model_validate(raw)
        logger.info(
            "ReviewerAgent done chapter_no=%d score=%d rewrite=%s",
            output.chapter_id,
            output.score,
            output.should_rewrite,
        )
        return output
