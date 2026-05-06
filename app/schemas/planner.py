"""Pydantic V2 schemas for the Planner agent."""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class PlannerInput(BaseModel):
    story_id: int | None = None
    story_title: str | None = None
    genre: str | None = None
    premise: str | None = None
    style_guide: str | None = None
    world_bible: dict[str, Any] = Field(default_factory=dict)
    current_story_state: dict[str, Any] | None = None
    recent_chapter_summaries: list[dict[str, Any]] = Field(default_factory=list)
    open_hooks: list[dict[str, Any]] = Field(default_factory=list)
    planner_mode: str = "next_chapter_outline"  # "story_genesis" | "next_chapter_outline"
    target_date: str
    target_chapter_no: int = 1


class ChapterPlan(BaseModel):
    chapter_no: int
    title: str
    summary: str
    outline: dict[str, Any] = Field(default_factory=dict)
    key_events: list[str] = Field(default_factory=list)


class ActPlan(BaseModel):
    title: str
    summary: str

class PlannerOutput(BaseModel):
    recent_events_analysis: str | None = Field(None, description="Tóm tắt ngắn gọn chương liền trước để nhận thức rõ nhân vật vừa làm gì.")
    new_direction_decision: str | None = Field(None, description="Cam kết bẻ lái sang một tình huống HOÀN TOÀN KHÁC để không bị lặp lại ý tưởng của chương trước.")
    # Story Genesis fields (optional, used when creating a new story)
    title: str | None = None
    genre: str | None = None
    premise: str | None = None
    backstory: str | None = None # Detailed world/story history
    arc_overview: str | None = None # High-level plan for the first story arc
    world_bible: dict[str, Any] | None = None
    initial_characters: list[dict[str, Any]] | None = None # [{code, name, role, description}]
    
    # Full Series Script (for 10-20 chapters)
    series_plan: list[ChapterPlan] | None = None
    act_summaries: list[ActPlan] | None = None # Structured summary for Act 1, 2, and 3

    # Chapter Planning fields
    story_id: int | None = None # Optional during Genesis
    # Chapter-specific fields (for the current target chapter)
    chapter_no: int | None = None
    theme: str = "Tên chương đang cập nhật"
    summary: str = "Tóm tắt đang cập nhật"
    outline: dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed outline including chapter_goal, chapter_purpose, scene_list, ending_hook, and tone."
    )
    must_include: list[str] = Field(default_factory=list)
    must_avoid: list[str] = Field(default_factory=list)
    continuity_notes: list[str] = Field(default_factory=list)
    suggested_characters: list[str] = Field(default_factory=list)
    relationship_focus: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of relationship dynamics to focus on in this chapter."
    )
    hook_strategy: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Strategy for advancing, resolving, or creating hooks."
    )
    creates_write_task: bool = True

