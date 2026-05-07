import aiohttp
from datetime import datetime
from typing import List
import asyncio
from fetchers.base import BaseAdapter, RawPost


class VKAdapter(BaseAdapter):
    BASE_URL = "https://api.vk.com/method/"

    async def fetch(self, source, since: datetime):
        access_token = self.config["access_token"]
        owner_id = source.external_id  # e.g., -12345 for group
        version = "5.131"

        since_ts = int(since.timestamp())
        params = {
            "access_token": access_token,
            "v": version,
            "owner_id": owner_id,
            "count": 50,
            "start_time": since_ts,
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(self.BASE_URL + "wall.get", params=params) as resp:
                data = await resp.json()
                if "error" in data:
                    # Rate limit handling
                    if data["error"]["error_code"] == 6:
                        await asyncio.sleep(1)
                        # Retry once
                        async with session.get(self.BASE_URL + "wall.get", params=params) as retry_resp:
                            data = await retry_resp.json()
                    else:
                        raise Exception(f"VK API error: {data}")
                items = data.get("response", {}).get("items", [])
        posts = []
        for item in items:
            media_urls = []
            if "attachments" in item:
                for att in item["attachments"]:
                    if att["type"] == "photo":
                        # get largest photo URL
                        sizes = att["photo"]["sizes"]
                        if sizes:
                            media_urls.append(sizes[-1]["url"])
            posts.append(RawPost(
                external_id=str(item["id"]),
                title=None,
                text=item.get("text", ""),
                media_urls=media_urls,
                publish_time=datetime.fromtimestamp(item["date"]),
            ))
        return posts