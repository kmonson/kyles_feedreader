from asciimatics.widgets import Frame, Layout, ListBox, Widget
from ..db_interface import NO_GROUP_TUPLE

class FeedListView(Frame):
    def __init__(self, screen, on_select=None):
        super().__init__(screen,
                         screen.height-2,
                         max(min(screen.width // 8, 48), 16),
                         x=0,
                         reduce_cpu=True,
                         title="Feeds")

        layout = Layout([100], fill_frame=True)
        self.add_layout(layout)
        self.list_box = ListBox(Widget.FILL_FRAME,
                                [],
                                name="feeds",
                                on_select=on_select)
        layout.add_widget(self.list_box)
        self.fix()

    def update_feed_list(self, feed_dict):
        options = []
        no_group = feed_dict.pop(NO_GROUP_TUPLE, {"feeds": list(), "unreads": False})
        options.append(("All", ("all",)))
        options.append(("Starred", ("starred",)))
        for (name, _id), feeds in feed_dict.items():
            options.append(("-"+name, ("group", _id)))
            options.extend(self.build_options(feeds, prefix=" "))
        options.extend(self.build_options(no_group))

        self.list_box.options = options

    @staticmethod
    def build_options(feeds, prefix=""):
        options = []
        for item in feeds["feeds"]:
            options.append((prefix+item["name"], ("feed", item["id"])))
        return options




class FeedItemView:
    pass
