from kyles_feedreader.view.feed_browser import FeedListView
from kyles_feedreader.db_interface import get_feeds_by_group
from typing import Optional, Tuple
from . import BaseController, Scenes


class FeedListController(BaseController):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = get_feeds_by_group()
        self.view: Optional[FeedListView] = None

    def refresh(self):
        self.state = get_feeds_by_group()
        if self.view is not None:
            self.view.update_feed_list(self.state.copy())

    def build_view(self, screen) -> Tuple[str, FeedListView]:
        data = self.view.data if self.view is not None else None
        self.view = FeedListView(screen)
        self.view.update_feed_list(self.state.copy())
        self.view.data = data
        return Scenes.FEED_BROWSER.value, self.view



