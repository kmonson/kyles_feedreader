import pytest
from src import db_interface as dbi
from src.db_model import db
from pony import orm
from datetime import timedelta, datetime


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
    g = session.add_group("Foo")
    assert g["name"] == "Foo"

    g_list = session.get_groups()
    assert len(g_list) == 1
    assert g_list[0]["name"] == "Foo"


def test_delete_group_with_id(session):
    g = session.add_group("Foo")
    g_id = g["id"]

    g_list = session.get_groups()
    assert len(g_list) == 1

    session.delete_group(g_id)

    g_list = session.get_groups()
    assert len(g_list) == 0


def test_delete_group_with_name(session):
    g = session.add_group("Foo")
    g_name = g["name"]

    g_list = session.get_groups()
    assert len(g_list) == 1

    session.delete_group(g_name)

    g_list = session.get_groups()
    assert len(g_list) == 0


def test_add_feed(session):
    f = session.add_feed("Foo", "url", "homepage")
    assert f["name"] == "Foo"
    assert f["url"] == "url"
    assert f["home_page"] == "homepage"
    assert f["group"] is None
    assert f["update_rate"] == timedelta(hours=1)
    assert f["last_update"] is None
    assert f["etag"] == ""
    assert f["last_modified"] == ""

    feed_id = f["id"]

    f_dict = session.get_feeds()
    f = f_dict[None][0]
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
    with pytest.raises(ValueError):
        f = session.add_feed("Foo", "url", "homepage")


def test_delete_feed(session):
    f = session.add_feed("Foo", "url", "homepage")
    feed_id = f["id"]
    session.delete_feed(feed_id)
    f_dict = session.get_feeds()
    assert not f_dict


def test_update_feed(session):
    f = session.add_feed("Foo", "url", "homepage")

    feed_id = f["id"]

    session.update_feed(feed_id, home_page="homepage2", update_rate=timedelta(hours=2))

    f_dict = session.get_feeds()
    f = f_dict[None][0]
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
    f = session.add_feed("Foo", "url", "homepage", group_name="Test_Group")

    feed_id = f["id"]
    g_list = session.get_groups()
    g_id = g_list[0]["id"]
    assert len(g_list) == 1
    assert g_list[0]["name"] == "Test_Group"

    f_dict = session.get_feeds()
    f = f_dict["Test_Group"][0]
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
    f = session.add_feed("Foo", "url", "homepage")

    feed_id = f["id"]

    session.update_feed(feed_id, group_name="Test_Group")

    g_list = session.get_groups()
    g_id = g_list[0]["id"]
    assert len(g_list) == 1
    assert g_list[0]["name"] == "Test_Group"

    f_dict = session.get_feeds()
    f = f_dict["Test_Group"][0]
    assert f["group"] == g_id


def test_group_delete_feed_no_group(session):
    f = session.add_feed("Foo", "url", "homepage", group_name="Test_Group")

    feed_id = f["id"]
    g_list = session.get_groups()
    g_id = g_list[0]["id"]
    assert len(g_list) == 1
    assert g_list[0]["name"] == "Test_Group"

    session.delete_group(g_id)

    g_list = session.get_groups()
    assert len(g_list) == 0

    f_dict = session.get_feeds()
    f = f_dict[None][0]
    assert f["id"] == feed_id
    assert "Test_Group" not in f_dict
