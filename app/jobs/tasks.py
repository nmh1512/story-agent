"""Celery task definitions."""

import logging
import traceback
from datetime import date

from app.jobs.celery_app import celery_app
from app.db.session import get_session
from app.db.models import StoryTask, TaskStatus, TaskType
from app.services.story_service import StoryService

logger = logging.getLogger(__name__)


def _mark_task_failed(task_id: int, error_msg: str) -> None:
    with get_session() as session:
        task = session.get(StoryTask, task_id)
        if task:
            task.retry_count += 1
            task.error_message = error_msg
            if task.retry_count >= 3:
                task.status = TaskStatus.failed
            else:
                task.status = TaskStatus.pending


@celery_app.task(bind=True, max_retries=3)
def execute_task(self, task_id: int) -> None:
    """Executes a queued StoryTask via the StoryService."""
    logger.info("Executing Task ID=%d", task_id)

    with get_session() as session:
        task = session.get(StoryTask, task_id)
        if not task:
            logger.error("Task %d not found", task_id)
            return
        
        if task.status not in (TaskStatus.pending, TaskStatus.failed):
            logger.info("Task %d is not pending (status=%s)", task_id, task.status)
            return

        task.status = TaskStatus.processing
        task_type = task.task_type
        # Commit to lock state
        session.commit()

        service = StoryService(session)
        
        try:
            if task_type == TaskType.plan:
                # Plan is triggered by a task row here for uniformity, or by CLI directly
                svc_story_id = task.story_id
                target_date = date.today().isoformat()
                service.plan_daily_for_story(svc_story_id, target_date)
            elif task_type in (TaskType.write, TaskType.rewrite):
                service.write_chapter(task_id)
            elif task_type == TaskType.review:
                service.review_chapter(task_id)
            elif task_type == TaskType.memory_update:
                service.update_memory(task_id)
            
            # success commit done by context manager yield
        except Exception as exc:
            logger.exception("Task %d failed", task_id)
            session.rollback()
            _mark_task_failed(task_id, str(exc) + "\n" + traceback.format_exc())
            # optional: self.retry(exc=exc, countdown=60 * self.request.retries)
