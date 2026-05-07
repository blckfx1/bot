import asyncio
from datetime import datetime
from typing import List
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from fetchers.base import BaseAdapter, RawPost


class TelegramAdapter(BaseAdapter):
    def __init__(self, api_config):
        super().__init__(api_config)
        self.client = None

    async def _get_client(self):
        if self.client is None:
            self.client = TelegramClient(
                "bot_session",
                self.config["api_id"],
                self.config["api_hash"],
                flood_sleep_threshold=60,
            )
            await self.client.start()
        return self.client

    async def fetch(self, source, since: datetime):
        client = await self._get_client()
        entity = await client.get_entity(source.external_id)  # external_id = channel username
        messages = await client.get_messages(entity, offset_date=since, limit=50)

        posts = []
        for msg in messages:
            if msg.date.replace(tzinfo=None) <= since:
                continue
            media_urls = []
            if msg.media and hasattr(msg.media, "photo"):
                # For simplicity: we don't download, just note that there is media
                media_urls.append("photo_present")
            posts.append(RawPost(
                external_id=str(msg.id),
                title=None,
                text=msg.text or msg.caption or "",
                media_urls=media_urls,
                publish_time=msg.date.replace(tzinfo=None),
            ))
        return posts