# By Kyle Monson

import sys
import click

from kyles_feedreader import db_interface, defaults
from .feed_parsing import parse_feed


@click.group()
@click.option("--db-path", default=defaults.db_path)
# @click.option("--config-path", default=defaults.config_path)
def cli(db_path, config_path=None):
    db_interface.initialize_sql(db_path)


@cli.command()
@click.argument("url")
@click.option("--group")
@click.option("--name")
def add(url, group=None, name=None):
    f = parse_feed(url)
    if f is None:
        click.echo("Invalid URL")
        sys.exit(1)
    if name is None:
        name = f["name"]
    try:
        db_f = db_interface.add_feed(name, url, f["home_page"], group_name=group)
    except ValueError as e:
        click.echo(str(e))
        sys.exit(1)

    feed_id = db_f["id"]

    db_interface.add_feed_items(feed_id, f["entries"])


@cli.command()
@click.argument("name")
def add_group(name):
    pass


@cli.command()
@click.argument("name")
def delete(name):
    pass


@cli.command()
@click.argument("name")
def delete_group(name):
    pass


@cli.command()
@click.option("--name")
def update(name):
    pass


def print_feed_list(feed_list, verbose):
    for feed in feed_list:
        click.echo(f"\t{feed['name']} Updated: {feed['last_update']}")
        click.echo(f"\t Homepage: {feed['home_page']}")
        click.echo(f"\t URL: {feed['url']}")
        if verbose:
            for item in db_interface.get_feed_items(feed["id"]):
                click.echo(f"\t\t{item['title']}")
                click.echo(f"\t\t URL: {item['url']}")
                click.echo(f"\t\t Enclosure: {item['enclosure_url']}")
                click.echo(f"\t\t Read: {item['read']}")


@cli.command(name="list")
@click.option("-v", "--verbose", is_flag=True)
def list_(verbose):
    feeds = db_interface.get_feeds()
    print(feeds)
    no_group = feeds.pop(None, [])
    for group, feed_list in feeds.items():
        click.echo(group, color="green")
        print_feed_list(feed_list, verbose)

    click.echo("No Group", color="green")
    print_feed_list(no_group, verbose)


if __name__ == "__main__":
    cli()
