# By Kyle Monson

import string

import click
import textwrap
from lxml import etree, objectify
from . import db_interface, defaults
from .feed_parsing import parse_feed, ResultType


text_wrapper = textwrap.TextWrapper()


@click.group()
@click.option("--db-path", default=defaults.db_path, type=click.Path(dir_okay=False, resolve_path=True))
# @click.option("--config-path", default=defaults.config_path)
def cli(db_path, config_path=None):
    db_interface.initialize_sql(db_path)
    pass


def _add_from_url(url: str, group: db_interface.GroupData):
    r, f = parse_feed(url)
    if r & (ResultType.HTTP_ERROR | ResultType.AUTH_ERROR):
        click.echo(f"Error: {f['status'].phrase}, {f['status'].description}")
        return

    if ResultType.ERROR in r:
        click.echo(f"Error: {f['error']}")
        return

    if ResultType.PERMANENT_REDIRECT in r:
        url = f["new_url"]
        click.echo(f"Automatically redirecting to new URL: {url}")

    name = f["name"]

    if db_interface.find_feed_from_url(url) is None:
        db_f = db_interface.add_feed(name, url, f["home_page"], group_data=group)

        db_interface.update_feed(db_f, etag=f["etag"], last_modified=f["modified"])

        db_interface.add_feed_items(db_f, f["entries"])
    else:
        click.echo(f"Skipping {name}: added previously.")


@cli.command()
@click.option("-g", "--group")
@click.argument("urls", nargs=-1)
def add(urls, group=None):
    """Add feeds specified at URLS to feed db."""
    group_data, _ = parse_path(group)
    for url in urls:
        _add_from_url(url, group_data)


def parse_path(group_path: str | None, parse_all: bool = True) -> tuple[db_interface.GroupData, str | None]:
    current = db_interface.root_group
    parts = [] if group_path is None else group_path.strip(string.whitespace + "/").split("/")
    if not parts:
        return current, None

    if parse_all:
        name = None
        path = parts
    else:
        name = parts[-1]
        path = parts[:-1]

    for part in path:
        current = db_interface.find_group_by_name(part, current)
        if current is None:
            raise click.BadParameter(f"Group {part} does not exist")

    return current, name


@cli.command()
@click.argument("group_path")
def add_group(group_path: str):
    """Add group specified by '/' delimited PATH to feed db."""
    parent, name = parse_path(group_path, parse_all=False)
    group = db_interface.find_group_by_name(name, parent)

    if not group:
        db_interface.add_find_group(name, parent)
    else:
        click.echo(f"Group {name} already exists")


@cli.command()
@click.argument("group_path")
@click.option('-r', '--recursive', is_flag=True, help="Delete all child groups and feeds. Otherwise all chidren are moved to the parent group.")
def delete_group(group_path: str, recursive: bool):
    """Delete group specified by PATH from feed db."""
    group, _ = parse_path(group_path)
    db_interface.delete_group(group, recursive)


@cli.command()
@click.argument("urls", nargs=-1)
def delete(urls):
    """Delete feeds specified at URLS from feed db."""
    urls = set(urls)
    for url in urls:
        feed = db_interface.find_feed_from_url(url)
        if feed is None:
            click.echo(f"Cannot find {url}")
        db_interface.delete_feed(feed)


@cli.command()
def update():
    """Update all feeds in feed db.."""
    feeds = db_interface.get_feeds()
    for feed in feeds:
        url = feed.url
        name = feed.name

        click.echo(f"Getting {name}")

        r, f = parse_feed(url, etag=feed.etag, modified=feed.last_modified)

        if r & (ResultType.HTTP_ERROR | ResultType.AUTH_ERROR):
            click.echo(f"Error getting {url}: {f['status'].phrase}, {f['status'].description}")
            continue

        if ResultType.ERROR in r:
            click.echo(f"Error getting {url}: {f['error']}")
            continue

        if ResultType.PERMANENT_REDIRECT in r:
            new_url = f["new_url"]
            click.echo(f"Updating {name} to new URL: {new_url}")
            try:
                db_interface.update_feed(feed, url=new_url)
            except ValueError as e:
                click.echo(f"Updating {name} URL failed: {str(e)}")
                continue

        if ResultType.NOT_MODIFIED in r:
            db_interface.update_feed_last_update(feed)
            continue

        db_interface.update_feed(feed, etag=f["etag"], last_modified=f["modified"])
        new_items = db_interface.add_feed_items(feed, f["entries"])
        if new_items:
            click.echo(f"Added {len(new_items)} items to {name}")





@cli.command()
@click.option("-v", "--verbose", count=True)
def view(verbose):
    """Print information about groups and feeds."""
    def print_feed(feed: db_interface.FeedData, indent: int):
        lead = ' ' * indent
        yield f"{lead}{feed.name} Updated: {feed.last_update}\n"
        if verbose > 0:
            yield f"{lead} Homepage: {feed.home_page}\n"
            yield f"{lead} URL: {feed.url}\n"
            if verbose > 1:
                if feed.description:
                    yield f"{lead} Description: {feed.description}\n"
                for item in db_interface.get_feed_items(feed):
                    yield from print_feed_item(item, indent+1)

    def print_feed_item(item: db_interface.FeedItemData, indent: int):
        lead = ' ' * indent
        yield f"{lead}{item.title}\n"
        if item.timestamp is not None:
            yield f"{lead} Timestamp: {item.timestamp}\n"
        yield f"{lead} URL: {item.url}\n"
        if item.enclosure_url:
            yield f"{lead} Enclosure: {item.enclosure_url}\n"
        yield f"{lead} Read: {item.read}\n"
        if verbose > 2:
            if item.text is not None:
                text_wrapper.initial_indent = text_wrapper.subsequent_indent = lead
                yield text_wrapper.fill(item.text) + "\n"

    def print_group(group_data: db_interface.GroupData, indent=0):
        yield f"{' '*indent}{group_data.name if group_data.name is not None else ''}\n"
        children = db_interface.get_groups(group_data)
        for child in children:
            yield from print_group(child, indent+1)
        for feed_data in db_interface.get_feeds(group_data):
            yield from print_feed(feed_data, indent+1)

    click.echo_via_pager(print_group(db_interface.root_group))


@cli.command(name="import")
@click.argument("files", nargs=-1, type=click.Path(dir_okay=False, resolve_path=True, exists=True))
def import_(files):
    """Import OPML file."""
    def add_element(element, path, group: db_interface.GroupData):
        children = element.iterfind("outline")
        for c in children:
            child_name = c.attrib.get("text")
            if c.attrib.get("type") == "rss":
                url = c.attrib.get("xmlUrl")
                click.echo(f"Adding feed {'/'.join(path)}/{child_name} at {url}")
                _add_from_url(url, group)
            else:
                new_path = path + (child_name,)
                click.echo(f"Creating group {'/'.join(new_path)}")
                new_group = db_interface.add_find_group(child_name, group)
                add_element(c, new_path, new_group)

    for file_path in files:
        tree = etree.parse(file_path)
        root = tree.getroot()
        root_elements = root.iterfind("./body")
        for root_element in root_elements:
            click.echo(f"Processing root element")
            add_element(root_element, (), db_interface.root_group)


if __name__ == "__main__":
    cli()
