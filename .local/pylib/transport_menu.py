from __future__ import annotations

from .ansi import Ansi, clear_screen
from .config_paths import ensure_config_file, ssh_config, telnet_config
from .types import Transport


def select_transport() -> Transport | None:
    while True:
        clear_screen()
        print("\n------------SELECT CONNECTION METHOD------------\n")
        print(f"1) {Ansi.GREEN}SSH{Ansi.RESET} (default)")
        print(f"2) {Ansi.YELLOW}Telnet{Ansi.RESET}\n")
        sel = input(
            f"Enter number (or {Ansi.RED}E{Ansi.RESET} to exit) [{Ansi.GREEN}1{Ansi.RESET}]: "
        ).strip()
        if sel in ("", "1"):
            cfg = ssh_config()
            ensure_config_file(cfg.config_path)
            return Transport(key=cfg.key, label=cfg.label, config_file=cfg.config_path)
        if sel == "2":
            cfg = telnet_config()
            ensure_config_file(cfg.config_path)
            return Transport(key=cfg.key, label=cfg.label, config_file=cfg.config_path)
        if sel.lower() == "e":
            return None
        print(f"{Ansi.RED}Invalid selection.{Ansi.RESET}")
