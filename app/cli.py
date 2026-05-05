"""Typer CLI entrypoint for the Story Agent MVP."""

import json
import typer
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.base import Base
from app.db.session import engine, get_session
from app.db.models import Story, Character, CharacterState, StoryState, StoryTask, TaskStatus, TaskType, Chapter, ChapterSummary
from app.graph.client import get_graph_client
from app.graph.graph_service import GraphService
from app.services.story_service import StoryService

app = typer.Typer(help="Story Agent CLI for managing automated fiction writing.")


@app.command("init-db")
def init_db():
    """Initialize MySQL schema and FalkorDB graph."""
    typer.echo("Creating MySQL schema...")
    Base.metadata.create_all(bind=engine)
    typer.echo("MySQL schema created.")
    
    typer.echo("Initializing FalkorDB schema...")
    graph = GraphService()
    graph.init_schema()
    typer.echo("FalkorDB initialized.")



@app.command("create-story")
def create_story(file_path: str = typer.Option(..., help="Path to JSON file containing story definition.")):
    """Create a new story from a JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        with get_session() as session:
            story = Story(
                code=data["code"],
                title=data["title"],
                genre=data["genre"],
                premise=data["premise"],
                style_guide=data.get("style_guide"),
                world_bible_json=data.get("world_bible", {})
            )
            session.add(story)
            session.flush()
            session.add(StoryState(story_id=story.id, current_chapter_no=0))
            
            graph = GraphService()
            graph.upsert_story(story.id, story.code, story.title, story.genre)
            session.commit()
            
        typer.secho(f"Story {data['code']} created.", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)


@app.command("new-story")
def new_story():
    """Trigger the Planner Genesis mode to conceive a new story from scratch."""
    typer.echo("Conceiving a new story idea from scratch...")
    with get_session() as session:
        svc = StoryService(session)
        story = svc.initiate_new_story()
        session.commit()
        typer.secho(f"New story created: {story.title} (ID: {story.id})", fg=typer.colors.GREEN)
        typer.secho(f"Premise: {story.premise}", italic=True)
    return story.id


@app.command("plan-daily")
def plan_daily(story_id: int = typer.Option(None, help="Specific story ID to plan for")):
    """Conceive a NEW story or plan the next chapter for an existing one."""
    target_date = date.today().isoformat()
    with get_session() as session:
        svc = StoryService(session)
        if story_id is None:
            typer.echo("No story ID provided. Conceiving a brand new story idea...")
            story = svc.initiate_new_story(target_date)
            session.commit()
            typer.secho(f"New story created: {story.title} (ID: {story.id})", fg=typer.colors.GREEN)
        else:
            story = session.get(Story, story_id)
            if not story:
                typer.secho(f"Story {story_id} not found.", fg=typer.colors.RED)
                return
            typer.echo(f"Planning next chapter for Story {story.id} ({story.title})...")
            svc.plan_daily_for_story(story.id, target_date)
            session.commit()
    typer.secho("Planning phase complete.", fg=typer.colors.GREEN)


def _run_tasks(task_type: TaskType, handler_method: str):
    with get_session() as session:
        tasks = session.query(StoryTask).filter(
            StoryTask.task_type == task_type,
            StoryTask.status == TaskStatus.pending
        ).all()
        
        if not tasks:
            typer.echo(f"No pending {task_type.value} tasks.")
            return

        svc = StoryService(session)
        handler = getattr(svc, handler_method)
        
        for t in tasks:
            typer.echo(f"Processing Task {t.id} ({task_type.value})...")
            t.status = TaskStatus.processing
            session.commit()
            
            try:
                handler(t.id)
                session.commit()
                typer.secho(f"Task {t.id} completed.", fg=typer.colors.GREEN)
            except Exception as e:
                session.rollback()
                typer.secho(f"Task {t.id} failed: {e}", fg=typer.colors.RED)
                # re-fetch and update error state
                t_fail = session.get(StoryTask, t.id)
                t_fail.status = TaskStatus.failed
                t_fail.error_message = str(e)
                session.commit()


@app.command("write-due")
def write_due():
    """Find due write tasks and run Writer agent."""
    _run_tasks(TaskType.write, "write_chapter")


@app.command("review-due")
def review_due():
    """Find due review tasks and run Reviewer agent."""
    _run_tasks(TaskType.review, "review_chapter")


@app.command("rewrite-due")
def rewrite_due():
    """Process rewrite tasks using Writer in rewrite mode."""
    _run_tasks(TaskType.rewrite, "write_chapter")


@app.command("update-memory")
def update_memory():
    """Process memory_update tasks and sync to DB + Graph."""
    _run_tasks(TaskType.memory_update, "update_memory")


@app.command("sync-graph")
def sync_graph():
    """Manual sync of relation changes to FalkorDB."""
    typer.echo("Syncing all current relations from chapter summaries to FalkorDB...")
    # Typically done incrementally in update_memory, this is a full rebuild stub
    typer.echo("Graph sync complete.")


@app.command("run-once")
def run_once(story_id: int = typer.Option(None)):
    """Always start a NEW story and run the full pipeline: genesis -> write -> review -> memory."""
    if story_id is None:
        typer.echo("Starting a fresh story session...")
        with get_session() as session:
            svc = StoryService(session)
            story = svc.initiate_new_story()
            session.commit()
            story_id = story.id
            typer.secho(f"Genesis Complete: {story.title}", fg=typer.colors.CYAN)

    write_due()
    review_due()
    rewrite_due()
    update_memory()
    sync_graph()
    typer.secho(f"Pipeline completed for Story ID: {story_id}", fg=typer.colors.GREEN)


@app.command("worker")
def worker():
    """Run Celery worker (blocking)."""
    import subprocess
    typer.echo("Starting Celery worker...")
    subprocess.run(["celery", "-A", "app.jobs.celery_app", "worker", "--loglevel=info"])


@app.command("scheduler-start")
def scheduler_start():
    """Run APScheduler recurring scheduler (blocking)."""
    from app.scheduler.scheduler import start_scheduler
    typer.echo("Starting Scheduler...")
    start_scheduler()


if __name__ == "__main__":
    app()
