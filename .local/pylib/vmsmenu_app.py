from __future__ import annotations

from .connection import attempt_connection
from .menu_utils import setup_menu
from .ansi import Ansi
from .menu_utils import main_menu


def run_vmsmenu() -> int:
    last_msg = [""]

    menu_vars = setup_menu()
    if menu_vars is None:
        return 0

    main_title = f"{Ansi.GREEN}{menu_vars.transport.label.upper()}{Ansi.RESET} HOSTS"
    main_subtitle = (
        f"Select a {Ansi.GREEN}host{Ansi.RESET} to connect to "
        f"or a {Ansi.ORANGE}group{Ansi.RESET} to open its menu:"
    )

    rc = main_menu(
        last_msg,
        main_title,
        main_subtitle,
        menu_vars,
        on_host_selected=attempt_connection,
        refresh_menu=False,
    )
    return rc
