import feedparser as fp
from typing import Optional
from datetime import datetime


def parse_feed(feed_str: str, newer_than: Optional[datetime] = None):
    feed = fp.parse(feed_str)

    results = dict()

    results["name"] = feed.feed.title
    results["description"] = feed.feed.description

    return results