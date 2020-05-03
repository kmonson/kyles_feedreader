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
    with orm.db_session:
        yield dbi
    database.drop_all_tables(with_all_data=True)


def test_add_group(session):
    g = session.add_get_group("Foo")
    assert g["name"] == "Foo"

    g_list = session.get_groups()
    assert len(g_list) == 1
    assert g_list[0]["name"] == "Foo"


def test_delete_group_with_id(session):
    g = session.add_get_group("Foo")
    g_id = g["id"]

    g_list = session.get_groups()
    assert len(g_list) == 1

    session.delete_group(g_id)

    g_list = session.get_groups()
    assert len(g_list) == 0


def test_delete_group_with_name(session):
    g = session.add_get_group("Foo")
    g_name = g["name"]

    g_list = session.get_groups()
    assert len(g_list) == 1

    session.delete_group(g_name)

    g_list = session.get_groups()
    assert len(g_list) == 0


def test_add_feed(session):
    f = session.add_get_feed("Foo", "url", "homepage")
    assert f["name"] == "Foo"
    assert f["url"] == "url"
    assert f["home_page"] == "homepage"
    assert f["group"] is None
    assert f["update_rate"] == timedelta(hours=1)
    assert f["last_update"] is None
    assert f["etag"] == ""
    assert f["last_modified"] == ""

    feed_id = f["id"]

    f_dict = session.get_feeds_by_group()
    f = f_dict["No Group", -1][0]
    assert f["name"] == "Foo"
    assert f["url"] == "url"
    assert f["home_page"] == "homepage"
    assert f["group"] is None
    assert f["update_rate"] == timedelta(hours=1)
    assert f["last_update"] is None
    assert f["etag"] == ""
    assert f["last_modified"] == ""
    assert f["id"] == feed_id

    # Test duplicate add
    f2 = session.add_get_feed("Foo", "url", "homepage")

    assert f == f2


def test_delete_feed(session):
    f = session.add_get_feed("Foo", "url", "homepage")
    feed_id = f["id"]
    session.delete_feed(feed_id)
    f_dict = session.get_feeds()
    assert not f_dict


def test_update_feed(session):
    f = session.add_get_feed("Foo", "url", "homepage")

    feed_id = f["id"]

    session.update_feed(feed_id, home_page="homepage2", update_rate=timedelta(hours=2))

    f_dict = session.get_feeds_by_group()
    f = f_dict["No Group", -1][0]
    assert f["name"] == "Foo"
    assert f["url"] == "url"
    assert f["home_page"] == "homepage2"
    assert f["group"] is None
    assert f["update_rate"] == timedelta(hours=2)
    assert f["last_update"] is None
    assert f["etag"] == ""
    assert f["last_modified"] == ""
    assert f["id"] == feed_id


def test_add_group_via_feed(session):
    f = session.add_get_feed("Foo", "url", "homepage", group_name="Test_Group")

    feed_id = f["id"]
    g_list = session.get_groups()
    g_id = g_list[0]["id"]
    assert len(g_list) == 1
    assert g_list[0]["name"] == "Test_Group"

    f_dict = session.get_feeds_by_group()
    f = f_dict["Test_Group", 1][0]
    assert f["name"] == "Foo"
    assert f["url"] == "url"
    assert f["home_page"] == "homepage"
    assert f["group"] == g_id
    assert f["update_rate"] == timedelta(hours=1)
    assert f["last_update"] is None
    assert f["etag"] == ""
    assert f["last_modified"] == ""
    assert f["id"] == feed_id


def test_add_group_via_update_feed(session):
    f = session.add_get_feed("Foo", "url", "homepage")

    feed_id = f["id"]

    session.update_feed(feed_id, group_name="Test_Group")

    g_list = session.get_groups()
    g_id = g_list[0]["id"]
    assert len(g_list) == 1
    assert g_list[0]["name"] == "Test_Group"

    f_dict = session.get_feeds_by_group()
    f = f_dict["Test_Group", 1][0]
    assert f["group"] == g_id


def test_group_delete_feed_no_group(session):
    f = session.add_get_feed("Foo", "url", "homepage", group_name="Test_Group")

    feed_id = f["id"]
    g_list = session.get_groups()
    g_id = g_list[0]["id"]
    assert len(g_list) == 1
    assert g_list[0]["name"] == "Test_Group"

    session.delete_group(g_id)

    g_list = session.get_groups()
    assert len(g_list) == 0

    f_dict = session.get_feeds_by_group()
    f = f_dict["No Group", -1][0]
    assert f["id"] == feed_id
    assert "Test_Group" not in f_dict


def test_add_feed_items(session):
    f = session.add_get_feed("Foo", "url", "homepage")

    items = [
        {"title": "Foo1", "url": "Foo1URL"},
        {"title": "Foo2", "url": "Foo2URL"}
    ]
    session.add_feed_items(f["id"], items)
    fi = session.get_feed_items(f["id"])
    assert fi[0]["url"] == "Foo1URL"
    assert fi[0]["title"] == "Foo1"
    assert fi[0]["read"] is False
    assert fi[0]["viewed"] is False

    assert fi[1]["url"] == "Foo2URL"
    assert fi[1]["title"] == "Foo2"
    assert fi[1]["read"] is False
    assert fi[1]["viewed"] is False


def test_all_viewed_items(session):
    f = session.add_get_feed("Foo", "url", "homepage")

    items = [
        {"title": "Foo1", "url": "Foo1URL"},
        {"title": "Foo2", "url": "Foo2URL"}
    ]
    session.add_feed_items(f["id"], items)
    fi = session.get_feed_items(f["id"])

    assert fi[0]["viewed"] is False
    assert fi[1]["viewed"] is False

    session.mark_all_items_viewed()

    fi = session.get_feed_items(f["id"])

    assert fi[0]["viewed"] is True
    assert fi[1]["viewed"] is True


def test_group_viewed_items(session):
    f1 = session.add_get_feed("Foo1", "url1", "homepage", group_name="g1")
    f2 = session.add_get_feed("Foo2", "url2", "homepage")

    items = [
        {"title": "Foo11", "url": "Foo11URL"}
    ]
    session.add_feed_items(f1["id"], items)

    items = [
        {"title": "Foo21", "url": "Foo21URL"}
    ]
    session.add_feed_items(f2["id"], items)

    fi1 = session.get_feed_items(f1["id"])
    fi2 = session.get_feed_items(f2["id"])

    assert fi1[0]["viewed"] is False
    assert fi2[0]["viewed"] is False

    session.mark_group_items_viewed(f1["group"])

    fi1 = session.get_feed_items(f1["id"])
    fi2 = session.get_feed_items(f2["id"])

    assert fi1[0]["viewed"] is True
    assert fi2[0]["viewed"] is False

    session.mark_group_items_viewed(None)

    fi1 = session.get_feed_items(f1["id"])
    fi2 = session.get_feed_items(f2["id"])

    assert fi1[0]["viewed"] is True
    assert fi2[0]["viewed"] is True


def test_has_unviewed(session):
    f = session.add_get_feed("Foo", "url", "homepage")

    items = [
        {"title": "Foo1", "url": "Foo1URL"},
        {"title": "Foo2", "url": "Foo2URL"}
    ]
    session.add_feed_items(f["id"], items)

    assert session.has_unviewed_feed_items()

    session.mark_feed_items_viewed(f["id"])

    assert not session.has_unviewed_feed_items()
