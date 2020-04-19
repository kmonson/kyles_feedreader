# By Kyle Monson

import click
import pathlib
import xml.etree.ElementTree as ET

from . import db_interface, defaults
from .feed_parsing import parse_feed, ResultType


@click.group()
@click.option("--db-path", default=defaults.db_path, type=click.Path(dir_okay=False, resolve_path=True))
# @click.option("--config-path", default=defaults.config_path)
def cli(db_path, config_path=None):
    pathlib.Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    db_interface.initialize_sql(db_path)


def _add_from_url(url, group=None):
    r, f = parse_feed(url)
    if r & (ResultType.HTTP_ERROR | ResultType.AUTH_ERROR):
        click.echo(f"Error: {f['status'].phrase}, {f['status'].description}")
        return

    if ResultType.ERROR in r:
        click.echo(f"Error: {f['error']}")
        return

    if ResultType.PERMANENT_REDIRECT in r:
        new_url = f["new_url"]
        click.echo(f"Automatically redirecting to new URL: {new_url}")
        url = new_url

    name = f["name"]
    db_f = db_interface.add_get_feed(name, url, f["home_page"], group_name=group)

    feed_id = db_f["id"]

    db_interface.update_feed(feed_id, etag=f["etag"], last_modified=f["modified"])

    db_interface.add_feed_items(feed_id, f["entries"])


@cli.command()
@click.option("--group")
@click.argument("urls", nargs=-1)
def add(urls, group=None):
    """Add feeds specified at URLS to feed db."""
    for url in urls:
        _add_from_url(url, group)


@cli.command()
@click.argument("names")
def add_group(names):
    """Add groups specified by NAMES to feed db."""
    for name in names:
        try:
            db_interface.add_group(name)
            click.echo(f"Created {name}")
        except ValueError as e:
            click.echo(str(e))



@cli.command()
@click.argument("urls", nargs=-1)
def delete(urls):
    """Delete feeds specified at URLS from feed db."""
    urls = set(urls)
    for url in urls:
        db_interface.delete_feed(url)


@cli.command()
@click.argument("names", nargs=-1)
def delete_group(names):
    """Delete groups specified by NAMES from feed db."""
    names = set(names)
    for name in names:
        db_interface.delete_group(name)


@cli.command()
def update():
    """Update all feeds in feed db.."""
    feeds = db_interface.get_flat_feeds()
    for feed in feeds:
        url = feed["url"]
        name = feed['name']

        r, f = parse_feed(url, etag=feed['etag'], modified=feed['last_modified'])

        if r & (ResultType.HTTP_ERROR | ResultType.AUTH_ERROR):
            click.echo(f"Error getting {url}: {f['status'].phrase}, {f['status'].description}")
            continue

        if ResultType.ERROR in r:
            click.echo(f"Error getting {url}: {f['error']}")
            continue

        if ResultType.PERMANENT_REDIRECT in r:
            feed_id = f["id"]
            new_url = f["new_url"]
            click.echo(f"Updating {name} to new URL: {new_url}")
            try:
                db_interface.update_feed(feed_id, url=new_url)
            except ValueError as e:
                click.echo(f"Updating {name} URL failed: {str(e)}")
                continue

        feed_id = feed["id"]

        if ResultType.NOT_MODIFIED in r:
            db_interface.update_feed_last_update(feed_id)
            continue

        db_interface.update_feed(feed_id, etag=f["etag"], last_modified=f["modified"])
        new_items = db_interface.add_feed_items(feed_id, f["entries"])
        if new_items:
            click.echo(f"Added {len(new_items)} items to {name}")


def print_feed_list(feed_list, verbose):
    for feed in feed_list:
        click.echo(f"\t{feed['name']} Updated: {feed['last_update']}")
        click.echo(f"\t Homepage: {feed['home_page']}")
        click.echo(f"\t URL: {feed['url']}")
        if verbose:
            for item in db_interface.get_feed_items(feed["id"]):
                click.echo(f"\t\t{item['title']}")
                click.echo(f"\t\t Timestamp: {item['timestamp']}")
                click.echo(f"\t\t URL: {item['url']}")
                click.echo(f"\t\t Enclosure: {item['enclosure_url']}")
                click.echo(f"\t\t Read: {item['read']}")


@cli.command(name="list")
@click.option("-v", "--verbose", is_flag=True)
def list_(verbose):
    """List all feeds, sorted by group."""
    feeds = db_interface.get_feeds()
    no_group = feeds.pop(None, [])
    for group, feed_list in feeds.items():
        click.echo(group, color="green")
        print_feed_list(feed_list, verbose)

    click.echo("No Group", color="green")
    print_feed_list(no_group, verbose)


@cli.command(name="import")
@click.argument("files", nargs=-1, type=click.Path(dir_okay=False, resolve_path=True, exists=True))
def import_(files):
    """Import OPML file."""
    def add_feeds(feeds, group_name=None):
        for f in feeds:
            feed_name = f.attrib.get("text")
            url = f.attrib.get("xmlUrl")
            click.echo(f"Adding feed {feed_name} at {url}")
            _add_from_url(url, group_name)

    for path in files:
        tree = ET.parse(path)
        root = tree.getroot()
        groups = root.findall(".//outline/..[@text]")
        for g in groups:
            group_name = g.attrib.get("text")
            click.echo(f"Processing Group {group_name}")
            feeds = g.findall("./outline")
            add_feeds(feeds, group_name)

        click.echo("Processing ungrouped feeds")
        feeds = root.findall("./body/outline/[@xmlUrl]")
        add_feeds(feeds)


if __name__ == "__main__":
    cli()
