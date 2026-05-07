import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import async_sessionmaker
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from db import crud
from db.models import Source
from fetchers.base import BaseAdapter
from classifier.engine import Classifier
from bot.notifier import send_new_post_notifications  # will implement

logger = logging.getLogger(__name__)


async def fetch_and_process_source(source: Source, adapter: BaseAdapter, classifier: Classifier, session_maker):
    """Fetch posts for a single source, classify, store, and notify."""
    try:
        since = source.last_fetched
        posts_raw = await adapter.fetch(source, since)
        if not posts_raw:
            # Update last_fetched to now if no new posts? Better to keep old last_fetched or set to now?
            # If no posts, set last_fetched to now to avoid re-fetching same empty period.
            await crud.update_source_last_fetched(session_maker, source.id, datetime.utcnow())
            return
        newest_time = since
        async with session_maker() as session:
            for raw in posts_raw:
                post_data = {
                    "source_id": source.id,
                    "external_id": raw.external_id,
                    "title": raw.title,
                    "text": raw.text,
                    "media_urls": raw.media_urls,
                    "publish_time": raw.publish_time,
                }
                post = await crud.insert_post(session, post_data)
                if post:
                    # Classify
                    themes = classifier.classify(post.text, post.title, source)
                    await crud.add_post_themes(session, post.id, themes)
                    # Notify subscribers
                    subscribers = await crud.get_subscribed_users_for_source(session, source.id)
                    if subscribers:
                        await send_new_post_notifications(post, themes, subscribers)
                if raw.publish_time > newest_time:
                    newest_time = raw.publish_time
            # Update last_fetched to newest post time
            await crud.update_source_last_fetched(session, source.id, newest_time)
    except Exception as e:
        logger.exception(f"Error fetching source {source.id}: {e}")
        # Optionally implement backoff by increasing update_interval temporarily
        # For simplicity, just log


async def scan_due_sources(session_maker, adapters, classifier):
    """Called by scheduler every minute."""
    async with session_maker() as session:
        due_sources = await crud.get_sources_due_for_fetch(session, datetime.utcnow())
    for src in due_sources:
        adapter = adapters.get(src.platform)
        if not adapter:
            logger.warning(f"No adapter for platform {src.platform}")
            continue
        asyncio.create_task(fetch_and_process_source(src, adapter, classifier, session_maker))


def setup_scheduler_jobs(scheduler: AsyncIOScheduler, session_maker, adapters, classifier):
    scheduler.add_job(
        scan_due_sources,
        "interval",
        minutes=1,
        args=[session_maker, adapters, classifier],
        id="scan_sources",
        replace_existing=True,
    )