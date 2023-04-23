import feedparser as fp
import dateparser
from datetime import datetime
from enum import Flag, auto
from http import HTTPStatus
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


class ResultType(Flag):
    NONE = 0
    PERMANENT_REDIRECT = auto()
    NOT_MODIFIED = auto()
    HTTP_ERROR = auto()
    ERROR = auto()
    AUTH_ERROR = auto()


def parse_feed(feed_url: str, etag=None, modified=None):
    # Make sure we aren't passing empty strings to fp.parse.
    if not etag:
        etag = None
    if not modified:
        modified = None

    results = dict()
    result_type = ResultType.NONE

    try:
        feed = fp.parse(feed_url, etag=etag, modified=modified)
    except Exception as e:
        results["error"] = f"{e.__class__.__name__}: {str(e)}"
        return ResultType.ERROR, results

    # we can not be modified and still have a HTTPStatus.FOUND or HTTPStatus.MOVED_PERMANENTLY
    # which will cause us to try to parse feed.feed anyway and fail.
    if (etag is not None or modified is not None) and not feed.feed:
        result_type |= ResultType.NOT_MODIFIED

    if "status" in feed:
        if feed.status == HTTPStatus.MOVED_PERMANENTLY:
            result_type |= ResultType.PERMANENT_REDIRECT
            results["new_url"] = feed.href
        elif feed.status == HTTPStatus.NOT_MODIFIED:
            result_type |= ResultType.NOT_MODIFIED
        elif feed.status == HTTPStatus.UNAUTHORIZED:
            results["status"] = HTTPStatus(feed.status)
            return ResultType.AUTH_ERROR, results
        elif feed.status not in (HTTPStatus.OK, HTTPStatus.FOUND):
            results["status"] = HTTPStatus(feed.status)
            return ResultType.HTTP_ERROR, results

    # If we detected no modification had some other status besides HTTPStatus.NOT_MODIFIED
    # we need to bail here.
    if ResultType.NOT_MODIFIED in result_type:
        return result_type, results

    results["etag"] = feed.get("etag", "")
    results["modified"] = feed.get("modified", "")

    f = feed.feed
    entries = feed.entries

    if any(x not in f for x in REQUIRED_FEED_ELEMENTS):
        results["error"] = f"Required elements missing from feed data: {', '.join(x for x in REQUIRED_FEED_ELEMENTS if x not in f)}"
        return ResultType.ERROR, results

    results["name"] = f.title
    results["description"] = BeautifulSoup(f.get("description", ""), features="lxml").get_text()
    results["home_page"] = f.link

    results["url"] = feed_url if feed_url.startswith("http") else None

    results["entries"] = entry_results = []
    for e in entries:
        e_map = dict()
        timestamp = None
        if "published_parsed" in e:
            timestamp = datetime(*e.published_parsed[:6])
        e_map["timestamp"] = timestamp
        e_map["title"] = e.title
        if "summary" in e:
            e_map["text"] = BeautifulSoup(e.summary, features="lxml").get_text()
        e_map["url"] = e.link

        if len(e.enclosures) > 0:
            e_map["enclosure_url"] = e.enclosures[0].href

        entry_results.append(e_map)
    return result_type, results
