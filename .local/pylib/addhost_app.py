from __future__ import annotations

from .ansi import Ansi, clear_screen
from .prompting import prompt_yes_no
from .types import PromptCancel, PromptInvalid, PromptOk, HostEntry
from .menu_utils import add_or_list_menu, format_host_display, setup_menu
from .config_utils import (
    load_host_aliases,
    read_host_values, 
    remove_host_entry, 
    upsert_host_entry, 
    host_entry_exists,
)
from .addhost_prompts import (
    prompt_nickname, 
    prompt_hostname, 
    prompt_port, 
    prompt_alias_change, 
    prompt_configure_algorithms,
)


def run_addhost() -> int:
    last_msg = [""]

    while True:
        menu_vars = setup_menu()
        if menu_vars is None:
            return 0
        
        transport, group_names = menu_vars.transport, menu_vars.group_names
        proceed, edit_host = add_or_list_menu(transport.config_file, menu_vars, last_msg)
        if not proceed:
            return 0

        clear_screen()
        print("\n-----------------ADD HOST MENU--------------------\n\n")

        if group_names:
            grp_disp = ", ".join(g.upper() for g in group_names)
            print(f"Existing groups: {Ansi.ORANGE}{grp_disp}{Ansi.RESET}\n")

        print(f"Editing {transport.label} configuration file: {Ansi.MAGENTA}{transport.config_file}{Ansi.RESET}\n")

        if last_msg[0]:
            print(f"{Ansi.RED}{last_msg[0]}{Ansi.RESET}\n")
            last_msg[0] = ""

        host_alias: str = edit_host or ""
        if not host_alias:
            aliases = load_host_aliases(transport.config_file)
            nickname_result = prompt_nickname(aliases, last_msg)
            match nickname_result:
                case PromptCancel():
                    clear_screen()
                    return 0
                case PromptInvalid():
                    continue
                case PromptOk(value=value):
                    host_alias = str(value)

        is_editing = False
        original_alias = ""
        hostname = ""
        port = ""
        hostkey = ""
        kex = ""
        macs = ""

        if host_alias and host_entry_exists(host_alias, transport.config_file):
            is_editing = True
            original_alias = host_alias

        if is_editing:
            hostname, port, hostkey, kex, macs = read_host_values(original_alias, transport.config_file)
            while True:
                updated_result = prompt_alias_change(original_alias, last_msg)
                match updated_result:
                    case PromptOk(value=updated):
                        host_alias = updated
                        break
                    case PromptCancel():
                        break
                    case PromptInvalid():
                        if last_msg[0]:
                            print(f"{Ansi.RED}{last_msg[0]}{Ansi.RESET}\n")
                            last_msg[0] = ""
                        continue
            if isinstance(updated_result, PromptCancel):
                continue

        while True:
            hostname_result = prompt_hostname(hostname, last_msg)
            match hostname_result:
                case PromptOk(value=hostname):
                    break
                case PromptCancel():
                    break
                case PromptInvalid():
                    if last_msg[0]:
                        print(f"{Ansi.RED}{last_msg[0]}{Ansi.RESET}\n")
                        last_msg[0] = ""
                    continue
        if isinstance(hostname_result, PromptCancel):
            continue

        while True:
            port_result = prompt_port(port, last_msg)
            match port_result:
                case PromptOk(value=port):
                    break
                case PromptCancel():
                    break
                case PromptInvalid():
                    if last_msg[0]:
                        print(f"{Ansi.RED}{last_msg[0]}{Ansi.RESET}\n")
                        last_msg[0] = ""
                    continue
        if isinstance(port_result, PromptCancel):
            continue

        if transport.key == "ssh":
            while True:
                algo_result = prompt_configure_algorithms(host_alias, hostname, port, hostkey, kex, macs, last_msg)
                match algo_result:
                    case PromptOk(value=(hostkey, kex, macs)):
                        break
                    case PromptCancel():
                        break
                    case PromptInvalid():
                        if last_msg[0]:
                            print(f"{Ansi.RED}{last_msg[0]}{Ansi.RESET}\n")
                            last_msg[0] = ""
                        continue
            if isinstance(algo_result, PromptCancel):
                continue

        if is_editing and host_alias != original_alias:
            remove_host_entry(original_alias, transport.config_file)

        entry = HostEntry(alias=host_alias, hostname=hostname, port=port, 
                          hostkey_algorithms=hostkey, kex_algorithms=kex, macs=macs)
        upsert_host_entry(entry, transport.config_file)

        print(
            f"Saved host {format_host_display(host_alias)} ("
            f"{Ansi.GREEN}{hostname}{Ansi.RESET}:{Ansi.MAGENTA}{port}{Ansi.RESET}) "
            f"to {Ansi.MAGENTA}{transport.config_file}{Ansi.RESET}"
        )

        if not prompt_yes_no("Add or edit another host?"):
            clear_screen()
            return 0