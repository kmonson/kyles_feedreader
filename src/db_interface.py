# By Kyle Monson

from collections import defaultdict
from datetime import timedelta
from pony import orm
from .db_model import db, Group, Feed, FeedItem


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
def add_feed(name, url, home_page, update_rate=timedelta(hours=1), group_name=None):
    group = _group_find_add_helper(group_name)

    f = Feed(name=name,
             url=url,
             home_page=home_page,
             update_rate=update_rate,
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


@orm.db_session
def get_feeds():
    result = defaultdict(list)
    q = Feed.select().sort_by(Feed.group, Feed.name)
    for f in q:
        name = f.group.name if f.group is not None else None
        result[name].append(f.to_dict())

    return result


@orm.db_session
def delete_feed(feed_id):
    Feed[feed_id].delete()


@orm.db_session
def update_feed(feed_id, **kwargs):
    group_name = kwargs.pop("group_name", None)
    group = _group_find_add_helper(group_name)
    if group is not None:
        kwargs["group"] = group

    Feed[feed_id].set(**kwargs)


@orm.db_session
def add_feed_items(feed_id, items):
    feed = Feed[feed_id]

    for item in items:
        FeedItem(feed=feed,
                 **item)