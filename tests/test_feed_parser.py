import pytest
from src import feed_parsing
from datetime import timedelta, datetime


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


def test_parser():
    r = feed_parsing.parse_feed(feed_data)

    assert r["name"] == "Sample Feed"
    assert r["description"] == "For documentation only"
    assert r["home_page"] == "http://example.org/"

    entry = r["entries"][0]
    assert entry["timestamp"] == datetime(2005, 11, 9, 0, 23, 47)
    assert entry["text"] == 'Watch out for nasty tricks'
    assert entry["url"] == 'http://example.org/entry/3'
    assert entry["enclosure_url"] == 'http://www.example.com/movie.mp4'


def test_parser_newer_than():
    r = feed_parsing.parse_feed(feed_data, newer_than=datetime(2005, 11, 9, 0, 23, 48))

    assert r["name"] == "Sample Feed"
    assert r["description"] == "For documentation only"
    assert r["home_page"] == "http://example.org/"

    assert not len(r["entries"])
