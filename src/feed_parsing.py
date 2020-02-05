import feedparser as fp
from typing import Optional
from datetime import datetime
from bs4 import BeautifulSoup

REQUIRED_FEED_ELEMENTS = ("title", "link")
REQUIRED_ENTRY_ELEMENTS = ()


def parse_feed(feed_url: str, newer_than: Optional[datetime] = None, etag=None, modified=None):
    feed = fp.parse(feed_url, etag=etag, modified=modified)

    results = dict()

    if "status" in feed and feed.status != 200:
        return None

    results["etag"] = feed.get("etag")
    results["modified"] = feed.get("modified")

    f = feed.feed
    entries = feed.entries

    if any(x not in f for x in REQUIRED_FEED_ELEMENTS):
        # TODO: log something here.
        return None

    results["name"] = f.title
    results["description"] = BeautifulSoup(f.get("description", ""), features="html.parser").get_text()
    results["home_page"] = f.link

    results["url"] = feed_url

    results["entries"] = entry_results = []
    for e in entries:
        e_map = dict()
        e_map["timestamp"] = datetime(*e.published_parsed[:6])
        e_map["text"] = BeautifulSoup(e.summary, features="html.parser").get_text()
        e_map["url"] = e.link

        if len(e.enclosures) > 0:
            e_map["enclosure_url"] = e.enclosures[0].href

        entry_results.append(e_map)
    return results
