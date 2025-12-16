from __future__ import annotations

from pathlib import Path

from .types import Transport


def ssh_config() -> Transport:
    return Transport(key="ssh", label="SSH", config_file=Path.home() / ".ssh" / "config")


def telnet_config() -> Transport:
    return Transport(key="telnet", label="Telnet", config_file=Path.home() / ".telnet" / "config")


def ensure_config_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
