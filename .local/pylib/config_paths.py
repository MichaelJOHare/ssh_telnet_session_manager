from __future__ import annotations

from pathlib import Path

from .types import TransportConfig


def ssh_config() -> TransportConfig:
    return TransportConfig(key="ssh", label="SSH", config_path=Path.home() / ".ssh" / "config")


def telnet_config() -> TransportConfig:
    return TransportConfig(key="telnet", label="Telnet", config_path=Path.home() / ".telnet" / "config")


def ensure_config_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
