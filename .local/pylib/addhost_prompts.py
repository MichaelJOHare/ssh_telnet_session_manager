from __future__ import annotations

from .ansi import Ansi
from .ident import normalize_identifier
from .prompting import prompt_yes_no, prompt_text
from .config_utils import find_aliases_for_nickname
from .menu_utils import format_host_details, format_host_display
from .types import PromptCancel, PromptInvalid, PromptOk, PromptResult


def prompt_nickname(aliases: list[str], last_msg: list[str]) -> PromptResult[str]:
    raw = prompt_text(f"Enter unique {Ansi.GREEN}nickname{Ansi.RESET} for the host (or {Ansi.RED}E{Ansi.RESET} to exit): ").strip()
    if raw.lower() == "e":
        return PromptCancel()

    norm = normalize_identifier(raw, case_mode="upper")
    if not norm.ok:
        last_msg[0] = "Nickname is required." if norm.error == "empty" else "Nicknames must consist of letters and/or numbers."
        return PromptInvalid()

    nickname = norm.value
    matches = find_aliases_for_nickname(nickname, aliases)
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
        raw = prompt_text(prompt).strip()
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
            choice = prompt_text(f"Select entry to edit (1-{len(matches)}) or {Ansi.RED}E{Ansi.RESET} to cancel: ").strip()
            if choice.lower() == "e":
                last_msg[0] = "Selection cancelled."
                return PromptCancel()
            if choice.isdigit() and 1 <= int(choice) <= len(matches):
                resolved = matches[int(choice) - 1]
                break
            print(f"{Ansi.RED}Enter a valid selection.{Ansi.RESET}")
    else:
        resolved = matches[0]

    host_display = format_host_display(resolved)
    print(f"\nHost {host_display} already exists.")
    if not prompt_yes_no("Edit this host?", default=True):
        last_msg[0] = "Use a different nickname or confirm edit, each entry must have a unique nickname."
        return PromptInvalid()

    return PromptOk(resolved)


def prompt_alias_change(current_alias: str, last_msg: list[str]) -> PromptResult[str]:
    current_group = ""
    current_nick = current_alias
    if "." in current_alias:
        current_group, current_nick = current_alias.split(".", 1)

    host_display = format_host_display(current_alias)
    print(f"\nEditing existing host {host_display}")
    if not prompt_yes_no("Change nickname or group?"):
        return PromptOk(current_alias)

    new_nick = current_nick
    while True:
        raw = prompt_text(
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

    group_label = current_group.upper() if current_group else "none"
    while True:
        raw = prompt_text(
            f"Enter new group name [{Ansi.ORANGE}{group_label}{Ansi.RESET}]"
            f" ({Ansi.GREEN}Enter{Ansi.RESET} keeps current, {Ansi.MAGENTA}-{Ansi.RESET} removes, {Ansi.RED}E{Ansi.RESET} to cancel): "
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

    raw = prompt_text(prompt).strip()
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
    raw = prompt_text(f"Enter port [{Ansi.GREEN}{cur}{Ansi.RESET}] (or {Ansi.RED}E{Ansi.RESET} to cancel): ").strip()
    if raw.lower() == "e":
        last_msg[0] = "Port entry cancelled. Any changes to host were not saved."
        return PromptCancel()
    if raw:
        if not raw.isdigit() or not (1 <= int(raw) <= 65535):
            last_msg[0] = "Port must be a number between 1 and 65535."
            return PromptInvalid()
    return PromptOk(raw or cur)


def prompt_configure_algorithms(
    host_alias: str,
    port: str,
    hostkey: str,
    kex: str,
    macs: str,
    last_msg: list[str],
) -> PromptResult[tuple[str, str, str]]:
    while True:
        p1 = (
            f"Configure algorithms -- {Ansi.YELLOW}H{Ansi.RESET})ostKeyAlgorithms, "
            f"{Ansi.YELLOW}K{Ansi.RESET})exAlgorithms, {Ansi.YELLOW}M{Ansi.RESET})ACs\n"
        )
        p2 = (
            f"Press {Ansi.GREEN}Enter{Ansi.RESET} to keep current algorithm settings "
            f"({Ansi.RED}E{Ansi.RESET} to cancel, {Ansi.MAGENTA}?{Ansi.RESET} to list current settings): "
        )
        choice = prompt_text(p1 + p2).strip()

        if choice.lower() == "e":
            last_msg[0] = "Algorithm configuration cancelled. Any changes to host were not saved."
            return PromptCancel()

        if choice == "?":
            print(f"\nCurrent algorithm settings for host {Ansi.GREEN}{host_alias}{Ansi.RESET}:")
            format_host_details(host_alias, port, hostkey, kex, macs)
            prompt_text(f"\nPress {Ansi.GREEN}Enter{Ansi.RESET} to continue...")
            print()
            continue

        if choice == "":
            return PromptOk((hostkey, kex, macs))

        choice = "".join([c for c in choice.upper() if c in "HKM"])
        if not choice:
            print(f"{Ansi.RED}Enter a combination of H, K, or M.{Ansi.RESET}")
            continue
        break

    if "H" in choice:
        raw = prompt_text(f"HostKeyAlgorithms{f' [{hostkey}]' if hostkey else ''} (blank keeps current, '-' removes): ").strip()
        if raw == "-":
            hostkey = ""
        elif raw:
            hostkey = f"+{raw}"

    if "K" in choice:
        raw = prompt_text(f"KexAlgorithms{f' [{kex}]' if kex else ''} (blank keeps current, '-' removes): ").strip()
        if raw == "-":
            kex = ""
        elif raw:
            kex = f"+{raw}"

    if "M" in choice:
        raw = prompt_text(f"MACs{f' [{macs}]' if macs else ''} (blank keeps current, '-' removes): ").strip()
        if raw == "-":
            macs = ""
        elif raw:
            macs = f"+{raw}"

    return PromptOk((hostkey, kex, macs))