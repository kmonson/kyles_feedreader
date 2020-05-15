import gevent
import time
from asciimatics.screen import Screen
from asciimatics.scene import Scene
from asciimatics.effects import Cycle, Stars
from asciimatics.renderers import FigletText
from asciimatics.exceptions import StopApplication


def main_loop():
    screen = None
    while True:
        if screen is None or screen.has_resized():
            if screen is not None:
                screen.close(False)
            screen = Screen.open()
            effects = create_effect(screen)
            screen.set_scenes([Scene(effects, 500)])
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


def main():
    # Define the scene that you'd like to play.
    loop = gevent.spawn(main_loop)
    loop.join()


if __name__ == "__main__":
    main()
