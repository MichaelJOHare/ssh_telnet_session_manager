from __future__ import annotations

from ..ansi import Ansi, clear_screen
from ..prompting import prompt_yes_no
from ..transport_menu import select_transport
from ..types import PromptCancel, PromptInvalid, PromptOk
from ..config_utils import (
    HostEntry, 
    list_groups, 
    read_host_values, 
    remove_host_entry, 
    upsert_host_entry, 
    host_entry_exists
)
from .addhost_utils import (
    add_or_list_menu, 
    prompt_nickname, 
    prompt_hostname, 
    prompt_port, 
    prompt_alias_change, 
    prompt_configure_algorithms, 
    format_host_display,
)


def run_addhost() -> int:
    last_msg = [""]

    transport = select_transport()
    if transport is None:
        clear_screen()
        return 0

    if not add_or_list_menu(transport.config_file, last_msg):
        return 0

    while True:
        clear_screen()
        print("\n-----------------ADD HOST MENU--------------------\n\n")

        groups = list_groups(transport.config_file)
        if groups:
            grp_disp = ", ".join(g.upper() for g in groups)
            print(f"Existing groups: {Ansi.ORANGE}{grp_disp}{Ansi.RESET}\n")

        print(f"Editing {transport.label} configuration file: {Ansi.MAGENTA}{transport.config_file}{Ansi.RESET}\n")

        if last_msg[0]:
            print(f"{Ansi.RED}{last_msg[0]}{Ansi.RESET}\n")
            last_msg[0] = ""

        nickname_result = prompt_nickname(transport.config_file, last_msg)
        match nickname_result:
            case PromptCancel():
                clear_screen()
                return 0
            case PromptInvalid():
                continue
            case PromptOk(value=host_alias):
                pass

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
            updated_result = prompt_alias_change(original_alias, last_msg)
            match updated_result:
                case PromptOk(value=updated):
                    host_alias = updated
                case PromptCancel() | PromptInvalid():
                    continue

        hostname_result = prompt_hostname(hostname, last_msg)
        match hostname_result:
            case PromptOk(value=hostname):
                pass
            case PromptCancel() | PromptInvalid():
                continue

        port_result = prompt_port(port, last_msg)
        match port_result:
            case PromptOk(value=port):
                pass
            case PromptCancel() | PromptInvalid():
                continue

        if transport.key == "ssh":
            algo_result = prompt_configure_algorithms(host_alias, hostkey, kex, macs, last_msg)
            match algo_result:
                case PromptCancel() | PromptInvalid():
                    continue
                case PromptOk(value=settings):
                    hostkey, kex, macs = settings.hostkey, settings.kex, settings.macs

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


if __name__ == "__main__":
    raise SystemExit(run_addhost())
