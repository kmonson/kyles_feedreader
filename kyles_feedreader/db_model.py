# By Kyle Monson

from __future__ import annotations

from pony import orm

from datetime import datetime, timedelta


db = orm.Database()


class RootGroup(db.Entity):
    id = orm.PrimaryKey(int, auto=True)
    feeds = orm.Set('Feed')
    children = orm.Set("Group", reverse="parent")


class Group(RootGroup):
    name = orm.Required(str, index=True)
    parent = orm.Required("RootGroup", reverse="children")
    orm.composite_key(name, parent)


class Feed(db.Entity):
    id = orm.PrimaryKey(int, auto=True)
    name = orm.Required(str, index=True)
    url = orm.Required(str, unique=True)
    home_page = orm.Required(str)
    description = orm.Optional(str)
    user_name = orm.Optional(str, nullable=True)
    password = orm.Optional(str, nullable=True)
    last_update = orm.Optional(datetime)
    update_rate = orm.Required(timedelta)
    etag = orm.Optional(str, nullable=True)
    last_modified = orm.Optional(str, nullable=True)  # Stored as a string to send right back to server on request.
    group = orm.Required(RootGroup)
    items = orm.Set('FeedItem')

    @property
    def unreads(self):
        return orm.select(fi for fi in self.items if not fi.read).exists()


class FeedItem(db.Entity):
    id = orm.PrimaryKey(int, auto=True)
    feed = orm.Required(Feed)
    enclosure_url = orm.Optional(str, nullable=True)
    enclosure_path = orm.Optional(str, nullable=True)
    timestamp = orm.Optional(datetime, index=True)
    read = orm.Required(bool, index=True, default=bool)
    viewed = orm.Required(bool, index=True, default=bool)
    starred = orm.Required(bool, index=True, default=bool)
    title = orm.Required(str)
    text = orm.Optional(str)
    url = orm.Required(str, unique=True)
    orm.composite_index(read, timestamp)
