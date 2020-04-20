# By Kyle Monson

from collections import defaultdict
import datetime
import pathlib
import pytz
from dateutil.tz import tzlocal
from pony import orm
from .db_model import db, Group, Feed, FeedItem
from .defaults import update_rate


def initialize_sql(filename):
    pathlib.Path(filename).parent.mkdir(parents=True, exist_ok=True)
    initialize_db(provider='sqlite', filename=filename, create_db=True)


def initialize_db(provider='sqlite', **kwargs):
    db.bind(provider=provider, **kwargs)
    db.generate_mapping(create_tables=True)


def _group_find_add_helper(group_name):
    group = None
    if group_name is not None:
        group = Group.get(name=group_name)
        # Create group if it does not exist.
        if group is None:
            group = Group(name=group_name)
    return group


@orm.db_session
def add_get_feed(name, url, home_page, rate=update_rate, group_name=None):
    group = _group_find_add_helper(group_name)

    f = Feed.get(url=url)
    if f is None:
        f = Feed(name=name,
                 url=url,
                 home_page=home_page,
                 update_rate=rate,
                 group=group)

    return f.to_dict()


@orm.db_session
def add_get_group(name):
    g = Group.get(name=name)
    if g is None:
        g = Group(name=name)
    return g.to_dict()


@orm.db_session
def delete_group(group):
    if isinstance(group, int):
        Group[group].delete()
    else:
        Group.select(lambda g: g.name == group).delete()


@orm.db_session
def get_groups():
    q = Group.select().sort_by(Group.name)
    return [g.to_dict() for g in q]


def utc_unaware_to_local(ts):
    if ts is not None:
        ts = ts.replace(tzinfo=pytz.utc)
        ts = ts.astimezone(tzlocal())
        return ts
    return None


@orm.db_session
def get_feeds():
    result = defaultdict(list)
    q = Feed.select().sort_by(Feed.group, Feed.name)
    for f in q:
        name = f.group.name if f.group is not None else None
        fd = f.to_dict()
        fd["last_update"] = utc_unaware_to_local(fd.get("last_update"))
        result[name].append(fd)

    return result


@orm.db_session
def get_flat_feeds():
    result = list()
    q = Feed.select().sort_by(Feed.name)
    for f in q:
        fd = f.to_dict()
        fd["last_update"] = utc_unaware_to_local(fd.get("last_update"))
        result.append(fd)

    return result


@orm.db_session
def delete_feed(feed):
    if isinstance(feed, int):
        Feed[feed].delete()
    else:
        Feed.select(lambda f: f.url == feed).delete()


@orm.db_session
def update_feed(feed_id, **kwargs):
    if "group_name" in kwargs and "group_id" in kwargs:
        raise ValueError("Only allowed to specify group_id or group_name, but not both.")
    group_name = kwargs.pop("group_name", None)
    group = _group_find_add_helper(group_name)
    if group is None:
        group_id = kwargs.pop("group_id", None)
        if group_id is not None:
            group = Group[group_id]
    if group is not None:
        kwargs["group"] = group

    f = Feed[feed_id]

    # If we are trying to update the URL ensure that it's different and doesn't conflict with an existing feed.
    if "url" in kwargs:
        url = kwargs["url"]
        if url != f.url:
            target_feed = Feed.get(url=url)
            if target_feed is not None:
                raise ValueError("Updated URL already exists")
        else:
            # If the URL hasn't changed just drop it.
            kwargs.pop("url")

    f.set(**kwargs)


@orm.db_session
def add_feed_items(feed_id, items):
    result = list()
    feed = Feed[feed_id]

    for item in items:
        # Make sure it doesn't exist before we try to add it.
        feed_item = FeedItem.get(url=item["url"])
        if feed_item is None:
            f = FeedItem(feed=feed,
                         **item)
            result.append(f.to_dict())

    update_feed_last_update(feed_id)

    return result


@orm.db_session
def update_feed_last_update(feed_id):
    feed = Feed[feed_id]

    last_update = datetime.datetime.utcnow()
    # Pony doesn't support this yet.
    # last_update = last_update.replace(tzinfo=pytz.utc)
    feed.last_update = last_update


def _get_feed_item_query(unread_only):
    if unread_only:
        return FeedItem.select().sort_by(FeedItem.timestamp)
    else:
        return orm.select(i for i in FeedItem if not i.read).sort_by(FeedItem.timestamp)


@orm.db_session
def get_all_feed_items(unread_only=True):
    q = _get_feed_item_query(unread_only)
    return [f.to_dict() for f in q]


@orm.db_session
def get_group_feed_items(group_id=None, unread_only=True):
    q = _get_feed_item_query(unread_only)
    group = Group[group_id] if group_id is not None else None
    q = orm.select(i for i in q if i.feed.group == group)
    return [f.to_dict() for f in q]


@orm.db_session
def get_feed_items(feed_id, unread_only=True):
    q = _get_feed_item_query(unread_only)
    feed = Feed[feed_id]
    q = orm.select(i for i in q if i.feed == feed)
    return [f.to_dict() for f in q]


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
def mark_feed_items_viewed(feed_id):
    feed = Feed[feed_id]
    q = orm.select(i for i in FeedItem if not i.viewed and i.feed == feed)
    for i in q:
        i.set(viewed=True)
