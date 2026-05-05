"""Pydantic V2 schemas for the Writer agent."""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class WriterInput(BaseModel):
    story_id: int
    outline_id: int
    chapter_no: int
    genre: str
    premise: str
    style_guide: str | None = None
    world_bible: dict[str, Any] = Field(default_factory=dict)
    current_story_state: dict[str, Any] = Field(default_factory=dict)
    relevant_character_states: list[dict[str, Any]] = Field(default_factory=list)
    relation_snapshot: list[dict[str, Any]] = Field(default_factory=list)
    open_hooks: list[dict[str, Any]] = Field(default_factory=list)
    recent_full_chapters: list[dict[str, Any]] = Field(default_factory=list)
    older_summaries: list[dict[str, Any]] = Field(default_factory=list)
    outline: dict[str, Any] = Field(default_factory=dict)
    mode: str = "write"  # "write" | "rewrite"
    rewrite_notes: list[str] | None = None
    target_word_count: int | None = None


class WriterOutput(BaseModel):
    story_id: int
    chapter_no: int
    title: str
    content: str
    word_count: int
    new_facts: list[str] = Field(default_factory=list)
    newly_introduced_hooks: list[str] = Field(default_factory=list)
    affected_character_ids: list[int] = Field(default_factory=list)
    continuity_notes: list[str] = Field(default_factory=list)
