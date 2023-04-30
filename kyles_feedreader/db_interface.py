# By Kyle Monson

from collections import defaultdict
import datetime
from functools import singledispatch
import pathlib
from dataclasses import dataclass, fields, field
import pytz
from dateutil.tz import tzlocal
from pony import orm
from typing import TypeAlias, Type, TypeVar, Any
from .db_model import define_entities
from .defaults import update_rate


ALL = object()


GroupHandle: TypeAlias = int
FeedHandle: TypeAlias = int
FeedItemHandle: TypeAlias = int
T = TypeVar('T')


class Updatable:
    def update(self, **kwargs: dict[str, Any]):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise TypeError(f"Updatable does not have {key} attribute")


@dataclass
class GroupData(Updatable):
    id: GroupHandle
    name: str | None = None
    parent: GroupHandle | None = None
    feeds: list["FeedData"] = field(default_factory=list)
    children: list["GroupData"] = field(default_factory=list)
    unreads: bool = field(init=False)

    def __post_init__(self):
        self.feeds = [db_to_feed(f, recursive=True) for f in self.feeds]
        self.children = [db_to_group(g, recursive=True) for g in self.children]

    def update_unread(self):
        for g in self.children:
            g.update_unread()
        self.unreads = any(f.unreads for f in self.feeds) or any(g.unreads for g in self.children)


@dataclass
class FeedData(Updatable):
    id: FeedHandle
    name: str
    url: str
    home_page: str
    description: str | None
    user_name: str | None
    password: str | None
    last_update: datetime.datetime | None
    update_rate: datetime.timedelta
    etag: str | None
    last_modified: str | None  # Stored as a string to send right back to server on request.
    group: GroupHandle
    unreads: bool
    # items is intentionally omitted to allow us to do a recursive to_dict call without scooping them all up.


@dataclass
class FeedItemData(Updatable):
    id: FeedItemHandle
    title: str
    text: str | None
    url: str
    feed: FeedHandle
    read: bool
    viewed: bool
    starred: bool
    timestamp: datetime.datetime | None
    enclosure_url: str | None
    enclosure_path: str | None


def _get_interface_params(klass) -> list[str]:
    return [f.name for f in fields(klass)]


def db_to_root_group(db_obj, recursive: bool = False):
    recurse = ["feeds", "children"] if recursive else []
    return GroupData(**db_obj.to_dict(only=["id"] + recurse,
                                      with_collections=recursive, related_objects=recursive))


def db_to_feed_item(db_obj, recursive: bool = False):
    params = _get_interface_params(FeedItemData)
    return FeedItemData(**db_obj.to_dict(only=params, with_collections=recursive, related_objects=recursive))


def db_to_group(db_obj, recursive: bool = False):
    params = _get_interface_params(GroupData)
    params.remove("unreads")
    if not recursive:
        params.remove("feeds")
        params.remove("children")
    return GroupData(**db_obj.to_dict(only=params, with_collections=recursive, related_objects=recursive))


def db_to_feed(db_obj, recursive: bool = False):
    params = _get_interface_params(FeedData)
    params.remove("unreads")
    db_dict = db_obj.to_dict(only=params, with_collections=recursive, related_objects=recursive)
    db_dict["unreads"] = db_obj.unreads
    return FeedData(**db_dict)


class DBInterface:
    def __init__(self, filename: str | pathlib.Path) -> None:
        self.db = orm.Database()
        define_entities(self.db)
        self.root_group: GroupData = self.initialize_sqlite(filename)

    def initialize_sqlite(self, filename: str | pathlib.Path) -> GroupData:
        if not isinstance(filename, str) or not filename.startswith(":"):
            pathlib.Path(filename).parent.mkdir(parents=True, exist_ok=True)
        return self.initialize_db(provider='sqlite', filename=filename, create_db=True)

    def initialize_db(self, provider: str = 'sqlite', **kwargs: Any) -> GroupData:
        db = self.db
        db.bind(provider=provider, **kwargs)
        db.generate_mapping(create_tables=True)

        with orm.db_session:
            # Ensure the root group exists.
            root_object = orm.select(g for g in db.RootGroup if not isinstance(g, db.Group)).first()
            if root_object is None:
                root_group = db_to_root_group(db.RootGroup())
            else:
                root_group = db_to_root_group(root_object)
        return root_group

    @orm.db_session
    def add_feed(self, name, url, home_page, group_data: GroupData, rate=update_rate) -> FeedData:
        db = self.db
        group = db.RootGroup.get(id=group_data.id)
        assert group is not None

        f = db.Feed.get(url=url)
        if f is not None:
            raise ValueError(f"Feed already exists for {url}")

        f = db.Feed(name=name,
                    url=url,
                    home_page=home_page,
                    update_rate=rate,
                    group=group)

        return db_to_feed(f)

    @orm.db_session
    def find_feed_from_url(self, url) -> FeedData | None:
        f = self.db.Feed.get(url=url)
        if f is not None:
            return db_to_feed(f)
        return None

    @orm.db_session
    def add_find_group(self, group_name: str, parent_data: GroupData) -> GroupData:
        db = self.db
        parent_id = parent_data.id
        g = db.Group.get(name=group_name, parent=parent_id)
        if g is None:
            g = db.Group(name=group_name, parent=parent_id)
        return db_to_group(g)

    @orm.db_session
    def find_group_by_name(self, group_name: str, parent_data: GroupData) -> GroupData | None:
        g = self.db.Group.get(name=group_name, parent=parent_data.id)
        return None if g is None else db_to_feed(g)

    @orm.db_session
    def delete_group(self, group: GroupData | GroupHandle, recursive: bool = True) -> None:
        if isinstance(group, GroupData):
            group_id = group.id
        else:
            group_id = group

        assert group_id != self.root_group.id

        group_obj = self.db.RootGroup.get(id=group_id)

        if group_obj is None:
            raise ValueError(f"Group ID {group_id} does not exist in database")

        # Pony recursively deletes children unless we move them out of the group.
        if not recursive:
            parent_id = group_obj.parent
            for c in group_obj.children:
                c.parent = parent_id
            for f in group_obj.feeds:
                f.group = parent_id

        group_obj.delete()

    @orm.db_session
    def get_groups(self, parent_data: GroupData) -> list[GroupData]:
        group = self.db.Group
        parent_id = parent_data.id
        q = group.select(parent=parent_id).sort_by(group.name)
        return [db_to_group(g) for g in q]

    @orm.db_session
    def get_feeds(self, group_data: GroupData | None = None) -> list[FeedData]:
        feed = self.db.Feed
        if group_data is None:
            fq = feed.select().sort_by(feed.name)
        else:
            group = self.db.RootGroup.get(id=group_data.id)
            assert group is not None
            fq = feed.select(lambda f: f.group is group).order_by(feed.name)
        return [db_to_feed(f) for f in fq]

    @orm.db_session
    def get_feed(self, feed_id: FeedHandle) -> FeedData | None:
        feed = self.db.Feed.get(id=feed_id)
        if feed is None:
            return None
        return db_to_feed(feed)

    @orm.db_session
    def delete_feed(self, feed: FeedData):
        self.db.Feed[feed.id].delete()

    @orm.db_session
    def update_feed(self, feed: FeedData, **kwargs):
        db = self.db
        group = kwargs.pop("group", None)
        if group is not None:
            if isinstance(group, GroupData):
                group = group.id
                kwargs["group"] = group
            assert db.RootGroup[group] is not None

        f = db.Feed[feed.id]

        # If we are trying to update the URL ensure that it's different and doesn't conflict with an existing feed.
        if "url" in kwargs:
            url = kwargs["url"]
            if url != f.url:
                target_feed = db.Feed.get(url=url)
                if target_feed is not None:
                    raise ValueError(f"Updated URL already exists for feed {target_feed.name}")
            else:
                # If the URL hasn't changed just drop it.
                kwargs.pop("url")

        f.set(**kwargs)
        feed.update(**kwargs)

    @orm.db_session
    def add_feed_items(self, feed: FeedData, items: list[dict[str, Any]]) -> list[FeedItemData]:
        result = []
        f = self.db.Feed[feed.id]

        for item in items:
            # Make sure it doesn't exist before we try to add it.
            feed_item = f.items.select(url=item["url"]).first()
            if feed_item is None:
                f_item = f.items.create(**item)
                result.append(db_to_feed_item(f_item))

        self.update_feed_last_update(feed)
        return result

    @orm.db_session
    def update_feed_last_update(self, feed: FeedData) -> None:
        f = self.db.Feed[feed.id]

        last_update = datetime.datetime.utcnow()
        # Pony doesn't support this yet.
        # last_update = last_update.replace(tzinfo=pytz.utc)
        f.last_update = last_update

    def _get_feed_item_query(self, unread_only: bool):
        feed_item = self.db.FeedItem
        if not unread_only:
            return feed_item.select().sort_by(orm.desc(feed_item.timestamp))
        else:
            return orm.select(i for i in feed_item if not i.read).sort_by(orm.desc(feed_item.timestamp))


    @orm.db_session
    def get_all_feed_items(self, unread_only=True) -> list[FeedItemData]:
        q = self._get_feed_item_query(unread_only)
        return [db_to_feed_item(f) for f in q]

    @orm.db_session
    def get_group_feed_items(self, group: GroupData, unread_only=True) -> list[FeedItemData]:
        group_id = group.id
        q = self._get_feed_item_query(unread_only)
        group = self.db.RootGroup[group_id] if group_id is not None else None
        q = orm.select(i for i in q if i.feed.group == group)
        return [db_to_feed_item(f) for f in q]

    @orm.db_session
    def get_feed_items(self, feed: FeedData, unread_only=True) -> list[FeedItemData]:
        q = self._get_feed_item_query(unread_only)
        feed = self.db.Feed[feed.id]
        q = orm.select(i for i in q if i.feed == feed)
        return [db_to_feed_item(f) for f in q]

    @orm.db_session
    def has_unviewed_feed_items(self):
        r = orm.select(i for i in self.db.FeedItem if not i.viewed).exists()
        return r

    @orm.db_session
    def mark_all_items_viewed(self):
        # ponyorm does not yet support bulk update, so we do it in a loop.
        q = orm.select(i for i in self.db.FeedItem if not i.viewed)
        for i in q:
            i.set(viewed=True)

    @orm.db_session
    def mark_group_items_viewed(self, group: GroupData):
        group = self.db.RootGroup[group.id]
        q = orm.select(i for i in self.db.FeedItem if not i.viewed and i.feed.group == group)
        for i in q:
            i.set(viewed=True)

    @orm.db_session
    def mark_feed_items_viewed(self, feed: FeedData):
        feed = self.db.Feed[feed.id]
        q = orm.select(i for i in self.db.FeedItem if not i.viewed and i.feed == feed)
        for i in q:
            i.set(viewed=True)
