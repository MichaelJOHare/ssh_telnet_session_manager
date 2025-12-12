from __future__ import annotations

import subprocess
from pathlib import Path

from ..ansi import clear_screen, Ansi, set_title
from ..prompting import prompt_text
from ..transport_menu import Transport
from ..config_utils import read_host_values

def render_menu(title: str, subtitle: str, labels: list[str], *, types: list[str] | None = None, message: str = "") -> None:
    clear_screen()
    print(f"\n------------------------{title} MENU------------------------\n")
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


def ssh_connect(host_alias: str) -> int:
    user = prompt_text(f"{Ansi.MAGENTA}login{Ansi.RESET} as: ").strip()
    if not user:
        return 2

    clear_screen()
    print(f"Connecting to {Ansi.GREEN}{host_alias}{Ansi.RESET} as {Ansi.MAGENTA}{user}{Ansi.RESET}...")
    set_title(f"{user}@{host_alias}")
    try:
        result = subprocess.run(["ssh", f"{user}@{host_alias}"])
        return result.returncode
    finally:
        set_title("VMS MENU")


def telnet_connect(host_alias: str, config_file: Path) -> int:
    hostname, port, *_ = read_host_values(host_alias, config_file)
    if not hostname:
        return 3

    clear_screen()
    print(f"Connecting to {Ansi.GREEN}{host_alias}{Ansi.RESET} via telnet...")
    set_title(f"telnet:{host_alias}")
    try:
        result = subprocess.run(["telnet", hostname, str(port or "23")])
        return result.returncode
    finally:
        set_title("VMS MENU")


def attempt_connection(host_label: str, transport: Transport, *, last_msg_out: list[str]) -> bool:
    if transport.key == "ssh":
        rc = ssh_connect(host_label)
        if rc == 0:
            last_msg_out[:] = [""]
            return True
        if rc == 2:
            last_msg_out[:] = ["Error: username required"]
            return False
        last_msg_out[:] = [f"Connection to {host_label} failed — returned to menu"]
        return False

    rc = telnet_connect(host_label, transport.config_file)
    if rc == 0:
        last_msg_out[:] = [""]
        return True
    if rc == 3:
        last_msg_out[:] = [
            f"No telnet hostname/IP configured for {Ansi.GREEN}{host_label}{Ansi.RESET}\n"
            f"{Ansi.YELLOW}Note{Ansi.RESET}: ~/.telnet/config should have an empty newline at the end of the file."
        ]
        return False
    last_msg_out[:] = [f"Connection to {host_label} failed — returned to menu"]
    return False