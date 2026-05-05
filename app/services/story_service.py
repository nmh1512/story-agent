"""Story orchestration service handling DB logic and context assembly for tasks."""

from __future__ import annotations

import logging
from datetime import datetime, date

from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.db.models import (
    Story,
    StoryOutline,
    StoryTask,
    Chapter,
    ChapterSummary,
    ChapterReview,
    StoryState,
    Character,
    CharacterState,
    StoryEvent,
    StoryHook,
    AgentRun,
    TaskType,
    TaskStatus,
    HookStatus,
    ChapterStatus,
)
from app.graph.graph_service import GraphService
from app.agents.planner import PlannerAgent
from app.schemas.planner import PlannerInput
from app.agents.writer import WriterAgent
from app.schemas.writer import WriterInput
from app.agents.reviewer import ReviewerAgent
from app.schemas.reviewer import ReviewerInput
from app.agents.memory import MemoryUpdateAgent
from app.schemas.memory import MemoryUpdateInput
from app.core.config import settings

logger = logging.getLogger(__name__)


class StoryService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.graph = GraphService()

    # ──────────────────────────────────────────────────────────
    # Task 1: Planner
    # ──────────────────────────────────────────────────────────
    def initiate_new_story(self, target_date: str | None = None) -> Story:
        """Uses the planner to conceive a new story from scratch."""
        if not target_date:
            target_date = date.today().isoformat()
            
        inp = PlannerInput(
            planner_mode="story_genesis",
            target_date=target_date,
            target_chapter_no=1
        )
        
        agent = PlannerAgent()
        out = agent.run(inp)
        
        # Create story
        story = Story(
            code=f"GEN-{datetime.now().strftime('%Y%m%d%H%M')}",
            title=out.title or "Untitled Story",
            genre=out.genre or "Fiction",
            premise=out.premise or "Generated Story",
            backstory=out.backstory,
            arc_overview=out.arc_overview,
            world_bible_json=out.world_bible or {}
        )
        self.session.add(story)
        self.session.flush()
        
        # Create characters
        characters = []
        if out.initial_characters:
            for c_data in out.initial_characters:
                char = Character(
                    story_id=story.id,
                    code=c_data.get("code", "CHAR"),
                    name=c_data.get("name", "Unknown"),
                    role=c_data.get("role", "None"),
                    description=c_data.get("description", "")
                )
                self.session.add(char)
                characters.append(char)
            self.session.flush()
            
        # Create story state
        state = StoryState(story_id=story.id, current_chapter_no=0, world_state_json={})
        self.session.add(state)
        
        # Create initial character states
        for char in characters:
            cs = CharacterState(story_id=story.id, character_id=char.id, chapter_no=0, status="active")
            self.session.add(cs)
            
        # Sync to Graph
        self.graph.upsert_story(story.id, story.code, story.title, story.genre)
        for char in characters:
            self.graph.upsert_character(char.id, story.id, char.code, char.name, char.role)
            
        # Create story outlines from series plan if available
        if out.series_plan:
            for ch_plan in out.series_plan:
                # If this is Chapter 1, we use the detailed outline from the main response
                # Otherwise, we use the summary/outline from the ch_plan
                is_ch1 = ch_plan.chapter_no == 1
                
                outline = StoryOutline(
                    story_id=story.id,
                    outline_date=target_date,
                    chapter_no=ch_plan.chapter_no,
                    theme=out.theme if is_ch1 else f"Chapter {ch_plan.chapter_no}",
                    summary=out.summary if is_ch1 else ch_plan.summary,
                    outline_json=out.outline if is_ch1 else ch_plan.outline or {"summary": ch_plan.summary, "key_events": ch_plan.key_events}
                )
                self.session.add(outline)
                
                # If it's Chapter 1, we flush to get the ID for the writing task
                if is_ch1:
                    self.session.flush()
                    ch1_outline_id = outline.id
        else:
            # Fallback for old planner logic (only Ch1)
            outline = StoryOutline(
                story_id=story.id,
                outline_date=target_date,
                chapter_no=1,
                theme=out.theme,
                summary=out.summary,
                outline_json=out.outline
            )
            self.session.add(outline)
            self.session.flush()
            ch1_outline_id = outline.id
        
        # Create Task for Chapter 1
        task = StoryTask(
            story_id=story.id,
            outline_id=ch1_outline_id,
            task_type=TaskType.write,
            payload_json={"mode": "write"},
            scheduled_for=datetime.now()
        )

        self.session.add(task)
        
        # Log run
        run = AgentRun(
            agent_name="planner_genesis",
            story_id=story.id,
            input_json=inp.model_dump(),
            output_json=out.model_dump()
        )
        self.session.add(run)
        
        logger.info("Initiated new story: %s (ID: %d)", story.title, story.id)
        return story

    def plan_daily_for_story(self, story_id: int, target_date: str) -> None:
        """Runs the planner agent to create an outline for the next chapter."""
        story = self.session.get(Story, story_id)
        if not story:
            raise ValueError(f"Story {story_id} not found")

        # Determine next chapter number
        next_ch = 1
        if story.story_state:
            next_ch = story.story_state.current_chapter_no + 1

        state_dict = story.story_state.world_state_json if story.story_state else {}
        
        # Recent summaries
        stmt = select(ChapterSummary).where(ChapterSummary.story_id == story_id).order_by(desc(ChapterSummary.chapter_no)).limit(5)
        recent_summaries = [s.summary for s in self.session.scalars(stmt)]
        recent_summaries_dicts = [{"chapter_no": s.chapter_no, "summary": s.summary} for s in self.session.scalars(stmt)]

        # Open hooks
        stmt_hooks = select(StoryHook).where(StoryHook.story_id == story_id, StoryHook.status == HookStatus.open)
        open_hooks = [{"id": h.id, "text": h.hook_text} for h in self.session.scalars(stmt_hooks)]

        inp = PlannerInput(
            story_id=story_id,
            story_title=story.title,
            genre=story.genre,
            premise=story.premise,
            style_guide=story.style_guide,
            world_bible=story.world_bible_json or {},
            current_story_state=state_dict,
            recent_chapter_summaries=recent_summaries_dicts,
            open_hooks=open_hooks,
            planner_mode="next_chapter_outline",
            target_date=target_date,
            target_chapter_no=next_ch,
        )

        agent = PlannerAgent()
        out = agent.run(inp)

        # Save outline
        outline = StoryOutline(
            story_id=story_id,
            outline_date=target_date,
            chapter_no=out.chapter_no,
            theme=out.theme,
            summary=out.summary,
            outline_json=out.outline,
        )
        self.session.add(outline)
        self.session.flush()

        # Create task for writer
        if out.creates_write_task:
            task = StoryTask(
                story_id=story_id,
                outline_id=outline.id,
                task_type=TaskType.write,
                payload_json={"mode": "write"},
                scheduled_for=datetime.now()
            )
            self.session.add(task)

        # Log run
        run = AgentRun(
            agent_name="planner",
            story_id=story_id,
            input_json=inp.model_dump(),
            output_json=out.model_dump()
        )
        self.session.add(run)

    # ──────────────────────────────────────────────────────────
    # Task 2: Writer
    # ──────────────────────────────────────────────────────────
    def write_chapter(self, task_id: int) -> None:
        """Executes a writer task (write or rewrite)."""
        task = self.session.get(StoryTask, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        story = task.story
        outline = task.outline
        if not outline:
            raise ValueError("Write task missing outline")

        mode = "write"
        rewrite_notes = None
        if task.task_type == TaskType.rewrite:
            mode = "rewrite"
            rewrite_notes = task.payload_json.get("rewrite_notes", [])

        # Build Context
        state_dict = story.story_state.world_state_json if story.story_state else {}
        
        # Char states
        stmt_chars = select(CharacterState).where(CharacterState.story_id == story.id)
        char_states = []
        for cs in self.session.scalars(stmt_chars):
            char_states.append({
                "character_id": cs.character_id,
                "status": cs.status,
                "emotion": cs.emotion,
                "location": cs.location,
                "goal": cs.goal,
                "state_summary": cs.state_summary
            })

        # Rel snapshot
        rels = self.graph.get_relation_snapshot(story.id)

        # Open hooks
        stmt_hooks = select(StoryHook).where(StoryHook.story_id == story.id, StoryHook.status == HookStatus.open)
        open_hooks = [{"id": h.id, "text": h.hook_text} for h in self.session.scalars(stmt_hooks)]

        # Recent full chapters
        stmt_chaps = select(Chapter).where(Chapter.story_id == story.id).order_by(desc(Chapter.chapter_no)).limit(2)
        recent_chaps = [{"chapter_no": c.chapter_no, "content": c.content} for c in self.session.scalars(stmt_chaps)]

        # Older summaries
        stmt_sums = select(ChapterSummary).where(ChapterSummary.story_id == story.id).order_by(desc(ChapterSummary.chapter_no)).offset(2).limit(5)
        older_sums = [{"chapter_no": c.chapter_no, "summary": c.summary} for c in self.session.scalars(stmt_sums)]

        inp = WriterInput(
            story_id=story.id,
            outline_id=outline.id,
            chapter_no=outline.chapter_no,
            genre=story.genre,
            premise=story.premise,
            style_guide=story.style_guide,
            world_bible=story.world_bible_json or {},
            current_story_state=state_dict,
            relevant_character_states=char_states,
            relation_snapshot=rels,
            open_hooks=open_hooks,
            recent_full_chapters=recent_chaps,
            older_summaries=older_sums,
            outline=outline.outline_json or {},
            mode=mode,
            rewrite_notes=rewrite_notes
        )

        agent = WriterAgent()
        out = agent.run(inp)

        # Save Chapter
        if mode == "write":
            ch = Chapter(
                story_id=story.id,
                outline_id=outline.id,
                chapter_no=out.chapter_no,
                title=out.title,
                content=out.content,
                word_count=out.word_count,
            )
            self.session.add(ch)
            self.session.flush()
        else:
            ch = task.chapter
            if not ch:
                raise ValueError("Rewrite task missing chapter reference")
            ch.version_no += 1
            ch.title = out.title
            ch.content = out.content
            ch.word_count = out.word_count
            ch.status = ChapterStatus.draft
            self.session.flush()

        task.status = TaskStatus.done
        
        # Log run
        self.session.add(AgentRun(agent_name="writer", task_id=task.id, story_id=story.id, chapter_id=ch.id, input_json=inp.model_dump(), output_json=out.model_dump()))

        # Create review task
        review_task = StoryTask(
            story_id=story.id,
            chapter_id=ch.id,
            outline_id=outline.id,
            task_type=TaskType.review,
            scheduled_for=datetime.now()
        )
        self.session.add(review_task)

    # ──────────────────────────────────────────────────────────
    # Task 3: Reviewer
    # ──────────────────────────────────────────────────────────
    def review_chapter(self, task_id: int) -> None:
        """Executes a reviewer task."""
        task = self.session.get(StoryTask, task_id)
        if not task or not task.chapter:
            raise ValueError(f"Task {task_id} not found or missing chapter")

        story = task.story
        chapter = task.chapter

        stmt_sums = select(ChapterSummary).where(ChapterSummary.story_id == story.id).order_by(desc(ChapterSummary.chapter_no)).limit(5)
        recent_sums = [{"chapter_no": c.chapter_no, "summary": c.summary} for c in self.session.scalars(stmt_sums)]

        inp = ReviewerInput(
            story_id=story.id,
            chapter_id=chapter.id,
            chapter_no=chapter.chapter_no,
            chapter_title=chapter.title,
            chapter_content=chapter.content,
            outline=task.outline.outline_json if task.outline else None,
            current_story_state=story.story_state.world_state_json if story.story_state else {},
            recent_summaries=recent_sums,
            target_quality_threshold=settings.QUALITY_THRESHOLD
        )

        agent = ReviewerAgent()
        out = agent.run(inp)

        rev = ChapterReview(
            chapter_id=chapter.id,
            story_id=story.id,
            score=out.score,
            verdict=out.verdict,
            strengths_json=out.strengths,
            weaknesses_json=out.weaknesses,
            notes=out.notes,
            rewrite_notes_json=out.rewrite_notes
        )
        self.session.add(rev)

        chapter.review_score = out.score
        
        if out.should_rewrite:
            chapter.status = ChapterStatus.rewriting
            chapter.needs_rewrite = True
            
            rewrite_task = StoryTask(
                story_id=story.id,
                chapter_id=chapter.id,
                outline_id=task.outline_id,
                task_type=TaskType.rewrite,
                payload_json={"rewrite_notes": out.rewrite_notes},
                scheduled_for=datetime.now()
            )
            self.session.add(rewrite_task)
        else:
            chapter.status = ChapterStatus.reviewed
            chapter.needs_rewrite = False
            
            mem_task = StoryTask(
                story_id=story.id,
                chapter_id=chapter.id,
                task_type=TaskType.memory_update,
                scheduled_for=datetime.now()
            )
            self.session.add(mem_task)

        task.status = TaskStatus.done
        self.session.add(AgentRun(agent_name="reviewer", task_id=task.id, story_id=story.id, chapter_id=chapter.id, input_json=inp.model_dump(), output_json=out.model_dump()))

    # ──────────────────────────────────────────────────────────
    # Task 4: Memory Update
    # ──────────────────────────────────────────────────────────
    def update_memory(self, task_id: int) -> None:
        """Executes a memory update task and syncs relations to DB."""
        task = self.session.get(StoryTask, task_id)
        if not task or not task.chapter:
            raise ValueError(f"Task {task_id} not found or missing chapter")

        story = task.story
        chapter = task.chapter

        prev_state = story.story_state.world_state_json if story.story_state else {}
        
        stmt_chars = select(CharacterState).where(CharacterState.story_id == story.id)
        char_states = [{"character_id": cs.character_id, "status": cs.status, "emotion": cs.emotion} for cs in self.session.scalars(stmt_chars)]

        rels = self.graph.get_relation_snapshot(story.id)

        stmt_hooks = select(StoryHook).where(StoryHook.story_id == story.id, StoryHook.status == HookStatus.open)
        open_hooks = [{"id": h.id, "text": h.hook_text} for h in self.session.scalars(stmt_hooks)]

        inp = MemoryUpdateInput(
            story_id=story.id,
            chapter_id=chapter.id,
            chapter_no=chapter.chapter_no,
            chapter_title=chapter.title,
            chapter_content=chapter.content,
            previous_story_state=prev_state,
            previous_character_states=char_states,
            previous_open_hooks=open_hooks,
            previous_relation_snapshot=rels
        )

        agent = MemoryUpdateAgent()
        out = agent.run(inp)

        # 1. Save Summary
        summary = ChapterSummary(
            chapter_id=chapter.id,
            story_id=story.id,
            chapter_no=chapter.chapter_no,
            summary=out.chapter_summary,
            key_events_json=out.key_events,
            character_updates_json=out.character_state_updates
        )
        self.session.add(summary)

        # 2. Update Story State
        if not story.story_state:
            story.story_state = StoryState(story_id=story.id)
        story.story_state.current_chapter_no = chapter.chapter_no
        
        upd = out.story_state_update
        story.story_state.world_state_json = upd
        story.story_state.active_summary = out.chapter_summary
        story.story_state.current_arc = upd.get("current_arc", story.story_state.current_arc or "")
        story.story_state.current_goal = upd.get("current_goal", story.story_state.current_goal or "")
        
        # 3. Update events
        for ev in out.key_events:
            self.session.add(StoryEvent(
                story_id=story.id,
                chapter_id=chapter.id,
                chapter_no=chapter.chapter_no,
                event_type=ev.get("event_type", "event"),
                summary=ev.get("summary", ""),
                characters_involved_json=ev.get("characters", []),
                impact_level=ev.get("impact_level", "low")
            ))

        # Helper to find character by name
        def get_char_id(name: str) -> int | None:
            stmt = select(Character).where(Character.story_id == story.id, Character.name == name)
            char = self.session.scalar(stmt)
            return char.id if char else None

        # 4. Resolve Hooks
        for rh in out.resolved_hooks:
            txt = rh.get("hook_text")
            if txt:
                stmt_h = select(StoryHook).where(
                    StoryHook.story_id == story.id, 
                    StoryHook.status == HookStatus.open,
                    StoryHook.hook_text.contains(txt)
                )
                hook = self.session.scalar(stmt_h)
                if hook:
                    hook.status = HookStatus.resolved
                    hook.resolved_in_chapter = chapter.chapter_no

        # 5. New Hooks
        for nh in out.new_hooks:
            char_id = get_char_id(nh.get("related_character", ""))
            self.session.add(StoryHook(
                story_id=story.id,
                chapter_no_created=chapter.chapter_no,
                hook_text=nh.get("hook_text", ""),
                related_character_id=char_id
            ))

        # 6. Character States
        for cs_upd in out.character_state_updates:
            name = cs_upd.get("character")
            cid = get_char_id(name) if name else None
            if not cid:
                continue
            
            stmt_cs = select(CharacterState).where(CharacterState.character_id == cid).limit(1)
            cs = self.session.scalar(stmt_cs)
            if not cs:
                cs = CharacterState(story_id=story.id, character_id=cid, chapter_no=chapter.chapter_no)
                self.session.add(cs)
            else:
                cs.chapter_no = chapter.chapter_no
            
            cs.status = cs_upd.get("status") or cs.status
            cs.emotion = cs_upd.get("emotion") or cs.emotion
            cs.location = cs_upd.get("location") or cs.location
            cs.goal = cs_upd.get("goal") or cs.goal
            if "new_secrets" in cs_upd:
                current_secrets = cs.secrets_known_json or []
                cs.secrets_known_json = list(set(current_secrets + cs_upd["new_secrets"]))
            if "inventory_changes" in cs_upd:
                current_inv = cs.inventory_json or []
                cs.inventory_json = list(set(current_inv + cs_upd["inventory_changes"]))

        # 7. Sync Relations to Graph
        mapped_rels = []
        for rel in out.relation_updates:
            f_id = get_char_id(rel.get("source", ""))
            t_id = get_char_id(rel.get("target", ""))
            if f_id and t_id:
                mapped_rels.append({
                    "from_character_id": f_id,
                    "to_character_id": t_id,
                    "relation_type": rel.get("dimension", "RELATES_TO"),
                    "trust_score": 0.5 if rel.get("change") == "increase" else -0.5, # Placeholder logic
                    "note": rel.get("reason", "")
                })
        
        if mapped_rels:
            self.graph.sync_relation_updates(mapped_rels, chapter.chapter_no)
        # also update chapter json for record keeping if we want, but schema doesn't strict require it in summary
        summary.character_updates_json = out.relation_updates

        chapter.status = ChapterStatus.approved
        task.status = TaskStatus.done
        self.session.add(AgentRun(agent_name="memory_update", task_id=task.id, story_id=story.id, chapter_id=chapter.id, input_json=inp.model_dump(), output_json=out.model_dump()))
