import pytest
from kyles_feedreader import db_interface as dbi
from kyles_feedreader.db_model import db
from pony import orm
from datetime import timedelta


@pytest.fixture(scope="session")
def database():
    dbi.initialize_sql(":memory:")
    return db


@pytest.fixture
def session(database):
    database.create_tables()
    yield dbi
    database.drop_all_tables(with_all_data=True)



def test_add_group(session):
    g = session.add_find_group("Foo", dbi.root_group)
    assert g.name == "Foo"

    g_list = session.get_groups(dbi.root_group)
    assert len(g_list) == 1
    assert g_list[0].name == "Foo"


def test_delete_group_with_id(session):
    g = session.add_find_group("Foo", dbi.root_group)
    g_id = g.id

    g_list = session.get_groups(dbi.root_group)
    assert len(g_list) == 1

    session.delete_group(g_id)

    g_list = session.get_groups(dbi.root_group)
    assert len(g_list) == 0


def test_delete_group_with_data(session):
    g = session.add_find_group("Foo", dbi.root_group)

    g_list = session.get_groups(dbi.root_group)
    assert len(g_list) == 1

    session.delete_group(g)

    g_list = session.get_groups(dbi.root_group)
    assert len(g_list) == 0


def test_add_feed(session):
    f = session.add_feed("Foo", "url", "homepage", dbi.root_group)
    assert f.name == "Foo"
    assert f.url == "url"
    assert f.home_page == "homepage"
    assert f.group == dbi.root_group.id
    assert f.update_rate == timedelta(hours=1)
    assert f.last_update is None
    assert f.etag is None
    assert f.last_modified is None

    feed_id = f.id

    f_list = session.get_feeds()
    f = f_list[0]
    assert f.name == "Foo"
    assert f.url == "url"
    assert f.home_page == "homepage"
    assert f.group == dbi.root_group.id
    assert f.update_rate == timedelta(hours=1)
    assert f.last_update is None
    assert f.etag is None
    assert f.last_modified is None
    assert f.id == feed_id

    # Test duplicate add
    with pytest.raises(ValueError, match="Feed already exists"):
        session.add_feed("Foo", "url", "homepage", dbi.root_group)


def test_delete_feed(session):
    f = session.add_feed("Foo", "url", "homepage", dbi.root_group)
    session.delete_feed(f)
    f_list = session.get_feeds()
    assert not f_list


def test_update_feed(session):
    f = session.add_feed("Foo", "url", "homepage", dbi.root_group)

    feed_id = f.id

    session.update_feed(f, home_page="homepage2", update_rate=timedelta(hours=2))

    f_list = session.get_feeds()
    f = f_list[0]
    assert f.name == "Foo"
    assert f.url == "url"
    assert f.home_page == "homepage2"
    assert f.group == dbi.root_group.id
    assert f.update_rate == timedelta(hours=2)
    assert f.last_update is None
    assert f.etag is None
    assert f.last_modified is None
    assert f.id == feed_id


def test_group_delete_recurse(session):
    g = session.add_find_group("Test_Group", dbi.root_group)
    session.add_feed("Foo", "url", "homepage", g)

    session.delete_group(g, recursive=True)

    g_list = session.get_groups(dbi.root_group)
    assert len(g_list) == 0
    f_list = session.get_feeds(dbi.root_group)
    assert len(f_list) == 0


def test_group_delete_no_recurse(session):
    g = session.add_find_group("Test_Group", dbi.root_group)
    f = session.add_feed("Foo", "url", "homepage", g)
    feed_id = f.id

    session.delete_group(g, recursive=False)

    g_list = session.get_groups(dbi.root_group)
    assert len(g_list) == 0

    f_list = session.get_feeds(dbi.root_group)
    assert len(f_list) == 1
    f2 = f_list[0]
    assert f2.id == feed_id


def test_add_feed_items(session):
    f = session.add_feed("Foo", "url", "homepage", dbi.root_group)

    items = [
        {"title": "Foo1", "url": "Foo1URL"},
        {"title": "Foo2", "url": "Foo2URL"}
    ]
    session.add_feed_items(f, items)
    fi = session.get_feed_items(f)
    assert fi[0].url == "Foo1URL"
    assert fi[0].title == "Foo1"
    assert fi[0].read is False
    assert fi[0].viewed is False

    assert fi[1].url == "Foo2URL"
    assert fi[1].title == "Foo2"
    assert fi[1].read is False
    assert fi[1].viewed is False


def test_all_viewed_items(session):
    f = session.add_feed("Foo", "url", "homepage", dbi.root_group)

    items = [
        {"title": "Foo1", "url": "Foo1URL"},
        {"title": "Foo2", "url": "Foo2URL"}
    ]
    session.add_feed_items(f, items)
    fi = session.get_feed_items(f)

    assert fi[0].viewed is False
    assert fi[1].viewed is False

    session.mark_all_items_viewed()

    fi = session.get_feed_items()

    assert fi[0].viewed is True
    assert fi[1].viewed is True


def test_group_viewed_items(session):
    g = session.add_find_group("Test_Group", dbi.root_group)
    f1 = session.add_feed("Foo1", "url1", "homepage", g)
    f2 = session.add_feed("Foo2", "url2", "homepage")

    items = [
        {"title": "Foo11", "url": "Foo11URL"}
    ]
    session.add_feed_items(f1, items)

    items = [
        {"title": "Foo21", "url": "Foo21URL"}
    ]
    session.add_feed_items(f2, items)

    fi1 = session.get_feed_items(f1)
    fi2 = session.get_feed_items(f2)

    assert fi1[0].viewed is False
    assert fi2[0].viewed is False

    session.mark_group_items_viewed(f1.group)

    fi1 = session.get_feed_items(f1)
    fi2 = session.get_feed_items(f2)

    assert fi1[0].viewed is True
    assert fi2[0].viewed is False

    session.mark_group_items_viewed(None)

    fi1 = session.get_feed_items(f1)
    fi2 = session.get_feed_items(f2)

    assert fi1[0].viewed is True
    assert fi2[0].viewed is True


def test_has_unviewed(session):
    f = session.add_feed("Foo", "url", "homepage", dbi.root_group)

    items = [
        {"title": "Foo1", "url": "Foo1URL"},
        {"title": "Foo2", "url": "Foo2URL"}
    ]
    session.add_feed_items(f, items)

    assert session.has_unviewed_feed_items()

    session.mark_feed_items_viewed(f)

    assert not session.has_unviewed_feed_items()
