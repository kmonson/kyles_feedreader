import gevent
from gevent.event import Event
from . import feed_parsing
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class FeedManager:
    new_feed_item_event: Event
    name: str
    url: str
    home_page: str
    update_rate: int
    description: str = ""
    last_update: datetime = None
    etag: str = None
    last_modified: str = None
    unviewed_feeds: bool = False

    def worker(self):
        pass
