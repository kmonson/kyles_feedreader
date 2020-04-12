import feedparser as fp
import dateparser
from datetime import datetime
import warnings

from bs4 import BeautifulSoup

# BeautifulSoup complains about some possible inputs so I have to suppress it's whiny butt.
warnings.filterwarnings("ignore", category=UserWarning, module='bs4')


def handler(date_string):
    d = dateparser.parse(date_string)
    if d is not None:
        return d.timetuple()
    return None


# We add our own handler for all the weird stuff you see in feeds.
fp.datetimes.registerDateHandler(handler)


REQUIRED_FEED_ELEMENTS = ("title", "link")
REQUIRED_ENTRY_ELEMENTS = ()


def parse_feed(feed_url: str, etag=None, modified=None):
    # Make sure we aren't passing empty strings to fp.parse.
    if not etag:
        etag = None
    if not modified:
        modified = None

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

    results["url"] = feed_url if feed_url.startswith("http") else None

    results["entries"] = entry_results = []
    for e in entries:
        e_map = dict()
        timestamp = None
        if hasattr(e, "published_parsed"):
            timestamp = datetime(*e.published_parsed[:6])
        e_map["timestamp"] = timestamp
        e_map["title"] = e.title
        e_map["text"] = BeautifulSoup(e.summary, features="html.parser").get_text()
        e_map["url"] = e.link

        if len(e.enclosures) > 0:
            e_map["enclosure_url"] = e.enclosures[0].href

        entry_results.append(e_map)
    return results
