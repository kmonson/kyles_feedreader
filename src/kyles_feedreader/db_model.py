# By Kyle Monson

from pony import orm

from datetime import datetime, timedelta
from typing import NamedTuple


class GroupTuple(NamedTuple):
    name: str
    id: int


NO_GROUP_TUPLE = GroupTuple("No Group", -1)
db = orm.Database()


class Group(db.Entity):
    name = orm.Required(str, unique=True, index=True)
    feeds = orm.Set('Feed')

    def to_tuple(self):
        return GroupTuple(**self.to_dict())


class Feed(db.Entity):
    name = orm.Required(str, index=True)
    url = orm.Required(str, unique=True)
    home_page = orm.Required(str)
    description = orm.Optional(str)
    user_name = orm.Optional(str)
    password = orm.Optional(str)
    last_update = orm.Optional(datetime)
    update_rate = orm.Required(timedelta)
    etag = orm.Optional(str)
    last_modified = orm.Optional(str)  # Stored as a string to send right back to server on request.
    group = orm.Optional(Group)
    items = orm.Set('FeedItem')

    @property
    def unreads(self):
        return orm.select(fi for fi in self.items if not fi.read).exists()

    def to_dict(self):
        result = super().to_dict()
        result["unreads"] = self.unreads
        return result


class FeedItem(db.Entity):
    feed = orm.Required(Feed)
    enclosure_url = orm.Optional(str)
    enclosure_path = orm.Optional(str)
    timestamp = orm.Optional(datetime, index=True)
    read = orm.Required(bool, index=True, default=bool)
    viewed = orm.Required(bool, index=True, default=bool)
    starred = orm.Required(bool, index=True, default=bool)
    title = orm.Required(str)
    text = orm.Optional(str)
    url = orm.Required(str, unique=True)
    orm.composite_index(read, timestamp)
