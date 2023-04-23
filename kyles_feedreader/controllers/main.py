from collections import defaultdict
from typing import List

from asciimatics.screen import Screen
from asciimatics.scene import Scene

from .feed_list import FeedListController
from . import BaseController


class MainController:
    def __init__(self):
        self.feed_list = FeedListController()
        self.browser_controllers: List[BaseController] = [self.feed_list]
        self.all_controllers: List[BaseController] = self.browser_controllers

    def build_ui(self, screen: Screen, current_scene: str):
        view_dict = defaultdict(list)
        for con in self.browser_controllers:
            scene_name, view = con.build_view(screen)
            view_dict[scene_name].append(view)
        scenes = [Scene(views, -1, name=name) for (name, views) in view_dict.items()]
        screen.set_scenes(scenes, start_scene=current_scene)

    def refresh(self):
        for con in self.all_controllers:
            con.refresh()
