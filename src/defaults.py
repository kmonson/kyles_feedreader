# By Kyle Monson

from datetime import timedelta
from pathlib import Path
import click


app_dir_path = Path(click.get_app_dir("kyles_feedreader", roaming=False))

db_path = app_dir_path / "db.sqlite"
config_path = app_dir_path / "config.yaml"

update_rate = timedelta(hours=1)
