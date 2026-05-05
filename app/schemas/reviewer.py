"""Pydantic V2 schemas for the Reviewer agent."""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class ReviewerInput(BaseModel):
    story_id: int
    chapter_id: int
    chapter_no: int
    chapter_title: str
    chapter_content: str
    outline: dict[str, Any] | None = None
    current_story_state: dict[str, Any] | None = None
    recent_summaries: list[dict[str, Any]] = Field(default_factory=list)
    target_quality_threshold: int = 7


class ReviewerOutput(BaseModel):
    story_id: int
    chapter_id: int
    score: int
    verdict: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    notes: str = ""
    rewrite_notes: list[str] = Field(default_factory=list)
    should_rewrite: bool = False
