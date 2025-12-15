from __future__ import annotations

import sys


class Ansi:
    GREEN = "\033[0;32m"
    RED = "\033[0;31m"
    MAGENTA = "\033[0;35m"
    ORANGE = "\033[38;5;208m"
    YELLOW = "\033[0;33m"
    RESET = "\033[0m"


def clear_screen() -> None:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def set_title(title: str) -> None:
    # xterm title escape
    sys.stdout.write(f"\033]0;{title}\007")
    sys.stdout.flush()
