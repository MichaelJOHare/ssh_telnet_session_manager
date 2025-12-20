from __future__ import annotations

from pathlib import Path

from .ansi import Ansi, clear_screen
from .config_utils import GROUP_DELIMITER, load_host_aliases, read_host_values, categorize_hosts, remove_host_entry
from .transport_menu import select_transport
from .types import HostAction, MenuVars, Transport
from .prompting import SelectionBack, SelectionExit, SelectionInvalid, SelectionOk, prompt_selection, prompt_text


_RC_EXIT = 0
_RC_BACK = 1


def _build_menu_lists(
        main_hosts: list[str], 
        group_names: list[str]
) -> tuple[list[str], list[str], list[str]]:
    labels: list[str] = []
    types: list[str] = []
    values: list[str] = []

    for host in main_hosts:
        labels.append(host.upper())
        types.append("host")
        values.append(host)

    for group in group_names:
        labels.append(group.upper())
        types.append("group")
        values.append(group)

    return labels, types, values


def _clear_menu_vars(menu_vars: MenuVars) -> None:
    menu_vars.main_hosts = []
    menu_vars.group_map = {}
    menu_vars.group_names = []
    menu_vars.labels = []
    menu_vars.types = []
    menu_vars.values = []


def _populate_menu_vars(menu_vars: MenuVars, *, hosts: list[str]) -> bool:
    if not hosts:
        _clear_menu_vars(menu_vars)
        return False

    categorized = categorize_hosts(hosts)
    menu_vars.main_hosts = categorized.main_hosts
    menu_vars.group_map = categorized.group_map
    menu_vars.group_names = categorized.group_names

    labels, types, values = _build_menu_lists(menu_vars.main_hosts, menu_vars.group_names)
    menu_vars.labels = labels
    menu_vars.types = types
    menu_vars.values = values
    return True


def _refresh_menu(menu_vars: MenuVars) -> bool:
    hosts = load_host_aliases(menu_vars.transport.config_file)
    return _populate_menu_vars(menu_vars, hosts=hosts)


def setup_menu() -> MenuVars | None:
    transport = select_transport()
    if transport is None:
        clear_screen()
        return None

    hosts = load_host_aliases(transport.config_file)
    if not hosts:
        print(f"{Ansi.RED}No hosts found in {transport.config_file}{Ansi.RESET}")
        return None

    categorized = categorize_hosts(hosts)
    main_hosts, group_map, group_names = (
        categorized.main_hosts,
        categorized.group_map,
        categorized.group_names,
    )

    labels, types, values = _build_menu_lists(main_hosts, group_names)

    return MenuVars(
        main_hosts=main_hosts,
        group_map=group_map,
        group_names=group_names,
        labels=labels,
        types=types,
        values=values,
        transport=transport
    )


# render the menu with title, subtitle, labels, optional types, and optional message
def render_menu(
        title: str, 
        subtitle: str, 
        labels: list[str], 
        *, 
        types: list[str] | None = None, 
        message: str = ""
) -> None:
    clear_screen()
    print(f"\n------------------------{title}------------------------\n")
    if subtitle:
        print(f"{subtitle}\n")

    for idx, label in enumerate(labels, start=1):
        kind = (types[idx - 1] if types else "")
        if kind == "group":
            print(f"{idx}) {Ansi.ORANGE}{label} CLUSTER{Ansi.RESET}")
        else:
            print(f"{idx}) {Ansi.GREEN}{label}{Ansi.RESET}")

    if message:
        print(f"\n{Ansi.RED}{message}{Ansi.RESET}")


# main connect menu loop, returns 0 on successful connection or exit
def main_menu(
    last_msg: list[str],
    main_title: str,
    main_subtitle: str,
    menu_vars: MenuVars,
    *,
    on_host_selected: HostAction,
    refresh_menu: bool = True,
) -> int:
    while True:
        if refresh_menu:
            if not _refresh_menu(menu_vars):
                last_msg[0] = f"No hosts found in {menu_vars.transport.config_file}"
                clear_screen()
                return _RC_EXIT

        msg = last_msg[0]
        last_msg[0] = ""
        render_menu(main_title, main_subtitle, menu_vars.labels, types=menu_vars.types, message=msg)

        print()
        sel = prompt_selection(
            f"Enter number (or {Ansi.RED}E{Ansi.RESET} to exit): ",
            max_value=len(menu_vars.labels),
            allow_back=False,
        )

        match sel:
            case SelectionExit():
                clear_screen()
                return _RC_EXIT
            case SelectionInvalid() | SelectionBack():
                last_msg[0] = f"Invalid selection, enter a number between 1 and {len(menu_vars.labels)} or E to exit."
                continue
            case SelectionOk(value=n):
                idx = n - 1
        if menu_vars.types[idx] == "host":
            if on_host_selected(menu_vars.values[idx], menu_vars.transport, last_msg_out=last_msg):
                return _RC_EXIT
            continue
        result = group_menu(last_msg, idx, menu_vars, on_host_selected=on_host_selected)
        if result == _RC_EXIT:
            return _RC_EXIT

# group menu loop, returns 0 on successful connection, 1 to go back to main menu
def group_menu(
    last_msg: list[str],
    idx: int,
    menu_vars: MenuVars,
    *,
    on_host_selected: HostAction,
) -> int:
    group = menu_vars.values[idx]
    group_entries = menu_vars.group_map.get(group, [])
    if not group_entries:
        last_msg[0] = f"No hosts in group {group.upper()}"
        return _RC_EXIT

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
                return _RC_EXIT
            case SelectionBack():
                return _RC_BACK
            case SelectionInvalid():
                last_msg[0] = (
                    f"Invalid selection, enter a number between 1 and {len(group_labels)}, "
                    "B to go back, or E to exit."
                )
                continue
            case SelectionOk(value=n2):
                chosen_host = group_values[n2 - 1]
        if on_host_selected(chosen_host, menu_vars.transport, last_msg_out=last_msg):
            return _RC_EXIT
        

def add_or_list_menu(
    config_file: Path,
    menu_vars: MenuVars,
    last_msg: list[str],
) -> tuple[bool, str | None]:
    while True:
        clear_screen()
        print("\n-----------------ADD OR LIST HOSTS--------------------\n")
        print(f"1) {Ansi.MAGENTA}Add{Ansi.RESET} or edit {Ansi.GREEN}hosts{Ansi.RESET}")
        print(f"2) {Ansi.MAGENTA}List{Ansi.RESET} existing {Ansi.GREEN}hosts{Ansi.RESET}")
        sel = prompt_text(f"\nEnter selection (or {Ansi.RED}E{Ansi.RESET} to exit) [{Ansi.GREEN}1{Ansi.RESET}]: ").strip()
        if sel in ("", "1"):
            return True, None
        if sel == "2":
            menu_title = "EXISTING HOSTS"
            menu_subtitle = f"Listing hosts in configuration file: {Ansi.MAGENTA}{config_file}{Ansi.RESET}"
            menu_subtitle += f"\n\nSelect a host to view details, or {Ansi.RED}E{Ansi.RESET} to exit back to main menu"
            edit_host_out: list[str] = [""]

            def _on_host_selected(host_label: str, transport: Transport, *, last_msg_out: list[str]) -> bool:
                return show_host_details(
                    host_label,
                    transport,
                    last_msg_out=last_msg_out,
                    edit_host_out=edit_host_out,
                )

            main_menu(
                last_msg,
                menu_title,
                menu_subtitle,
                menu_vars=menu_vars,
                on_host_selected=_on_host_selected,
            )
            if edit_host_out[0]:
                return True, edit_host_out[0]
        if sel.lower() == "e":
            clear_screen()
            return False, None
        print(f"{Ansi.RED}Invalid selection.{Ansi.RESET}")


def show_host_details(
    host_label: str,
    transport: Transport,
    *,
    last_msg_out: list[str],
    edit_host_out: list[str] | None = None,
) -> bool:
    hostname, port, hostkey, kex, macs = read_host_values(host_label, transport.config_file)

    clear_screen()
    print("\n---------------------HOST DETAILS---------------------\n")
    print(f"Host: {format_host_display(host_label)}\n\n")
    format_host_details(hostname, port, hostkey, kex, macs)

    prompt_display = f"\nType {Ansi.GREEN}E{Ansi.RESET} to edit "
    prompt_display += f"or {Ansi.MAGENTA}B{Ansi.RESET} to go back to the previous menu."
    prompt_display += f"\nOr type {Ansi.RED}DELETE{Ansi.RESET} to remove this host entry: "
    resp = prompt_text(prompt_display)
    if resp.strip().upper() == "DELETE":
        remove_host_entry(host_label, transport.config_file)
        last_msg_out[0] = f"Host {host_label.upper()} deleted."
        return False
    if resp.strip().lower() == "e":
        if edit_host_out is not None:
            edit_host_out[0] = host_label
        return True
    last_msg_out[:] = [""]
    return False


def format_host_details(hostname: str, port: str, hostkey: str, kex: str, macs: str) -> None:
    print(f"  Hostname/IP: {Ansi.MAGENTA}{hostname}{Ansi.RESET}")
    print(f"  Port: {Ansi.MAGENTA}{port or '<default>'}{Ansi.RESET}\n")
    print(format_algo_display(hostkey, 'Host Key Algorithm'))
    print(format_algo_display(kex, 'Key Exchange Algorithms'))
    print(format_algo_display(macs, 'MAC Algorithms'))
    print()


def format_host_display(host: str, *, delimiter: str=GROUP_DELIMITER) -> str:
    if delimiter in host:
        group, member = host.split(GROUP_DELIMITER, 1)
        return f"{Ansi.ORANGE}{group.upper()}{Ansi.RESET} {Ansi.GREEN}{member.upper()}{Ansi.RESET}"
    return f"{Ansi.GREEN}{host.upper()}{Ansi.RESET}"


def format_algo_display(value: str, label: str) -> str:
    display = value if value else "<default>"
    if display == "<default>":
        return f"  {label}: {Ansi.ORANGE}{display}{Ansi.RESET}"
    return f"  {label}: {Ansi.MAGENTA}{display}{Ansi.RESET}"