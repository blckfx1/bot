from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, NamedTuple, Optional

class RawPost(NamedTuple):
    external_id: str
    title: Optional[str]
    text: Optional[str]
    media_urls: List[str]
    publish_time: datetime


class BaseAdapter(ABC):
    def __init__(self, api_config: dict):
        self.config = api_config

    @abstractmethod
    async def fetch(self, source, since: datetime) -> List[RawPost]:
        pass