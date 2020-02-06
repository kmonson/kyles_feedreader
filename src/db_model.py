# By Kyle Monson

from pony import orm

from datetime import datetime, timedelta

db = orm.Database()


class Group(db.Entity):
    name = orm.Required(str, unique=True, index=True)
    feeds = orm.Set('Feed')


class Feed(db.Entity):
    name = orm.Required(str, index=True)
    url = orm.Required(str, unique=True)
    home_page = orm.Required(str)
    description = orm.Optional(str)
    last_update = orm.Optional(datetime)
    update_rate = orm.Required(timedelta)
    etag = orm.Optional(str)
    last_modified = orm.Optional(str)  # Stored as a string to send right back to server on request.
    group = orm.Optional(Group)
    items = orm.Set('FeedItem')


class FeedItem(db.Entity):
    feed = orm.Required(Feed)
    enclosure_url = orm.Optional(str)
    enclosure_path = orm.Optional(str)
    timestamp = orm.Required(datetime, index=True)
    read = orm.Required(bool, index=True, default=bool)
    viewed = orm.Required(bool, default=bool)
    text = orm.Required(str)
    url = orm.Required(str, unique=True)
    orm.composite_index(read, timestamp)
