"""Planner agent — generates daily chapter outlines."""

from __future__ import annotations

import logging
from datetime import date

from app.core.llm_client import BaseLLMClient, get_llm_client
from app.prompts.planner import SYSTEM, build_planner_prompt
from app.schemas.planner import PlannerInput, PlannerOutput

logger = logging.getLogger(__name__)


class PlannerAgent:
    """Creates chapter outlines from story context."""

    def __init__(self, llm: BaseLLMClient | None = None) -> None:
        self.llm = llm or get_llm_client()

    def run(self, inp: PlannerInput) -> PlannerOutput:
        """Generate a chapter outline and return a validated PlannerOutput."""
        logger.info(
            "PlannerAgent running story_id=%d chapter_no=%d mode=%s",
            inp.story_id,
            inp.target_chapter_no,
            inp.planner_mode,
        )
        prompt = build_planner_prompt(inp)
        logger.info("PlannerAgent Prompt: \n%s", prompt)
        raw = self.llm.generate_json(
            prompt, 
            system=SYSTEM, 
            options={
                "num_ctx": 8192,
                "num_predict": 4096,
                "temperature": 0.6,
                "format": "json"
            }
        )

        logger.debug("PlannerAgent raw output: %s", raw)

        if not raw:
            raise ValueError("PlannerAgent received empty response from LLM")
        
        if not isinstance(raw, dict):
            logger.error("PlannerAgent expected dict but got %s: %s", type(raw), raw)
            raise ValueError(f"PlannerAgent received invalid JSON format (expected object, got {type(raw).__name__}). Raw output: {raw}")

        # Ensure required fields exist
        raw.setdefault("story_id", inp.story_id)
        raw.setdefault("chapter_no", inp.target_chapter_no)
        raw.setdefault("creates_write_task", True)

        output = PlannerOutput.model_validate(raw)
        logger.info(
            "PlannerAgent done chapter_no=%d theme=%s", output.chapter_no, output.theme
        )
        return output
