"""Pydantic V2 schemas for the Memory Update agent."""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class MemoryUpdateInput(BaseModel):
    story_id: int
    chapter_id: int
    chapter_no: int
    chapter_title: str
    chapter_content: str
    previous_story_state: dict[str, Any] | None = None
    previous_character_states: list[dict[str, Any]] = Field(default_factory=list)
    previous_open_hooks: list[dict[str, Any]] = Field(default_factory=list)
    previous_relation_snapshot: list[dict[str, Any]] = Field(default_factory=list)


class MemoryUpdateOutput(BaseModel):
    story_id: int
    chapter_id: int
    chapter_no: int
    chapter_summary: str
    key_events: list[dict[str, Any]] = Field(default_factory=list)
    character_state_updates: list[dict[str, Any]] = Field(default_factory=list)
    relation_updates: list[dict[str, Any]] = Field(default_factory=list)
    new_hooks: list[dict[str, Any]] = Field(default_factory=list)
    resolved_hooks: list[dict[str, Any]] = Field(default_factory=list)
    story_state_update: dict[str, Any] = Field(default_factory=dict)
