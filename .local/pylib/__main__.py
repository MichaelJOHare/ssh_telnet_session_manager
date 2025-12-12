from __future__ import annotations

import sys

from .addhost.addhost_app import run_addhost
from .vmsmenu.vmsmenu_app import run_vmsmenu


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    cmd = argv[0] if argv else "help"
    rest = argv[1:] if argv else []

    if cmd in {"-h", "--help", "help"}:
        print("Usage:")
        print("  vmsmenu [--help]")
        print("  addhost [--help]")
        print()
        print("Commands:")
        print("  vmsmenu   Interactive menu to connect to hosts via SSH or Telnet")
        print("  addhost   Interactive editor to add/edit host entries for SSH/Telnet")
        print()
        print("Config files:")
        print("  SSH:    ~/.ssh/config")
        print("  Telnet: ~/.telnet/config")
        print()
        print("Notes:")
        print("  - Both commands are interactive.")
        print("  - Extra CLI args are ignored (except --help / -h).")
        print("  - Hosts can be grouped as 'group.nickname' (e.g. prod.db1).")
        print("  - Set NO_COLOR=1 to disable ANSI colors.")
        return 0

    if cmd == "vmsmenu" and any(a in {"-h", "--help"} for a in rest):
        print("Usage:")
        print("  vmsmenu")
        print("  vmsmenu --help")
        print()
        print("What it does:")
        print("  - Prompts for SSH vs Telnet")
        print("  - Reads hosts from ~/.ssh/config or ~/.telnet/config")
        print("  - Lets you pick a host (or group) and launches ssh/telnet")
        print()
        print("Controls:")
        print("  - Enter a number to select")
        print("  - E to exit, B to go back (in group menus)")
        print()
        print("Notes:")
        print("  - Interactive; ignores other CLI arguments.")
        print("  - Set NO_COLOR=1 to disable ANSI colors.")
        return 0

    if cmd == "addhost" and any(a in {"-h", "--help"} for a in rest):
        print("Usage:")
        print("  addhost")
        print("  addhost --help")
        print()
        print("What it does:")
        print("  - Prompts for SSH vs Telnet")
        print("  - Adds/edits Host entries in ~/.ssh/config or ~/.telnet/config")
        print("  - Supports grouped aliases as 'group.nickname' (e.g. l2.IA21)")
        print()
        print("Notes:")
        print("  - Interactive; ignores other CLI arguments.")
        print("  - Set NO_COLOR=1 to disable ANSI colors.")
        return 0

    if cmd == "vmsmenu":
        return run_vmsmenu()

    if cmd == "addhost":
        return run_addhost()

    print(f"Unknown command: {cmd}")
    print("Try: vmsmenu --help or addhost --help")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
