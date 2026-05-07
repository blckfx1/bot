import asyncio
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.handlers import (
    start_command,
    subscribe_command,
    unsubscribe_command,
    list_command,
    help_command,
)
from db.session import init_db, async_session_maker
from scheduler.jobs import setup_scheduler_jobs
from classifier.engine import Classifier
from fetchers.telegram_adapter import TelegramAdapter
from fetchers.vk_adapter import VKAdapter
from fetchers.youtube_adapter import YouTubeAdapter

load_dotenv()

# Configure logging
from logging.config import dictConfig

LOGGING_CONFIG = {
    "version": 1,
    "formatters": {
        "json": {
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        }
    },
    "handlers": {
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/app.log",
            "maxBytes": 10485760,
            "backupCount": 5,
            "formatter": "json",
        },
        "console": {"class": "logging.StreamHandler", "formatter": "json"},
    },
    "root": {"level": "INFO", "handlers": ["file", "console"]},
}
dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# Global references for scheduler and adapters (used in jobs)
scheduler = None
adapters = {}
classifier = None


def setup_adapters():
    """Initialize adapters with API keys from env."""
    global adapters
    adapters = {
        "telegram": TelegramAdapter(
            {
                "api_id": int(os.getenv("TELEGRAM_API_ID")),
                "api_hash": os.getenv("TELEGRAM_API_HASH"),
            }
        ),
        "vk": VKAdapter({"access_token": os.getenv("VK_API_KEY")}),
        "youtube": YouTubeAdapter({"api_key": os.getenv("YT_API_KEY")}),
    }


async def main() -> None:
    global scheduler, classifier
    # Initialize DB
    await init_db()

    # Setup classifier
    classifier = Classifier(config_path="config/themes.yml")

    # Setup adapters
    setup_adapters()

    # Setup scheduler
    scheduler = AsyncIOScheduler()
    setup_scheduler_jobs(scheduler, async_session_maker, adapters, classifier)
    scheduler.start()

    # Setup bot
    bot_token = os.getenv("BOT_TOKEN")
    application = Application.builder().token(bot_token).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("help", help_command))

    logger.info("Bot started polling...")
    await application.run_polling()


if __name__ == "__main__":
    asyncio.run(main())