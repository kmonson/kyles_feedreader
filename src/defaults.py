# By Kyle Monson

from datetime import timedelta
from pathlib import Path
import click


_app_dir_path = Path(click.get_app_dir("kyles_feedreader", roaming=False))

db_path = str(_app_dir_path / "db.sqlite")
config_path = str(_app_dir_path / "config.yaml")

update_rate = timedelta(hours=1)
