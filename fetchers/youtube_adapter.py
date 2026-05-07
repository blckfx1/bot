import aiohttp
from datetime import datetime, timezone
from typing import List
from fetchers.base import BaseAdapter, RawPost


class YouTubeAdapter(BaseAdapter):
    BASE_URL = "https://www.googleapis.com/youtube/v3/"

    async def fetch(self, source, since: datetime):
        api_key = self.config["api_key"]
        channel_id = source.external_id
        # Get uploads playlist id
        async with aiohttp.ClientSession() as session:
            # Fetch channel details
            channel_url = f"{self.BASE_URL}channels?part=contentDetails&id={channel_id}&key={api_key}"
            async with session.get(channel_url) as resp:
                data = await resp.json()
                if "error" in data:
                    raise Exception(f"YouTube API error: {data}")
                uploads_playlist = data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

            # Fetch playlist items
            playlist_url = f"{self.BASE_URL}playlistItems?part=snippet&maxResults=50&playlistId={uploads_playlist}&key={api_key}"
            if since:
                since_str = since.isoformat("T") + "Z"
                playlist_url += f"&publishedAfter={since_str}"
            async with session.get(playlist_url) as resp:
                data = await resp.json()
                items = data.get("items", [])

        posts = []
        for item in items:
            snippet = item["snippet"]
            published_at = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00")).replace(tzinfo=None)
            if since and published_at <= since:
                continue
            media_urls = []
            if "thumbnails" in snippet:
                thumbs = snippet["thumbnails"]
                # take medium thumbnail
                if "medium" in thumbs:
                    media_urls.append(thumbs["medium"]["url"])
            posts.append(RawPost(
                external_id=snippet["resourceId"]["videoId"],
                title=snippet.get("title", ""),
                text=snippet.get("description", ""),
                media_urls=media_urls,
                publish_time=published_at,
            ))
        return posts