import abc
from enum import Enum, auto
from asciimatics.widgets import Frame
from asciimatics.screen import Screen
from asciimatics.scene import Scene
from typing import Tuple, List



class Scenes(Enum):
    FEED_BROWSER = auto()
    FEED_EDITOR = auto()
    FEED_DETAIL = auto()


class BaseController(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def refresh(self):
        """Called when model is updated"""
        pass

    @abc.abstractmethod
    def build_view(self, screen) -> Tuple[str, Frame]:
        """Called when a view needs to be built or rebuilt"""
        pass




