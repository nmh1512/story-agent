"""Daily scheduler using APScheduler to trigger the Planning phase."""

import logging
import time
from datetime import date
from apscheduler.schedulers.background import BackgroundScheduler

from app.db.session import get_session
from app.db.models import Story, StoryStatus
from app.services.story_service import StoryService
from app.core.config import settings

logger = logging.getLogger(__name__)


def plan_all_active_stories() -> None:
    """Finds all active stories and runs the Planner for them."""
    logger.info("Scheduler Triggered: Planning daily outlines for active stories.")
    target_date = date.today().isoformat()
    
    with get_session() as session:
        active_stories = session.query(Story).filter(Story.status == StoryStatus.active).all()
        svc = StoryService(session)
        for story in active_stories:
            logger.info("Planning for story_id=%d", story.id)
            try:
                svc.plan_daily_for_story(story.id, target_date)
            except Exception as e:
                logger.error("Failed to plan story_id=%d: %s", story.id, e)


def start_scheduler() -> None:
    """Initialize and run the APScheduler."""
    scheduler = BackgroundScheduler()
    
    # Schedule the planning task daily at the configured time
    scheduler.add_job(
        plan_all_active_stories, 
        'cron', 
        hour=settings.DAILY_PLAN_HOUR, 
        minute=settings.DAILY_PLAN_MINUTE
    )
    
    scheduler.start()
    logger.info("Scheduler started. Daily plan set for %02d:%02d UTC.", settings.DAILY_PLAN_HOUR, settings.DAILY_PLAN_MINUTE)
    
    try:
        # Keep the main thread alive while background scheduler works
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler shutdown.")
