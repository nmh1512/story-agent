"""SQLAlchemy ORM models — all 12 tables."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────
class StoryStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    completed = "completed"
    archived = "archived"


class OutlineStatus(str, enum.Enum):
    pending = "pending"
    used = "used"
    skipped = "skipped"


class TaskType(str, enum.Enum):
    plan = "plan"
    write = "write"
    review = "review"
    rewrite = "rewrite"
    memory_update = "memory_update"


class TaskStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    failed = "failed"
    cancelled = "cancelled"


class ChapterStatus(str, enum.Enum):
    draft = "draft"
    reviewed = "reviewed"
    approved = "approved"
    rewriting = "rewriting"


class HookStatus(str, enum.Enum):
    open = "open"
    resolved = "resolved"


class AgentRunStatus(str, enum.Enum):
    started = "started"
    done = "done"
    failed = "failed"


# ──────────────────────────────────────────────
# 8.1  stories
# ──────────────────────────────────────────────
class Story(Base):
    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    genre: Mapped[str] = mapped_column(String(128), nullable=False)
    premise: Mapped[str] = mapped_column(Text, nullable=False)
    backstory: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    arc_overview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    style_guide: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    world_bible_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[StoryStatus] = mapped_column(
        Enum(StoryStatus), default=StoryStatus.active, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # relationships
    outlines: Mapped[list[StoryOutline]] = relationship(back_populates="story")
    tasks: Mapped[list[StoryTask]] = relationship(back_populates="story")
    chapters: Mapped[list[Chapter]] = relationship(back_populates="story")
    characters: Mapped[list[Character]] = relationship(back_populates="story")
    story_state: Mapped[Optional[StoryState]] = relationship(
        back_populates="story", uselist=False
    )


# ──────────────────────────────────────────────
# 8.2  story_outlines
# ──────────────────────────────────────────────
class StoryOutline(Base):
    __tablename__ = "story_outlines"
    __table_args__ = (
        Index("ix_outlines_story_date", "story_id", "outline_date"),
        Index("ix_outlines_status", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    story_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("stories.id"), nullable=False
    )
    outline_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    chapter_no: Mapped[int] = mapped_column(Integer, nullable=False)
    theme: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    outline_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[OutlineStatus] = mapped_column(
        Enum(OutlineStatus), default=OutlineStatus.pending, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    story: Mapped[Story] = relationship(back_populates="outlines")
    tasks: Mapped[list[StoryTask]] = relationship(back_populates="outline")


# ──────────────────────────────────────────────
# 8.3  story_tasks
# ──────────────────────────────────────────────
class StoryTask(Base):
    __tablename__ = "story_tasks"
    __table_args__ = (
        Index("ix_tasks_story_status", "story_id", "status"),
        Index("ix_tasks_type_status", "task_type", "status"),
        Index("ix_tasks_scheduled", "scheduled_for"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    story_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("stories.id"), nullable=False
    )
    outline_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("story_outlines.id"), nullable=True
    )
    chapter_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("chapters.id"), nullable=True
    )
    task_type: Mapped[TaskType] = mapped_column(Enum(TaskType), nullable=False)
    payload_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    priority: Mapped[int] = mapped_column(SmallInteger, default=5, nullable=False)
    scheduled_for: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), default=TaskStatus.pending, nullable=False
    )
    retry_count: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    story: Mapped[Story] = relationship(back_populates="tasks")
    outline: Mapped[Optional[StoryOutline]] = relationship(back_populates="tasks")
    chapter: Mapped[Optional["Chapter"]] = relationship(
        foreign_keys=[chapter_id], back_populates="tasks"
    )


# ──────────────────────────────────────────────
# 8.4  chapters
# ──────────────────────────────────────────────
class Chapter(Base):
    __tablename__ = "chapters"
    __table_args__ = (
        Index("ix_chapters_story_no", "story_id", "chapter_no"),
        Index("ix_chapters_status", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    story_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("stories.id"), nullable=False
    )
    outline_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("story_outlines.id"), nullable=True
    )
    chapter_no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text(length=4294967295), nullable=False)  # LONGTEXT
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    version_no: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    status: Mapped[ChapterStatus] = mapped_column(
        Enum(ChapterStatus), default=ChapterStatus.draft, nullable=False
    )
    review_score: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    needs_rewrite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    story: Mapped[Story] = relationship(back_populates="chapters")
    tasks: Mapped[list[StoryTask]] = relationship(
        foreign_keys=[StoryTask.chapter_id], back_populates="chapter"
    )
    summary: Mapped[Optional["ChapterSummary"]] = relationship(
        back_populates="chapter", uselist=False
    )
    reviews: Mapped[list["ChapterReview"]] = relationship(back_populates="chapter")


# ──────────────────────────────────────────────
# 8.5  chapter_summaries
# ──────────────────────────────────────────────
class ChapterSummary(Base):
    __tablename__ = "chapter_summaries"
    __table_args__ = (Index("ix_csummary_story_no", "story_id", "chapter_no"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    chapter_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("chapters.id"), nullable=False, unique=True
    )
    story_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("stories.id"), nullable=False
    )
    chapter_no: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_events_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    character_updates_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    items_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    foreshadow_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    chapter: Mapped[Chapter] = relationship(back_populates="summary")


# ──────────────────────────────────────────────
# 8.6  chapter_reviews
# ──────────────────────────────────────────────
class ChapterReview(Base):
    __tablename__ = "chapter_reviews"
    __table_args__ = (Index("ix_review_chapter", "chapter_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    chapter_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("chapters.id"), nullable=False
    )
    story_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("stories.id"), nullable=False
    )
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    verdict: Mapped[str] = mapped_column(String(64), nullable=False)
    strengths_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    weaknesses_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rewrite_notes_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    chapter: Mapped[Chapter] = relationship(back_populates="reviews")


# ──────────────────────────────────────────────
# 8.7  story_states
# ──────────────────────────────────────────────
class StoryState(Base):
    __tablename__ = "story_states"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    story_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("stories.id"), nullable=False, unique=True
    )
    current_chapter_no: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_arc: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    current_goal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    current_conflict: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    world_state_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    active_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    story: Mapped[Story] = relationship(back_populates="story_state")


# ──────────────────────────────────────────────
# 8.8  characters
# ──────────────────────────────────────────────
class Character(Base):
    __tablename__ = "characters"
    __table_args__ = (Index("ix_characters_story", "story_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    story_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("stories.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    personality_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    background: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="alive", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    story: Mapped[Story] = relationship(back_populates="characters")
    states: Mapped[list["CharacterState"]] = relationship(back_populates="character")


# ──────────────────────────────────────────────
# 8.9  character_states
# ──────────────────────────────────────────────
class CharacterState(Base):
    __tablename__ = "character_states"
    __table_args__ = (
        Index("ix_charstate_story_char", "story_id", "character_id"),
        Index("ix_charstate_chapter_no", "chapter_no"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    story_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("stories.id"), nullable=False
    )
    character_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("characters.id"), nullable=False
    )
    chapter_no: Mapped[int] = mapped_column(Integer, nullable=False)
    realm: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    goal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    emotion: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    inventory_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    secrets_known_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    state_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    character: Mapped[Character] = relationship(back_populates="states")


# ──────────────────────────────────────────────
# 8.10  story_events
# ──────────────────────────────────────────────
class StoryEvent(Base):
    __tablename__ = "story_events"
    __table_args__ = (
        Index("ix_events_story_no", "story_id", "chapter_no"),
        Index("ix_events_type", "event_type"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    story_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("stories.id"), nullable=False
    )
    chapter_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("chapters.id"), nullable=True
    )
    chapter_no: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    characters_involved_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    impact_level: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


# ──────────────────────────────────────────────
# 8.11  story_hooks
# ──────────────────────────────────────────────
class StoryHook(Base):
    __tablename__ = "story_hooks"
    __table_args__ = (
        Index("ix_hooks_story_status", "story_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    story_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("stories.id"), nullable=False
    )
    chapter_no_created: Mapped[int] = mapped_column(Integer, nullable=False)
    hook_text: Mapped[str] = mapped_column(Text, nullable=False)
    related_character_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("characters.id"), nullable=True
    )
    status: Mapped[HookStatus] = mapped_column(
        Enum(HookStatus), default=HookStatus.open, nullable=False
    )
    resolved_in_chapter: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


# ──────────────────────────────────────────────
# 8.12  agent_runs
# ──────────────────────────────────────────────
class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        Index("ix_runs_agent_status", "agent_name", "status"),
        Index("ix_runs_story", "story_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    agent_name: Mapped[str] = mapped_column(String(64), nullable=False)
    task_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("story_tasks.id"), nullable=True
    )
    story_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("stories.id"), nullable=True
    )
    chapter_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("chapters.id"), nullable=True
    )
    input_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    output_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[AgentRunStatus] = mapped_column(
        Enum(AgentRunStatus), default=AgentRunStatus.started, nullable=False
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
