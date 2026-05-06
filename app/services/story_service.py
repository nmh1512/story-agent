import logging
import json
from datetime import datetime, date
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.db.models import (
    Story, StoryStatus, StoryOutline, OutlineStatus, 
    StoryTask, TaskType, AgentRun, ChapterSummary, StoryHook, HookStatus,
    Character, CharacterState, StoryState
)
from app.agents.planner import PlannerAgent
from app.agents.writer import WriterAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.memory import MemoryUpdateAgent
from app.schemas.planner import PlannerInput
from app.schemas.writer import WriterInput
from app.schemas.reviewer import ReviewerInput
from app.schemas.memory import MemoryUpdateInput
from app.graph.graph_service import GraphService

logger = logging.getLogger(__name__)

class StoryService:
    def __init__(self, session: Session):
        self.session = session
        self.graph = GraphService()

    # ──────────────────────────────────────────────────────────
    # Task 1: Planner
    # ──────────────────────────────────────────────────────────
    def initiate_new_story(self, target_date: str = None) -> Story:
        """Starts a new story using Hierarchical Planning (3 Acts -> Roadmaps -> Detailed)."""
        if not target_date:
            target_date = date.today().isoformat()
            
        agent = PlannerAgent()
        
        # --- PHASE 1: STORY GENESIS (Metadata + 3 Acts) ---
        inp_gen = PlannerInput(
            planner_mode="story_genesis",
            target_date=target_date,
            target_chapter_no=1
        )
        out_genesis = agent.run(inp_gen)
        
        # Create story
        story = Story(
            code=f"GEN-{datetime.now().strftime('%Y%m%d%H%M')}",
            title=out_genesis.title or "Chuyện chưa đặt tên",
            genre=out_genesis.genre or "Chưa rõ",
            premise=out_genesis.premise or "Đang cập nhật",
            backstory=out_genesis.backstory,
            arc_overview=json.dumps([act.model_dump() for act in out_genesis.act_summaries] if out_genesis.act_summaries else []), # Save the 3 Acts
            world_bible_json=out_genesis.world_bible or {}
        )
        self.session.add(story)
        self.session.flush()
        
        # Create characters and states
        if out_genesis.initial_characters:
            for c_data in out_genesis.initial_characters:
                char = Character(
                    story_id=story.id,
                    code=c_data.get("code", "CHAR"),
                    name=c_data.get("name", "Vô danh"),
                    role=c_data.get("role", "None"),
                    description=c_data.get("description", "")
                )
                self.session.add(char)
                self.session.flush()
                cs = CharacterState(story_id=story.id, character_id=char.id, chapter_no=0, status="active")
                self.session.add(cs)
                self.graph.upsert_character(char.id, story.id, char.code, char.name, char.role)
        
        state = StoryState(story_id=story.id, current_chapter_no=0, world_state_json={})
        self.session.add(state)
        self.graph.upsert_story(story.id, story.code, story.title, story.genre)

        # --- PHASE 2: INCREMENTAL ROADMAP GENERATION (Iterative 20 Chapters) ---
        act_summaries = out_genesis.act_summaries or []
        roadmap_full_text = ""
        total_chapters = 20
        ch1_outline_id = None
        
        for ch_no in range(1, total_chapters + 1):
            # Determine Act based on chapter number
            if ch_no <= 7: 
                act_no, act_plan = 1, act_summaries[0] if len(act_summaries) > 0 else None
            elif ch_no <= 14: 
                act_no, act_plan = 2, act_summaries[1] if len(act_summaries) > 1 else None
            else: 
                act_no, act_plan = 3, act_summaries[2] if len(act_summaries) > 2 else None
            act_sum = act_plan.summary if act_plan else "Tiếp tục diễn biến"
            
            pacing_instruction = "Phát triển cốt truyện một cách logic và mới mẻ."
            if ch_no == total_chapters:
                pacing_instruction = "Đây là CHƯƠNG CUỐI CÙNG. Bắt buộc phải giải quyết toàn bộ mâu thuẫn chính và kết thúc câu chuyện trọn vẹn."
            elif ch_no == total_chapters - 1:
                pacing_instruction = "Đây là CHƯƠNG CAO TRÀO (Climax). Đẩy mọi xung đột lên mức cao nhất, chuẩn bị cho kết thúc."
            elif ch_no == 1:
                pacing_instruction = "Đây là CHƯƠNG MỞ ĐẦU. Giới thiệu nhân vật, bối cảnh và tạo ra một sự kiện gây chú ý (Hook)."
            
            logger.info("Generating Roadmap for Chapter %d (Act %d)", ch_no, act_no)
            
            inp_road = PlannerInput(
                story_id=story.id,
                story_title=story.title,
                genre=story.genre,
                planner_mode="single_chapter_roadmap",
                target_date=target_date,
                target_chapter_no=ch_no,
                current_story_state={
                    "target_act_no": act_no,
                    "target_act_summary": act_sum,
                    "pacing_instruction": pacing_instruction,
                    "previous_chapters_roadmap": roadmap_full_text or "Chưa có chương nào. Bắt đầu câu chuyện."
                }
            )
            out_road = agent.run(inp_road)
            
            outline = StoryOutline(
                story_id=story.id,
                outline_date=target_date,
                chapter_no=ch_no,
                theme=out_road.theme,
                summary=out_road.summary,
                outline_json={
                    "roadmap_goal": out_road.summary, 
                    "act_no": act_no, 
                    "analysis": out_road.recent_events_analysis, 
                    "decision": out_road.new_direction_decision
                },
                status=OutlineStatus.pending
            )
            self.session.add(outline)
            if ch_no == 1:
                self.session.flush()
                ch1_outline_id = outline.id
            
            # Append this chapter to the history for the NEXT iteration
            roadmap_full_text += f"Ch {ch_no}: {out_road.theme} ({out_road.summary})\n"

        # --- PHASE 3: QUEUE FIRST PLAN TASK ---
        task = StoryTask(
            story_id=story.id,
            outline_id=ch1_outline_id,
            task_type=TaskType.plan,
            payload_json={"chapter_no": 1},
            scheduled_for=datetime.now()
        )
        self.session.add(task)
        
        logger.info("Hierarchical Planning complete for story %d. Total Chapters: %d", story.id, total_chapters)
        return story

    def plan_chapter(self, task_id: int) -> None:
        """Standard task handler for Just-In-Time detailed planning."""
        task = self.session.get(StoryTask, task_id)
        story_id = task.story_id
        target_date = date.today().isoformat()
        
        story = self.session.get(Story, story_id)
        next_ch = 1
        if story.story_state:
            next_ch = story.story_state.current_chapter_no + 1

        # 1. Get Roadmap Goal
        stmt_outline = select(StoryOutline).where(StoryOutline.story_id == story_id, StoryOutline.chapter_no == next_ch)
        outline = self.session.execute(stmt_outline).scalar_one_or_none()
        roadmap_goal = outline.outline_json.get("roadmap_goal", outline.summary) if outline and outline.outline_json else "Tiếp tục diễn biến"

        # 2. Context
        state_dict = story.story_state.world_state_json if story.story_state else {}
        state_dict["roadmap_summary"] = roadmap_goal
        
        stmt_sums = select(ChapterSummary).where(ChapterSummary.story_id == story_id).order_by(desc(ChapterSummary.chapter_no)).limit(5)
        recent_summaries = [{"chapter_no": s.chapter_no, "summary": s.summary} for s in self.session.scalars(stmt_sums).all()]

        stmt_hooks = select(StoryHook).where(StoryHook.story_id == story_id, StoryHook.status == HookStatus.open)
        open_hooks = [{"id": h.id, "text": h.hook_text} for h in self.session.scalars(stmt_hooks).all()]

        inp = PlannerInput(
            story_id=story_id,
            story_title=story.title,
            genre=story.genre,
            premise=story.premise,
            world_bible=story.world_bible_json or {},
            current_story_state=state_dict,
            recent_chapter_summaries=recent_summaries,
            open_hooks=open_hooks,
            planner_mode="chapter_planning",
            target_date=target_date,
            target_chapter_no=next_ch,
        )

        agent = PlannerAgent()
        out = agent.run(inp)

        # 3. Update Outline with Detailed JSON
        if not outline:
            outline = StoryOutline(story_id=story_id, chapter_no=next_ch, outline_date=target_date)
            self.session.add(outline)
            
        outline.theme = out.theme
        outline.summary = out.summary
        outline.outline_json = out.outline
        self.session.flush()

        # 4. Queue Writer
        task = StoryTask(story_id=story_id, outline_id=outline.id, task_type=TaskType.write, scheduled_for=datetime.now())
        self.session.add(task)
        logger.info("Detailed Planning done for Ch %d of story %d", next_ch, story_id)

    # ──────────────────────────────────────────────────────────
    # Task 2: Writer
    # ──────────────────────────────────────────────────────────
    def write_chapter(self, task_id: int) -> None:
        """Executes a writer task (write or rewrite)."""
        task = self.session.get(StoryTask, task_id)
        story_id = task.story_id
        outline_id = task.outline_id
        
        story = self.session.get(Story, story_id)
        outline = self.session.get(StoryOutline, outline_id)
        
        # 1. Character States
        stmt_chars = select(Character).where(Character.story_id == story_id)
        chars = self.session.scalars(stmt_chars).all()
        char_states = {}
        for c in chars:
            stmt_cs = select(CharacterState).where(CharacterState.character_id == c.id).order_by(desc(CharacterState.chapter_no)).limit(1)
            cs = self.session.scalar(stmt_cs)
            char_states[c.code] = {
                "name": c.name,
                "current_status": cs.status if cs else "active",
                "notes": cs.state_summary if cs else ""
            }

        # 2. Recent Summaries
        stmt_sums = select(ChapterSummary).where(ChapterSummary.story_id == story_id).order_by(desc(ChapterSummary.chapter_no)).limit(3)
        recent_summaries = [{"chapter_no": s.chapter_no, "summary": s.summary} for s in self.session.scalars(stmt_sums).all()]

        # 3. Story Graph Relations
        relations = self.graph.get_relation_snapshot(story_id)

        inp = WriterInput(
            story_title=story.title,
            genre=story.genre,
            premise=story.premise,
            chapter_no=outline.chapter_no,
            chapter_theme=outline.theme,
            chapter_summary=outline.summary,
            detailed_outline=outline.outline_json,
            world_bible=story.world_bible_json or {},
            character_states=char_states,
            recent_summaries=recent_summaries,
            relations=relations
        )

        agent = WriterAgent()
        out = agent.run(inp)

        from app.db.models import Chapter
        chapter = Chapter(story_id=story_id, chapter_no=outline.chapter_no, title=outline.theme, content=out.content, word_count=len(out.content.split()))
        self.session.add(chapter)
        self.session.flush()

        outline.status = OutlineStatus.used
        review_task = StoryTask(story_id=story_id, chapter_id=chapter.id, task_type=TaskType.review, scheduled_for=datetime.now())
        self.session.add(review_task)
        logger.info("Wrote Chapter %d for story %d", outline.chapter_no, story_id)

    # ──────────────────────────────────────────────────────────
    # Task 3: Reviewer
    # ──────────────────────────────────────────────────────────
    def review_chapter(self, task_id: int) -> None:
        """Reviews the recently written chapter."""
        task = self.session.get(StoryTask, task_id)
        story_id = task.story_id
        chapter_id = task.chapter_id
        
        from app.db.models import Chapter
        chapter = self.session.get(Chapter, chapter_id)
        story = self.session.get(Story, story_id)
        
        stmt_outline = select(StoryOutline).where(StoryOutline.story_id == story_id, StoryOutline.chapter_no == chapter.chapter_no)
        outline = self.session.scalar(stmt_outline)

        inp = ReviewerInput(story_title=story.title, chapter_no=chapter.chapter_no, content=chapter.content, outline_summary=outline.summary if outline else "")
        agent = ReviewerAgent()
        out = agent.run(inp)

        from app.db.models import ChapterReview
        review = ChapterReview(chapter_id=chapter_id, score=out.score, critique=out.critique, passed=out.passed)
        self.session.add(review)

        if not out.passed:
            rewrite_task = StoryTask(story_id=story_id, chapter_id=chapter_id, task_type=TaskType.rewrite, payload_json={"critique": out.critique}, scheduled_for=datetime.now())
            self.session.add(rewrite_task)
        else:
            mem_task = StoryTask(story_id=story_id, chapter_id=chapter_id, task_type=TaskType.memory_update, scheduled_for=datetime.now())
            self.session.add(mem_task)

    # ──────────────────────────────────────────────────────────
    # Task 4: Memory Update
    # ──────────────────────────────────────────────────────────
    def update_memory(self, task_id: int) -> None:
        """Extracts facts and updates graph/character states."""
        task = self.session.get(StoryTask, task_id)
        story_id = task.story_id
        chapter_id = task.chapter_id
        
        from app.db.models import Chapter
        chapter = self.session.get(Chapter, chapter_id)
        story = self.session.get(Story, story_id)
        
        prev_story_state = story.story_state.world_state_json if story.story_state else {}
        stmt_chars = select(Character).where(Character.story_id == story_id)
        chars = self.session.scalars(stmt_chars).all()
        prev_char_states = []
        for c in chars:
            stmt_cs = select(CharacterState).where(CharacterState.character_id == c.id).order_by(desc(CharacterState.chapter_no)).limit(1)
            cs = self.session.scalar(stmt_cs)
            if cs: prev_char_states.append({"character": c.name, "status": cs.status, "notes": cs.state_summary})

        relations = self.graph.get_relation_snapshot(story_id)
        inp = MemoryUpdateInput(story_id=story_id, chapter_id=chapter_id, chapter_no=chapter.chapter_no, 
                                chapter_title=chapter.title or "Untitled", chapter_content=chapter.content, 
                                previous_story_state=prev_story_state, previous_character_states=prev_char_states, 
                                previous_relation_snapshot=relations)

        agent = MemoryUpdateAgent()
        out = agent.run(inp)

        summary = ChapterSummary(story_id=story_id, chapter_id=chapter_id, chapter_no=chapter.chapter_no, summary=out.chapter_summary)
        self.session.add(summary)

        for rel_upd in out.relation_updates:
            s_char = next((c for c in chars if c.name == rel_upd["source"]), None)
            t_char = next((c for c in chars if c.name == rel_upd["target"]), None)
            if s_char and t_char:
                self.graph.upsert_relation(from_character_id=s_char.id, to_character_id=t_char.id, 
                                         relation_type=rel_upd.get("dimension", "RELATES_TO"), 
                                         note=rel_upd.get("reason", ""), updated_in_chapter=chapter.chapter_no)

        for upd in out.character_state_updates:
            char = next((c for c in chars if c.name == upd["character"]), None)
            if char:
                ns = CharacterState(story_id=story_id, character_id=char.id, chapter_no=chapter.chapter_no, 
                                   status=upd.get("status", "active"), 
                                   state_summary=f"Emotion: {upd.get('emotion')}. Goal: {upd.get('goal')}")
                self.session.add(ns)

        for hook in out.new_hooks:
            self.session.add(StoryHook(story_id=story_id, chapter_id=chapter_id, hook_text=hook["hook_text"], status=HookStatus.open))

        if not story.story_state:
            story.story_state = StoryState(story_id=story_id, current_chapter_no=chapter.chapter_no, world_state_json=out.story_state_update)
        else:
            story.story_state.current_chapter_no = chapter.chapter_no
            story.story_state.world_state_json.update(out.story_state_update)
        
        logger.info("Memory updated for Story %d, Ch %d", story_id, chapter.chapter_no)
