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
from .db_model import db, Group, Feed, FeedItem, RootGroup
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
        self.feeds = [_db_to_interface(f, recursive=True) for f in self.feeds]
        self.children = [_db_to_interface(g, recursive=True) for g in self.children]

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


_db_interface_map = {Feed: FeedData,
                     Group: GroupData,
                     FeedItem: FeedItemData}


def _get_interface_params(db_obj: Feed | RootGroup | FeedItem) -> tuple[type, list[str]]:
    klass = _db_interface_map[type(db_obj)]
    return klass, [f.name for f in fields(klass)]


@singledispatch
def _db_to_interface(db_obj, recursive: bool = False):
    raise NotImplementedError(f"Converting unsupported db model object: {db_obj}")


@_db_to_interface.register(RootGroup)
def _(db_obj, recursive: bool = False):
    recurse = ["feeds", "children"] if recursive else []
    return GroupData(**db_obj.to_dict(only=["id"] + recurse,
                                      with_collections=recursive, related_objects=recursive))


@_db_to_interface.register(FeedItem)
def _(db_obj, recursive: bool = False):
    klass, params = _get_interface_params(db_obj)
    return klass(**db_obj.to_dict(only=params, with_collections=recursive, related_objects=recursive))


@_db_to_interface.register(Group)
def _(db_obj, recursive: bool = False):
    klass, params = _get_interface_params(db_obj)
    params.remove("unreads")
    if not recursive:
        params.remove("feeds")
        params.remove("children")
    return klass(**db_obj.to_dict(only=params, with_collections=recursive, related_objects=recursive))


@_db_to_interface.register(Feed)
def _(db_obj, recursive: bool = False):
    klass, params = _get_interface_params(db_obj)
    params.remove("unreads")
    db_dict = db_obj.to_dict(only=params, with_collections=recursive, related_objects=recursive)
    db_dict["unreads"] = db_obj.unreads
    return klass(**db_dict)


root_group: GroupData


def initialize_sql(filename: str | pathlib.Path) -> None:
    if isinstance(filename, str) and not filename.startswith(":"):
        pathlib.Path(filename).parent.mkdir(parents=True, exist_ok=True)
    initialize_db(provider='sqlite', filename=filename, create_db=True)


def initialize_db(provider: str = 'sqlite', **kwargs: Any) -> None:
    db.bind(provider=provider, **kwargs)
    db.generate_mapping(create_tables=True)

    with orm.db_session:
        global root_group
        # Ensure the root group exists.
        root_object = orm.select(g for g in RootGroup if not isinstance(g, Group)).first()
        if root_object is None:
            root_group = _db_to_interface(RootGroup())
        else:
            root_group = _db_to_interface(root_object)


def _group_find_add_helper(group_name: str, group_parent: GroupHandle) -> Group:
    group = None
    if group_name is not None:
        group = Group.get(name=group_name, parent=group_parent)
        # Create group if it does not exist.
        if group is None:
            group = Group(name=group_name, parent=group_parent)
    return group


@orm.db_session
def add_feed(name, url, home_page, group_data: GroupData, rate=update_rate) -> FeedData:
    group = RootGroup.get(id=group_data.id)
    assert group is not None

    f = Feed.get(url=url)
    if f is not None:
        raise ValueError(f"Feed already exists for {url}")

    f = Feed(name=name,
             url=url,
             home_page=home_page,
             update_rate=rate,
             group=group)

    return _db_to_interface(f)

@orm.db_session
def find_feed_from_url(url) -> FeedData | None:
    f = Feed.get(url=url)
    if f is not None:
        return _db_to_interface(f)
    return None


@orm.db_session
def add_find_group(group_name: str, parent_data: GroupData) -> GroupData:
    parent_id = parent_data.id
    g = Group.get(name=group_name, parent=parent_id)
    if g is None:
        g = Group(name=group_name, parent=parent_id)
    return _db_to_interface(g)


def find_group_by_name(group_name: str, parent_data: GroupData) -> GroupData:
    g = Group.get(name=group_name, parent=parent_data.id)
    return None if g is None else _db_to_interface(g)


@orm.db_session
def delete_group(group: GroupData | GroupHandle, recursive: bool = True) -> None:
    if isinstance(group, GroupData):
        group_id = group.id
    else:
        group_id = group

    assert group_id != root_group.id

    group_obj = RootGroup.get(id=group_id)

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
def get_groups(parent_data: GroupData) -> list[GroupData]:
    parent_id = parent_data.id
    q = Group.select(parent=parent_id).sort_by(Group.name)
    return [_db_to_interface(g) for g in q]


def utc_unaware_to_local(ts: datetime.datetime) -> datetime.datetime | None:
    if ts is not None:
        ts = ts.replace(tzinfo=pytz.utc)
        ts = ts.astimezone(tzlocal())
        return ts
    return None


@orm.db_session
def get_feeds(group_data: GroupData | None = None) -> list[FeedData]:
    if group_data is None:
        fq = Feed.select().sort_by(Feed.name)
    else:
        group = RootGroup.get(id=group_data.id)
        assert group is not None
        fq = Feed.select(lambda feed: feed.group is group).order_by(Feed.name)
    return [_db_to_interface(f) for f in fq]


@orm.db_session
def get_feed(feed_id: FeedHandle):
    feed = Feed.get(id=feed_id)
    if feed is None:
        return None
    return _db_to_interface(feed)


@orm.db_session
def delete_feed(feed: FeedData | FeedHandle):
    if isinstance(feed, FeedData):
        feed = feed.id
    Feed[feed].delete()


@orm.db_session
def update_feed(feed: FeedData, **kwargs):
    group = kwargs.pop("group", None)
    if group is not None:
        if isinstance(group, GroupData):
            group = group.id
            kwargs["group"] = group
        assert Group[group] is not None

    f = Feed[feed.id]

    # If we are trying to update the URL ensure that it's different and doesn't conflict with an existing feed.
    if "url" in kwargs:
        url = kwargs["url"]
        if url != f.url:
            target_feed = Feed.get(url=url)
            if target_feed is not None:
                raise ValueError(f"Updated URL already exists for feed {target_feed.name}")
        else:
            # If the URL hasn't changed just drop it.
            kwargs.pop("url")

    f.set(**kwargs)

    feed.update(**kwargs)


@orm.db_session
def add_feed_items(feed: FeedData, items: list[dict[str, Any]]) -> list[FeedItemData]:
    result = []
    f = Feed[feed.id]

    for item in items:
        # Make sure it doesn't exist before we try to add it.
        feed_item = f.items.select(url=item["url"]).first()
        if feed_item is None:
            f_item = f.items.create(**item)
            result.append(_db_to_interface(f_item))

    update_feed_last_update(feed)

    return result


@orm.db_session
def update_feed_last_update(feed: FeedData) -> None:
    f = Feed[feed.id]

    last_update = datetime.datetime.utcnow()
    # Pony doesn't support this yet.
    # last_update = last_update.replace(tzinfo=pytz.utc)
    f.last_update = last_update


def _get_feed_item_query(unread_only):
    if not unread_only:
        return FeedItem.select().sort_by(orm.desc(FeedItem.timestamp))
    else:
        return orm.select(i for i in FeedItem if not i.read).sort_by(orm.desc(FeedItem.timestamp))


@orm.db_session
def get_all_feed_items(unread_only=True) -> list[FeedItemData]:
    q = _get_feed_item_query(unread_only)
    return [_db_to_interface(f) for f in q]


@orm.db_session
def get_group_feed_items(group_id=None, unread_only=True) -> list[FeedItemData]:
    q = _get_feed_item_query(unread_only)
    group = Group[group_id] if group_id is not None else None
    q = orm.select(i for i in q if i.feed.group == group)
    return [_db_to_interface(f) for f in q]


@orm.db_session
def get_feed_items(feed: FeedData, unread_only=True) -> list[FeedItemData]:
    q = _get_feed_item_query(unread_only)
    feed = Feed[feed.id]
    q = orm.select(i for i in q if i.feed == feed)
    return [_db_to_interface(f) for f in q]


@orm.db_session
def get_feed_item(feed_item_id):
    feed_item = FeedItem.get(id=feed_item_id)
    if feed_item is None:
        return None
    return feed_item.to_dict()


@orm.db_session
def has_unviewed_feed_items():
    r = orm.select(i for i in FeedItem if not i.viewed).exists()
    return r

# ponyorm does not yet support bulk update so we do it in a loop.
@orm.db_session
def mark_all_items_viewed():
    q = orm.select(i for i in FeedItem if not i.viewed)
    for i in q:
        i.set(viewed=True)


@orm.db_session
def mark_group_items_viewed(group_id=None):
    group = Group[group_id] if group_id is not None else None
    q = orm.select(i for i in FeedItem if not i.viewed and i.feed.group == group)
    for i in q:
        i.set(viewed=True)


@orm.db_session
def mark_feed_items_viewed(feed: FeedData):
    feed = Feed[feed.id]
    q = orm.select(i for i in FeedItem if not i.viewed and i.feed == feed)
    for i in q:
        i.set(viewed=True)
