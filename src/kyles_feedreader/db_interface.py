# By Kyle Monson

from collections import defaultdict
import datetime
import pytz
from dateutil.tz import tzlocal
from pony import orm
from .db_model import db, Group, Feed, FeedItem
from .defaults import update_rate


def initialize_sql(filename):
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
def add_feed(name, url, home_page, rate=update_rate, group_name=None):
    group = _group_find_add_helper(group_name)

    f = Feed.get(url=url)
    if f is not None:
        raise ValueError(f"Feed at {url} already exists in database.")

    f = Feed(name=name,
             url=url,
             home_page=home_page,
             update_rate=rate,
             group=group)

    return f.to_dict()


@orm.db_session
def add_group(name):
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
def delete_feed(feed_id):
    Feed[feed_id].delete()


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

    Feed[feed_id].set(**kwargs)


@orm.db_session
def add_feed_items(feed_id, items):
    feed = Feed[feed_id]

    for item in items:
        # Make sure it doesn't exist before we try to add it.
        feed_item = FeedItem.get(url=item["url"])
        if feed_item is None:
            FeedItem(feed=feed,
                     **item)

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
def get_group_feed_items(group_id, unread_only=True):
    q = _get_feed_item_query(unread_only)
    group = Group[group_id]
    q = orm.select(i for i in q if i.feed.group == group)
    return [f.to_dict() for f in q]


@orm.db_session
def get_feed_items(feed_id, unread_only=True):
    q = _get_feed_item_query(unread_only)
    feed = Feed[feed_id]
    q = orm.select(i for i in q if i.feed == feed)
    return [f.to_dict() for f in q]

