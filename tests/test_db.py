import pytest
from kyles_feedreader import db_interface as dbi
from datetime import timedelta


@pytest.fixture
def session():
    yield dbi.DBInterface(":memory:")


def test_add_group(session):
    g = session.add_find_group("Foo", session.root_group)
    assert g.name == "Foo"

    g_list = session.get_groups(session.root_group)
    assert len(g_list) == 1
    assert g_list[0].name == "Foo"


def test_delete_group_with_id(session):
    g = session.add_find_group("Foo", session.root_group)
    g_id = g.id

    g_list = session.get_groups(session.root_group)
    assert len(g_list) == 1

    session.delete_group(g_id)

    g_list = session.get_groups(session.root_group)
    assert len(g_list) == 0


def test_delete_group_with_data(session):
    g = session.add_find_group("Foo", session.root_group)

    g_list = session.get_groups(session.root_group)
    assert len(g_list) == 1

    session.delete_group(g)

    g_list = session.get_groups(session.root_group)
    assert len(g_list) == 0


def test_add_feed(session):
    f = session.add_feed("Foo", "url", "homepage", session.root_group)
    assert f.name == "Foo"
    assert f.url == "url"
    assert f.home_page == "homepage"
    assert f.group == session.root_group.id
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
    assert f.group == session.root_group.id
    assert f.update_rate == timedelta(hours=1)
    assert f.last_update is None
    assert f.etag is None
    assert f.last_modified is None
    assert f.id == feed_id

    # Test duplicate add
    with pytest.raises(ValueError, match="Feed already exists"):
        session.add_feed("Foo", "url", "homepage", session.root_group)


def test_delete_feed(session):
    f = session.add_feed("Foo", "url", "homepage", session.root_group)
    session.delete_feed(f)
    f_list = session.get_feeds()
    assert not f_list


def test_update_feed(session):
    f = session.add_feed("Foo", "url", "homepage", session.root_group)

    feed_id = f.id

    session.update_feed(f, home_page="homepage2", update_rate=timedelta(hours=2))

    f_list = session.get_feeds()
    f = f_list[0]
    assert f.name == "Foo"
    assert f.url == "url"
    assert f.home_page == "homepage2"
    assert f.group == session.root_group.id
    assert f.update_rate == timedelta(hours=2)
    assert f.last_update is None
    assert f.etag is None
    assert f.last_modified is None
    assert f.id == feed_id


def test_group_delete_recurse(session):
    g = session.add_find_group("Test_Group", session.root_group)
    session.add_feed("Foo", "url", "homepage", g)

    session.delete_group(g, recursive=True)

    g_list = session.get_groups(session.root_group)
    assert len(g_list) == 0
    f_list = session.get_feeds(session.root_group)
    assert len(f_list) == 0


def test_group_delete_no_recurse(session):
    g = session.add_find_group("Test_Group", session.root_group)
    f = session.add_feed("Foo", "url", "homepage", g)
    feed_id = f.id

    session.delete_group(g, recursive=False)

    g_list = session.get_groups(session.root_group)
    assert len(g_list) == 0

    f_list = session.get_feeds(session.root_group)
    assert len(f_list) == 1
    f2 = f_list[0]
    assert f2.id == feed_id


def test_add_feed_items(session):
    f = session.add_feed("Foo", "url", "homepage", session.root_group)

    items = [
        {"title": "Foo1", "url": "Foo1URL"},
        {"title": "Foo2", "url": "Foo2URL"}
    ]
    session.add_feed_items(f, items)

    def test(fi_test):
        assert fi_test[0].url == "Foo2URL"
        assert fi_test[0].title == "Foo2"
        assert fi_test[0].read is False
        assert fi_test[0].viewed is False

        assert fi_test[1].url == "Foo1URL"
        assert fi_test[1].title == "Foo1"
        assert fi_test[1].read is False
        assert fi_test[1].viewed is False

    fi = session.get_feed_items(f)
    test(fi)

    fi = session.get_all_feed_items(f)
    test(fi)

    fi = session.get_group_feed_items(session.root_group)
    test(fi)


def test_all_viewed_items(session):
    f = session.add_feed("Foo", "url", "homepage", session.root_group)

    items = [
        {"title": "Foo1", "url": "Foo1URL"},
        {"title": "Foo2", "url": "Foo2URL"}
    ]
    session.add_feed_items(f, items)
    fi = session.get_feed_items(f)

    assert fi[0].viewed is False
    assert fi[1].viewed is False

    session.mark_all_items_viewed()

    fi = session.get_feed_items(f)

    assert fi[0].viewed is True
    assert fi[1].viewed is True

    assert not session.any_has_unviewed_feed_items()


def test_group_viewed_items(session):
    g = session.add_find_group("Test_Group", session.root_group)
    f1 = session.add_feed("Foo1", "url1", "homepage", g)
    f2 = session.add_feed("Foo2", "url2", "homepage", session.root_group)

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

    session.mark_group_items_viewed(g)

    fi1 = session.get_feed_items(f1)
    fi2 = session.get_feed_items(f2)

    assert fi1[0].viewed is True
    assert fi2[0].viewed is False

    session.mark_group_items_viewed(session.root_group)

    fi1 = session.get_feed_items(f1)
    fi2 = session.get_feed_items(f2)

    assert fi1[0].viewed is True
    assert fi2[0].viewed is True


def test_has_unviewed(session):
    f = session.add_feed("Foo", "url", "homepage", session.root_group)

    items = [
        {"title": "Foo1", "url": "Foo1URL"},
        {"title": "Foo2", "url": "Foo2URL"}
    ]
    session.add_feed_items(f, items)

    assert session.any_has_unviewed_feed_items()

    session.mark_feed_items_viewed(f)

    assert not session.any_has_unviewed_feed_items()


def test_unread_interface(session):
    g = session.add_find_group("Test_Group", session.root_group)
    f0 = session.add_feed("Foo0", "url0", "homepage", g)
    f1 = session.add_feed("Foo1", "url1", "homepage", g)
    f2 = session.add_feed("Foo2", "url2", "homepage", session.root_group)
    f3 = session.add_feed("Foo3", "url3", "homepage", session.root_group)

    fl = [f0, f1, f2, f3]
    gl = [g, session.root_group]

    for i, f in enumerate(fl):
        items = [{"title": f"Foo{i}{n}", "url": f"Foo{i}{n}URL"} for n in range(3)]
        session.add_feed_items(f, items)

    for f in fl:
        assert len(session.get_feed_items(f, unread_only=True)) == 3

    for g in gl:
        assert len(session.get_group_feed_items(g, unread_only=True)) == 6

    assert len(session.get_all_feed_items(unread_only=True)) == 12


    # assert not session.get_feed_items(f, unread_only=True)
    # assert not session.get_all_feed_items(unread_only=True)
    # assert not session.get_group_feed_items(session.root_group, unread_only=True)


