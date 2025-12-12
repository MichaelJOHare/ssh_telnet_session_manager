from __future__ import annotations

from ..ansi import Ansi, clear_screen
from ..prompting import SelectionBack, SelectionExit, SelectionInvalid, SelectionOk, prompt_selection
from ..transport_menu import select_transport
from ..config_utils import GROUP_DELIMITER, load_host_aliases, split_hosts_by_group
from .vmsmenu_utils import attempt_connection, render_menu


# TODO: refactor return codes
def run_vmsmenu() -> int:
    last_msg = [""]

    transport = select_transport()
    if transport is None:
        clear_screen()
        return 0

    hosts = load_host_aliases(transport.config_file)
    if not hosts:
        print(f"No hosts found in {transport.config_file}")
        return 1

    main_hosts, group_map, group_names = split_hosts_by_group(hosts)

    labels: list[str] = []
    types: list[str] = []
    values: list[str] = []

    for h in main_hosts:
        labels.append(h.upper())
        types.append("host")
        values.append(h)

    for g in group_names:
        labels.append(g.upper())
        types.append("group")
        values.append(g)

    main_title = f"VMS {transport.label.upper()}"
    main_subtitle = (
        f"Select a {Ansi.GREEN}host{Ansi.RESET} to connect to "
        f"or a {Ansi.ORANGE}group{Ansi.RESET} to open its menu:"
    )

    while True:
        msg = last_msg[0]
        last_msg[0] = ""
        render_menu(main_title, main_subtitle, labels, types=types, message=msg)

        print()
        sel = prompt_selection(
            f"Enter number (or {Ansi.RED}E{Ansi.RESET} to exit): ",
            max_value=len(labels),
            allow_back=False,
        )

        match sel:
            case SelectionExit():
                clear_screen()
                return 0
            case SelectionInvalid() | SelectionBack():
                last_msg[0] = f"Invalid selection, enter a number between 1 and {len(labels)} or E to exit."
                continue
            case SelectionOk(value=n):
                idx = n - 1
        if types[idx] == "host":
            if attempt_connection(values[idx], transport, last_msg_out=last_msg):
                return 0
            continue

        # group menu
        group = values[idx]
        group_entries = group_map.get(group, [])
        if not group_entries:
            last_msg[0] = f"No hosts in group {group.upper()}"
            continue

        group_labels: list[str] = []
        group_values: list[str] = []
        for host_item in group_entries:
            display = host_item.split(GROUP_DELIMITER, 1)[1] if GROUP_DELIMITER in host_item else host_item
            group_labels.append(display.upper())
            group_values.append(host_item)

        group_title = "GROUP"
        group_subtitle = f"{Ansi.ORANGE}{group.upper()} CLUSTER{Ansi.RESET} - select {Ansi.GREEN}host{Ansi.RESET}:"

        while True:
            msg2 = last_msg[0]
            last_msg[0] = ""
            render_menu(group_title, group_subtitle, group_labels, message=msg2)

            print()
            sel2 = prompt_selection(
                f"Enter number ({Ansi.MAGENTA}B{Ansi.RESET} to go back or {Ansi.RED}E{Ansi.RESET} to exit): ",
                max_value=len(group_labels),
                allow_back=True,
            )

            match sel2:
                case SelectionExit():
                    clear_screen()
                    return 0
                case SelectionBack():
                    break
                case SelectionInvalid():
                    last_msg[0] = (
                        f"Invalid selection, enter a number between 1 and {len(group_labels)}, "
                        "B to go back, or E to exit."
                    )
                    continue
                case SelectionOk(value=n2):
                    chosen_host = group_values[n2 - 1]
            if attempt_connection(chosen_host, transport, last_msg_out=last_msg):
                return 0


if __name__ == "__main__":
    raise SystemExit(run_vmsmenu())
