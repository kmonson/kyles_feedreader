import gevent

from asciimatics.screen import Screen
from asciimatics.effects import Cycle, Stars
from asciimatics.renderers import FigletText
from asciimatics.exceptions import StopApplication

import click

from .controllers.main import MainController
from . import db_interface, defaults


def main_loop(controller):
    screen = None
    while True:
        if screen is None or screen.has_resized():
            if screen is not None:
                screen.close(False)
            screen = Screen.open()
            controller.build_ui(screen, None)
            # effects = create_effect(screen)
            # screen.set_scenes([Scene(effects, 500)])
        try:
            screen.draw_next_frame()
        except StopApplication:
            screen.close(True)
            break
        gevent.sleep(0.05)


def create_effect(screen):
    effects = [
        Cycle(
            screen,
            FigletText("ASCIIMATICS", font='big'),
            screen.height // 2 - 8),
        Cycle(
            screen,
            FigletText("ROCKS!", font='big'),
            screen.height // 2 + 3),
        Stars(screen, (screen.width + screen.height) // 2)
    ]

    return effects


@click.command()
@click.option("--db-path", default=defaults.db_path, type=click.Path(dir_okay=False, resolve_path=True))
def main(db_path):
    db_interface.initialize_sql(db_path)
    controller = MainController()
    loop = gevent.spawn(main_loop, controller)
    loop.join()


if __name__ == "__main__":
    main()
