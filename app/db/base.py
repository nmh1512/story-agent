"""SQLAlchemy declarative base."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass

# Import all models here for Alembic
from app.db.models import (
    Story,
    Chapter,
    Character,
    CharacterState,
    ChapterSummary,
    StoryEvent,
    StoryHook,
    StoryState,
    StoryTask,
    ChapterReview,
    StoryOutline,
    AgentRun
)
