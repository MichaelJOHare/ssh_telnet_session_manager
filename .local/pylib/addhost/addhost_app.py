from __future__ import annotations

from pathlib import Path

from ..ansi import Ansi, clear_screen
from ..ident import normalize_identifier
from ..prompting import prompt_yes_no
from ..transport_menu import select_transport
from ..config_utils import HostEntry, GROUP_DELIMITER, find_aliases_for_nickname, list_groups, load_host_aliases, read_host_values, remove_host_entry, upsert_host_entry
from ..types import AlgorithmSettings, PromptCancel, PromptInvalid, PromptOk, PromptResult


def add_or_list_menu(config_file: Path, last_msg: list[str]) -> bool:
    while True:
        clear_screen()
        print("\n-----------------ADD OR LIST HOSTS--------------------\n")
        print(f"1) {Ansi.MAGENTA}Add{Ansi.RESET} or edit {Ansi.GREEN}hosts{Ansi.RESET}")
        print(f"2) {Ansi.MAGENTA}List{Ansi.RESET} existing {Ansi.GREEN}hosts{Ansi.RESET}")
        sel = input(f"\nEnter selection (or {Ansi.RED}E{Ansi.RESET} to exit) [{Ansi.GREEN}1{Ansi.RESET}]: ").strip()
        if sel in ("", "1"):
            return True
        if sel == "2":
            hosts = sorted(load_host_aliases(config_file), key=str.casefold)
            if not hosts:
                last_msg[0] = f"No hosts found in configuration file {config_file}."
                return False
            print(f"Listing existing hosts in {Ansi.MAGENTA}{config_file}{Ansi.RESET}:\n")
            for idx, host in enumerate(hosts, start=1):
                print(f"{idx}) {_format_host_display(host)}")
            input("\nPress Enter to return to menu...")
            continue
        if sel.lower() == "e":
            clear_screen()
            return False
        print(f"{Ansi.RED}Invalid selection.{Ansi.RESET}")


def _format_host_display(host: str, *, delimiter: str=GROUP_DELIMITER) -> str:
    if delimiter in host:
        group, member = host.split(GROUP_DELIMITER, 1)
        return f"{Ansi.ORANGE}{group.upper()}{Ansi.RESET} {Ansi.GREEN}{member.upper()}{Ansi.RESET}"
    return f"{Ansi.GREEN}{host.upper()}{Ansi.RESET}"


def prompt_nickname(config_file: Path, last_msg: list[str]) -> PromptResult[str]:
    raw = input(f"Enter unique {Ansi.GREEN}nickname{Ansi.RESET} for the host (or {Ansi.RED}E{Ansi.RESET} to exit): ").strip()
    if raw.lower() == "e":
        return PromptCancel()

    norm = normalize_identifier(raw, case_mode="upper")
    if not norm.ok:
        last_msg[0] = "Nickname is required." if norm.error == "empty" else "Nicknames must consist of letters and/or numbers."
        return PromptInvalid()

    nickname = norm.value
    matches = find_aliases_for_nickname(nickname, config_file)
    if matches:
        resolved_result = select_existing_alias(nickname, matches, last_msg)
        match resolved_result:
            case PromptOk(value=resolved):
                return PromptOk(resolved)
            case PromptCancel() | PromptInvalid():
                return PromptInvalid()

    group_result = prompt_group_name(last_msg)
    match group_result:
        case PromptCancel():
            # cancelling group selection returns to the nickname prompt
            return PromptInvalid()
        case PromptInvalid():
            return PromptInvalid()
        case PromptOk(value=group):
            return PromptOk(f"{group}.{nickname}" if group else nickname)


def prompt_group_name(last_msg: list[str]) -> PromptResult[str]:
    if not prompt_yes_no(f"Is this host part of a {Ansi.ORANGE}group{Ansi.RESET}?"):
        return PromptOk("")

    prompt = (
        "Enter a group name, use only letters and/or numbers "
        f"({Ansi.GREEN}Enter{Ansi.RESET} to skip, {Ansi.RED}E{Ansi.RESET} to cancel): "
    )

    while True:
        raw = input(prompt).strip()
        if raw.lower() == "e":
            last_msg[0] = "Group selection cancelled. Any changes to host were not saved."
            return PromptCancel()
        norm = normalize_identifier(raw, case_mode="lower", allow_empty=True)
        if not norm.ok:
            print(f"{Ansi.RED}Group names must consist of letters and/or numbers.{Ansi.RESET}")
            continue
        return PromptOk(norm.value)


def select_existing_alias(nickname: str, matches: list[str], last_msg: list[str]) -> PromptResult[str]:
    if len(matches) > 1:
        print(f"\nNickname {Ansi.GREEN}{nickname}{Ansi.RESET} exists in multiple host entries:")
        for idx, alias in enumerate(matches, start=1):
            print(f"  {idx}) {Ansi.GREEN}{alias}{Ansi.RESET}")

        while True:
            choice = input(f"Select entry to edit (1-{len(matches)}) or {Ansi.RED}E{Ansi.RESET} to cancel: ").strip()
            if choice.lower() == "e":
                last_msg[0] = "Selection cancelled."
                return PromptCancel()
            if choice.isdigit() and 1 <= int(choice) <= len(matches):
                resolved = matches[int(choice) - 1]
                break
            print(f"{Ansi.RED}Enter a valid selection.{Ansi.RESET}")
    else:
        resolved = matches[0]

    group_name = resolved.split(".", 1)[0] if "." in resolved else ""
    host_display = f"{Ansi.GREEN}{nickname}{Ansi.RESET}"
    if group_name:
        host_display = f"{Ansi.ORANGE}{group_name.upper()}{Ansi.RESET} {host_display}"

    print(f"\nHost {host_display} already exists.")
    if not prompt_yes_no("Edit this host?", default=True):
        last_msg[0] = "Use a different nickname or confirm edit, each entry must have a unique nickname."
        return PromptInvalid()

    return PromptOk(resolved)


def prompt_alias_edit(current_alias: str, last_msg: list[str]) -> PromptResult[str]:
    current_group = ""
    current_nick = current_alias
    if "." in current_alias:
        current_group, current_nick = current_alias.split(".", 1)

    host_display = f"{Ansi.GREEN}{current_nick}{Ansi.RESET}"
    if current_group:
        host_display = f"{Ansi.ORANGE}{current_group.upper()}{Ansi.RESET} {host_display}"

    print(f"\nEditing existing host {host_display}")
    if not prompt_yes_no("Change nickname or group?"):
        return PromptOk(current_alias)

    # nickname
    new_nick = current_nick
    while True:
        raw = input(
            f"Enter new nickname [{Ansi.GREEN}{current_nick}{Ansi.RESET}] "
            f"({Ansi.GREEN}Enter{Ansi.RESET} keeps current, {Ansi.RED}E{Ansi.RESET} to cancel): "
        ).strip()
        if raw.lower() == "e":
            last_msg[0] = "Nickname edit cancelled. Any changes to host were not saved."
            return PromptCancel()
        if raw == "":
            break
        norm = normalize_identifier(raw, case_mode="upper")
        if norm.ok:
            new_nick = norm.value
            break
        print(f"{Ansi.RED}Nicknames must consist of letters and/or numbers.{Ansi.RESET}")

    # group
    group_label = current_group.upper() if current_group else "none"
    while True:
        raw = input(
            f"Enter new group name [{Ansi.ORANGE}{group_label}{Ansi.RESET}] ("
            f"{Ansi.GREEN}Enter{Ansi.RESET} keeps current, {Ansi.MAGENTA}-{Ansi.RESET} removes, {Ansi.RED}E{Ansi.RESET} to cancel): "
        ).strip()
        if raw.lower() == "e":
            last_msg[0] = "Group edit cancelled. Any changes to host were not saved."
            return PromptCancel()
        if raw == "":
            new_group = current_group
            break
        if raw == "-":
            new_group = ""
            break
        norm = normalize_identifier(raw, case_mode="lower")
        if norm.ok:
            new_group = norm.value
            break
        print(f"{Ansi.RED}Group names must consist of letters and/or numbers.{Ansi.RESET}")

    return PromptOk(f"{new_group}.{new_nick}" if new_group else new_nick)


def prompt_hostname(current: str, last_msg: list[str]) -> PromptResult[str]:
    prompt = "Enter hostname or IP"
    if current:
        prompt += f" [{Ansi.GREEN}{current}{Ansi.RESET}]"
    prompt += f" (or {Ansi.RED}E{Ansi.RESET} to cancel): "

    raw = input(prompt).strip()
    if raw.lower() == "e":
        last_msg[0] = "Hostname entry cancelled. Any changes to host were not saved."
        return PromptCancel()
    if raw:
        return PromptOk(raw)
    if current:
        return PromptOk(current)
    last_msg[0] = "Hostname/IP is required."
    return PromptInvalid()


def prompt_port(current: str, last_msg: list[str]) -> PromptResult[str]:
    cur = current or "22"
    raw = input(f"Enter port [{Ansi.GREEN}{cur}{Ansi.RESET}] (or {Ansi.RED}E{Ansi.RESET} to cancel): ").strip()
    if raw.lower() == "e":
        last_msg[0] = "Port entry cancelled. Any changes to host were not saved."
        return PromptCancel()
    return PromptOk(raw or cur)


def format_algo_display(value: str, label: str) -> str:
    display = value if value else "<default>"
    if display == "<default>":
        return f"  {label}: {Ansi.ORANGE}{display}{Ansi.RESET}"
    return f"  {label}: {Ansi.MAGENTA}{display}{Ansi.RESET}"


def prompt_configure_algorithms(
    host_alias: str,
    hostkey: str,
    kex: str,
    macs: str,
    last_msg: list[str],
) -> PromptResult[AlgorithmSettings]:
    while True:
        p1 = (
            f"Configure algorithms -- {Ansi.YELLOW}H{Ansi.RESET})ostKeyAlgorithms, "
            f"{Ansi.YELLOW}K{Ansi.RESET})exAlgorithms, {Ansi.YELLOW}M{Ansi.RESET})ACs\n"
        )
        p2 = (
            f"Press {Ansi.GREEN}Enter{Ansi.RESET} to keep current algorithm settings "
            f"({Ansi.RED}E{Ansi.RESET} to cancel, {Ansi.MAGENTA}?{Ansi.RESET} to list current settings): "
        )
        choice = input(p1 + p2).strip()

        if choice.lower() == "e":
            last_msg[0] = "Algorithm configuration cancelled. Any changes to host were not saved."
            return PromptCancel()

        if choice == "?":
            print(f"\nCurrent algorithm settings for host {Ansi.GREEN}{host_alias}{Ansi.RESET}:")
            print(format_algo_display(hostkey, "HostKeyAlgorithms"))
            print(format_algo_display(kex, "KexAlgorithms"))
            print(format_algo_display(macs, "MACs"))
            input(f"\nPress {Ansi.GREEN}Enter{Ansi.RESET} to continue...")
            print()
            continue

        if choice == "":
            return PromptOk(AlgorithmSettings(hostkey=hostkey, kex=kex, macs=macs))

        choice = "".join([c for c in choice.upper() if c in "HKM"])
        if not choice:
            print(f"{Ansi.RED}Enter a combination of H, K, or M.{Ansi.RESET}")
            continue
        break

    if "H" in choice:
        raw = input(f"HostKeyAlgorithms{f' [{hostkey}]' if hostkey else ''} (blank keeps current, '-' removes): ").strip()
        if raw == "-":
            hostkey = ""
        elif raw:
            hostkey = f"+{raw}"

    if "K" in choice:
        raw = input(f"KexAlgorithms{f' [{kex}]' if kex else ''} (blank keeps current, '-' removes): ").strip()
        if raw == "-":
            kex = ""
        elif raw:
            kex = f"+{raw}"

    if "M" in choice:
        raw = input(f"MACs{f' [{macs}]' if macs else ''} (blank keeps current, '-' removes): ").strip()
        if raw == "-":
            macs = ""
        elif raw:
            macs = f"+{raw}"

    return PromptOk(AlgorithmSettings(hostkey=hostkey, kex=kex, macs=macs))


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

        editing_existing = False
        original_alias = ""
        hostname = ""
        port = ""
        hostkey = ""
        kex = ""
        macs = ""

        if host_alias and _host_entry_exists(host_alias, transport.config_file):
            editing_existing = True
            original_alias = host_alias

        if editing_existing:
            hostname, port, hostkey, kex, macs = read_host_values(original_alias, transport.config_file)
            updated_result = prompt_alias_edit(original_alias, last_msg)
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

        if editing_existing and host_alias != original_alias:
            remove_host_entry(original_alias, transport.config_file)

        entry = HostEntry(alias=host_alias, hostname=hostname, port=port, 
                          hostkey_algorithms=hostkey, kex_algorithms=kex, macs=macs)
        upsert_host_entry(entry, transport.config_file)

        print(
            f"Saved host {_format_host_display(host_alias)} ("
            f"{Ansi.GREEN}{hostname}{Ansi.RESET}:{Ansi.MAGENTA}{port}{Ansi.RESET}) "
            f"to {Ansi.MAGENTA}{transport.config_file}{Ansi.RESET}"
        )

        if not prompt_yes_no("Add or edit another host?"):
            clear_screen()
            return 0


def _host_entry_exists(alias: str, config_file: Path) -> bool:
    from ..config_utils import host_entry_exists

    return host_entry_exists(alias, config_file)


if __name__ == "__main__":
    raise SystemExit(run_addhost())
