import logging
from telegram import Bot
import os
from db.models import Post, User

logger = logging.getLogger(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)


async def send_new_post_notifications(post: Post, themes: list, subscribers: list):
    """Send notification to each subscriber."""
    source = post.source
    title = post.title or "No title"
    text_preview = (post.text or "")[:300]
    # Build platform-specific link
    if source.platform == "telegram":
        link = f"https://t.me/{source.external_id}/{post.external_id}"
    elif source.platform == "vk":
        link = f"https://vk.com/wall{source.external_id}_{post.external_id}"
    elif source.platform == "youtube":
        link = f"https://youtu.be/{post.external_id}"
    else:
        link = "#"

    themes_str = ", ".join(themes) if themes else "uncategorized"
    message = (
        f"*{title}*\n\n"
        f"{text_preview}\n\n"
        f"[Read more]({link})\n"
        f"Themes: {themes_str}"
    )
    # Escape markdown characters (simplified)
    # For production, use proper escape for MarkdownV2
    for user in subscribers:
        try:
            await bot.send_message(chat_id=user.tg_id, text=message, parse_mode="Markdown", disable_web_page_preview=False)
        except Exception as e:
            logger.error(f"Failed to notify user {user.tg_id}: {e}")