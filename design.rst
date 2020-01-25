Design
======

Data models
+++++++++++

Feed
----
In database
    - Group id
    - URL
    - Home page
    - Name
    - last update
    - update rate
    - etag
    - last modified
    - id


Feed items
----------
In database
    - id
    - id of feed
    - enclosure URL
    - enclosure URI
    - read
    - viewed
    - text
    - URL

Group
-----
In database
    - id
    - name

Feed Reader settings
--------------------
Config file

 Key values pairs for different settings
 (Not to be store in DB)
 Examples
 - DB setting
 - enclosure download directory

Database Interface
++++++++++++++++++
peewee does not support gevent in SQLite.
We will need to roll our own or not worry about it.

`initialize_db(provider='sqlite', **kwargs)`

add_feed(name, url, home_page, update_rate=1 hour, group=None)

add_group(name)

update_feed(feed_id,
          group=None
          name=None
          url=None
          home_page=None
          last_update=None
          etag=None
          last_modified=None
          update_rate=None)

get_feeds()

delete_feed(feed_id)

get_feed_items(unread, group=None, feed=None)

add_feed_items(feed_id, items)

update_feed_item(item_id, read: bool, viewed: bool)

delete_feed_items(item_id and/or feed_id and/or read, and/or leave_count)

unviewed_feed_items() -> bool


Feed Parser Interface
+++++++++++++++++++++

parse_feed(feed_str: str, newer_than: Optional[datetime] = None) ->
    - feed_object
        - feed
            name
            description
            url
            home_page
            etag if available
            last_modified if available as string
        - entries
            enclosure_url if available
            timestamp as datetime
            text
            url