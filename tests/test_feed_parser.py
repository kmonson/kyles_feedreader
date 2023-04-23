from kyles_feedreader import feed_parsing
from datetime import datetime
import time

from feedparser.util import FeedParserDict
import feedparser
import pytest


feed_data = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
xml:base="http://example.org/"
xml:lang="en">
<title type="text">Sample Feed</title>
<subtitle type="html">
For documentation &lt;em&gt;only&lt;/em&gt;
</subtitle>
<link rel="alternate" href="/"/>
<link rel="self"
type="application/atom+xml"
href="http://www.example.org/atom10.xml"/>
<rights type="html">
&lt;p>Copyright 2005, Mark Pilgrim&lt;/p>&lt;
</rights>
<id>tag:feedparser.org,2005-11-09:/docs/examples/atom10.xml</id>
<generator
uri="http://example.org/generator/"
version="4.0">
Sample Toolkit
</generator>
<updated>2005-11-09T11:56:34Z</updated>
<entry>
<title>First entry title</title>
<link rel="alternate"
href="/entry/3"/>
<link rel="related"
type="text/html"
href="http://search.example.com/"/>
<link rel="via"
type="text/html"
href="http://toby.example.com/examples/atom10"/>
<link rel="enclosure"
type="video/mpeg4"
href="http://www.example.com/movie.mp4"
length="42301"/>
<id>tag:feedparser.org,2005-11-09:/docs/examples/atom10.xml:3</id>
<published>2005-11-09T00:23:47Z</published>
<updated>2005-11-09T11:56:34Z</updated>
<summary type="text/plain" mode="escaped">Watch out for nasty tricks</summary>
<content type="application/xhtml+xml" mode="xml"
xml:base="http://example.org/entry/3" xml:lang="en-US">
<div xmlns="http://www.w3.org/1999/xhtml">Watch out for
<span style="background: url(javascript:window.location='http://example.org/')">
nasty tricks</span></div>
</content>
</entry>
</feed>"""


def test_parser_string():
    t, r = feed_parsing.parse_feed(feed_data)

    assert r["name"] == "Sample Feed"
    assert r["description"] == "For documentation only"
    assert r["home_page"] == "http://example.org/"

    entry = r["entries"][0]
    assert entry["timestamp"] == datetime(2005, 11, 9, 0, 23, 47)
    assert entry["text"] == 'Watch out for nasty tricks'
    assert entry["url"] == 'http://example.org/entry/3'
    assert entry["enclosure_url"] == 'http://www.example.com/movie.mp4'


sheldon_feed_dict = FeedParserDict(
    {
        'bozo': False,
        'debug_message': 'The feed has not changed since you last checked, so the '
                         'server sent no data.  This is a feature, not a bug!',
        'entries': [],
        'etag': '"a740a10f5d95c83b973395fc75c97714"',
        'feed': {},
        'headers': {'age': '441',
                    'cache-control': 'public, must-revalidate, proxy-revalidate, '
                                     'max-age=900',
                    'connection': 'close',
                    'date': 'Fri, 24 Jul 2020 17:03:31 GMT',
                    'etag': '"a740a10f5d95c83b973395fc75c97714"',
                    'expires': 'Fri, 24 Jul 2020 17:00:01 GMT',
                    'server': 'AmazonS3',
                    'via': '1.1 42ef990e439ae115ff739f04e3945234.cloudfront.net '
                           '(CloudFront)',
                    'x-amz-cf-id': 'WWkREBUOkcmiydbH3WQNRpviU9VxTkG9RGf5pLkmsTL2EnzLn4l6tA==',
                    'x-amz-cf-pop': 'SEA19-C1',
                    'x-cache': 'Hit from cloudfront'},
        'href': 'http://cdn.sheldoncomics.com/rss.xml',
        'status': 304,
        'version': ''
    }
)

schlock_feed_dict = FeedParserDict(
    {
        'bozo': False,
        'encoding': 'UTF-8',
        'entries': [FeedParserDict({'author': 'Howard Tayler',
                     'author_detail': {'name': 'Howard Tayler'},
                     'authors': [{'name': 'Howard Tayler'}],
                     'guidislink': False,
                     'id': 'schlockmercenary.com,strip:7348',
                     'link': 'https://www.schlockmercenary.com/2020-07-24',
                     'links': [{'href': 'https://www.schlockmercenary.com/2020-07-24',
                                'rel': 'alternate',
                                'type': 'text/html'}],
                     'published': 'Fri, 24 Jul 2020 00:00:00 -0600',
                     'published_parsed': time.struct_time((2020, 7, 24, 0, 0, 0, 4, 206, 0)),
                     'summary': '<img '
                                'src="https://www.schlockmercenary.com/strip/7348/0/schlock20200724a.jpg?v=1595554203281" '
                                '/><br />\n'
                                '\t\t\n'
                                '\t\t\t\n'
                                '\t\t\t<img '
                                'src="https://www.schlockmercenary.com/strip/7348/1/schlock20200724b.jpg?v=1595554203281" '
                                '/><br />',
                     'summary_detail': {'base': 'https://www.schlockmercenary.com/rss/',
                                        'language': 'en-US',
                                        'type': 'text/html',
                                        'value': '<img '
                                                 'src="https://www.schlockmercenary.com/strip/7348/0/schlock20200724a.jpg?v=1595554203281" '
                                                 '/><br />\n'
                                                 '\t\t\n'
                                                 '\t\t\t\n'
                                                 '\t\t\t<img '
                                                 'src="https://www.schlockmercenary.com/strip/7348/1/schlock20200724b.jpg?v=1595554203281" '
                                                 '/><br />'},
                     'title': 'Schlock Mercenary: July 24, 2020',
                     'title_detail': {'base': 'https://www.schlockmercenary.com/rss/',
                                      'language': 'en-US',
                                      'type': 'text/plain',
                                      'value': 'Schlock Mercenary: July 24, 2020'}})],
        'feed': FeedParserDict({'author': 'webmaster@schlockmercenary.com',
                 'author_detail': {'email': 'webmaster@schlockmercenary.com'},
                 'authors': [{'email': 'webmaster@schlockmercenary.com'}],
                 'language': 'en-US',
                 'link': 'http://www.schlockmercenary.com/',
                 'links': [{'href': 'http://www.schlockmercenary.com/',
                            'rel': 'alternate',
                            'type': 'text/html'},
                           {'href': 'https://www.schlockmercenary.com/rss/all/',
                            'rel': 'self',
                            'type': 'application/rss+xml'}],
                 'published': 'Fri, 24 Jul 2020 10:31:29 -0600',
                 'published_parsed': time.struct_time((2020, 7, 24, 10, 31, 29, 4, 206, 0)),
                 'publisher': 'webmaster@schlockmercenary.com',
                 'publisher_detail': {'email': 'webmaster@schlockmercenary.com'},
                 'subtitle': 'Schlock Mercenary',
                 'subtitle_detail': {'base': 'https://www.schlockmercenary.com/rss/',
                                     'language': 'en-US',
                                     'type': 'text/html',
                                     'value': 'Schlock Mercenary'},
                 'tags': [{'label': None,
                           'scheme': None,
                           'term': 'schlock mercenary, epic space opera'}],
                 'title': 'Schlock Mercenary',
                 'title_detail': {'base': 'https://www.schlockmercenary.com/rss/',
                                  'language': 'en-US',
                                  'type': 'text/plain',
                                  'value': 'Schlock Mercenary'}}),
        'headers': {'access-control-allow-origin': '*',
                    'connection': 'close',
                    'content-encoding': 'gzip',
                    'content-language': 'en-US',
                    'content-length': '2845',
                    'content-type': 'text/xml;charset=UTF-8',
                    'date': 'Fri, 24 Jul 2020 17:03:31 GMT',
                    'server': 'Apache',
                    'set-cookie': 'JSESSIONID=98BF303BF444BE0860412059E0D28347; '
                                  'Path=/; Secure; HttpOnly',
                    'vary': 'Accept-Encoding'},
        'href': 'https://www.schlockmercenary.com/rss/',
        'namespaces': {'': 'http://www.w3.org/2005/Atom',
                       'dc': 'http://purl.org/dc/elements/1.1/'},
        'status': 200,
        'version': 'rss20'
    }
)

feed_dict = {
    ('https://www.schlockmercenary.com/rss/', None, None): schlock_feed_dict,
    ('http://cdn.sheldoncomics.com/rss.xml', '"a740a10f5d95c83b973395fc75c97714"', None): sheldon_feed_dict
}


def parse_mock(feed_url: str, etag=None, modified=None):
    return feed_dict[feed_url, etag, modified]

@pytest.fixture
def mock_fp_parse(monkeypatch):
    def parse_mock(feed_url: str, etag=None, modified=None):
        return feed_dict[feed_url, etag, modified]

    monkeypatch.setattr(feedparser, "parse", parse_mock)


def test_parser(mock_fp_parse):
    t, r = feed_parsing.parse_feed('https://www.schlockmercenary.com/rss/', None, None)

    assert r["name"] == "Schlock Mercenary"
    assert r["description"] == "Schlock Mercenary"
    assert r["home_page"] == "http://www.schlockmercenary.com/"

    entry = r["entries"][0]
    assert entry["timestamp"] == datetime(2020, 7, 24, 0, 0, 0)
    assert entry["title"] == "Schlock Mercenary: July 24, 2020"
    assert entry["url"] == "https://www.schlockmercenary.com/2020-07-24"


def test_not_modified(mock_fp_parse):
    t, r = feed_parsing.parse_feed('http://cdn.sheldoncomics.com/rss.xml', '"a740a10f5d95c83b973395fc75c97714"')
    assert t == feed_parsing.ResultType.NOT_MODIFIED
    assert not r
